# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the above pages for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
""" ``scenedetect.scene_manager`` Module

This module implements the :py:class:`SceneManager` object, which is used to coordinate
SceneDetectors and frame sources (:py:class:`VideoStream <scenedetect.video_stream.VideoStream>`).
This includes creating a cut list (see :py:meth:`SceneManager.get_cut_list`) and event list (see
:py:meth:`SceneManager.get_event_list`) of all changes in scene, which is used to generate a final
list of scenes (see :py:meth:`SceneManager.get_scene_list`) in the form of a list of start/end
:py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>` objects at each scene boundary.
Decoding of video frames is performed in a separate thread to improve parallelism.

The :py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>` objects and `tuples`
thereof returned by :py:meth:`get_cut_list <SceneManager.get_cut_list>` and
:py:meth:`get_scene_list <SceneManager.get_scene_list>`, respectively, can be sorted if for
some reason the scene (or cut) list becomes unsorted. The :py:class:`SceneManager` also
facilitates passing a :py:class:`scenedetect.stats_manager.StatsManager`,
if any is defined, to the associated :py:class:`scenedetect.scene_detector.SceneDetector`
objects for caching of frame metrics.

This speeds up subsequent calls to the :py:meth:`SceneManager.detect_scenes` method
that process the same frames with the same detection algorithm, even if different
threshold values (or other algorithm options) are used.
"""

import csv
from string import Template
from typing import Iterable, List, Tuple, Optional, Dict, Callable, Union, TextIO
import threading
import queue
import logging
import math

import cv2
import numpy as np

from scenedetect.frame_timecode import FrameTimecode
from scenedetect.platform import (tqdm, get_and_create_path, get_cv2_imwrite_params)
from scenedetect.video_stream import VideoStream
from scenedetect.stats_manager import StatsManager, FrameMetricRegistered
from scenedetect.scene_detector import SceneDetector, SparseSceneDetector
from scenedetect.thirdparty.simpletable import (SimpleTableCell, SimpleTableImage, SimpleTableRow,
                                                SimpleTable, HTMLPage)

logger = logging.getLogger('pyscenedetect')

##
## SceneManager Helper Functions
##

# TODO: This value can and should be tuned for performance improvements as much as possible,
# until accuracy falls, on a large enough dataset. This has yet to be done, but the current
# value doesn't seem to have caused any issues at least.
DEFAULT_MIN_WIDTH: int = 256
"""The default minimum width a frame will be downscaled to when calculating a downscale factor."""

MAX_FRAME_QUEUE_LENGTH: int = 4
"""Maximum size of the queue of frames waiting to be processed after decoding."""


def compute_downscale_factor(frame_width: int, effective_width: int = DEFAULT_MIN_WIDTH) -> int:
    """Get the optimal default downscale factor based on a video's resolution (currently only
    the width in pixels is considered).

    The resulting effective width of the video will be between frame_width and 1.5 * frame_width
    pixels (e.g. if frame_width is 200, the range of effective widths will be between 200 and 300).

    Arguments:
        frame_width: Actual width of the video frame in pixels.
        effective_width: Desired minimum width in pixels.

    Returns:
        int: The defalt downscale factor to use to achieve at least the target effective_width.
    """
    assert not (frame_width < 1 or effective_width < 1)
    if frame_width < effective_width:
        return 1
    return frame_width // effective_width


def get_scenes_from_cuts(
        cut_list: Iterable[FrameTimecode], base_timecode: FrameTimecode,
        start_pos: Union[int, FrameTimecode],
        end_pos: Union[int, FrameTimecode]) -> List[Tuple[FrameTimecode, FrameTimecode]]:
    """Returns a list of tuples of start/end FrameTimecodes for each scene based on a
    list of detected scene cuts/breaks.

    This function is called when using the :py:meth:`SceneManager.get_scene_list` method.
    The scene list is generated from a cutting list (:py:meth:`SceneManager.get_cut_list`),
    noting that each scene is contiguous, starting from the first to last frame of the input.
    If `cut_list` is empty, the resulting scene will span from `start_pos` to `end_pos`.

    Arguments:
        cut_list: List of FrameTimecode objects where scene cuts/breaks occur.
        base_timecode: The base_timecode of which all FrameTimecodes in the cut_list are based on.
        num_frames: The number of frames, or FrameTimecode representing duration, of the video that
            was processed (used to generate last scene's end time).
        start_frame: The start frame or FrameTimecode of the cut list. Used to generate the first
            scene's start time.
    Returns:
        List of tuples in the form (start_time, end_time), where both start_time and
        end_time are FrameTimecode objects representing the exact time/frame where each
        scene occupies based on the input cut_list.
    """
    # Scene list, where scenes are tuples of (Start FrameTimecode, End FrameTimecode).
    scene_list = []
    if not cut_list:
        scene_list.append((base_timecode + start_pos, base_timecode + end_pos))
        return scene_list
    # Initialize last_cut to the first frame we processed,as it will be
    # the start timecode for the first scene in the list.
    last_cut = base_timecode + start_pos
    for cut in cut_list:
        scene_list.append((last_cut, cut))
        last_cut = cut
    # Last scene is from last cut to end of video.
    scene_list.append((last_cut, base_timecode + end_pos))

    return scene_list


def write_scene_list(output_csv_file: TextIO,
                     scene_list: Iterable[Tuple[FrameTimecode, FrameTimecode]],
                     include_cut_list: bool = True,
                     cut_list: Optional[Iterable[FrameTimecode]] = None) -> None:
    """Writes the given list of scenes to an output file handle in CSV format.

    Arguments:
        output_csv_file: Handle to open file in write mode.
        scene_list: List of pairs of FrameTimecodes denoting each scene's start/end FrameTimecode.
        include_cut_list: Bool indicating if the first row should include the timecodes where
            each scene starts. Should be set to False if RFC 4180 compliant CSV output is required.
        cut_list: Optional list of FrameTimecode objects denoting the cut list (i.e. the frames
            in the video that need to be split to generate individual scenes). If not specified,
            the cut list is generated using the start times of each scene following the first one.
    """
    csv_writer = csv.writer(output_csv_file, lineterminator='\n')
    # If required, output the cutting list as the first row (i.e. before the header row).
    if include_cut_list:
        csv_writer.writerow(
            ["Timecode List:"] +
            cut_list if cut_list else [start.get_timecode() for start, _ in scene_list[1:]])
    csv_writer.writerow([
        "Scene Number", "Start Frame", "Start Timecode", "Start Time (seconds)", "End Frame",
        "End Timecode", "End Time (seconds)", "Length (frames)", "Length (timecode)",
        "Length (seconds)"
    ])
    for i, (start, end) in enumerate(scene_list):
        duration = end - start
        csv_writer.writerow([
            '%d' % (i + 1),
            '%d' % start.get_frames(),
            start.get_timecode(),
            '%.3f' % start.get_seconds(),
            '%d' % end.get_frames(),
            end.get_timecode(),
            '%.3f' % end.get_seconds(),
            '%d' % duration.get_frames(),
            duration.get_timecode(),
            '%.3f' % duration.get_seconds()
        ])


def write_scene_list_html(output_html_filename,
                          scene_list,
                          cut_list=None,
                          css=None,
                          css_class='mytable',
                          image_filenames=None,
                          image_width=None,
                          image_height=None):
    """Writes the given list of scenes to an output file handle in html format.

    Arguments:
        output_html_filename: filename of output html file
        scene_list: List of pairs of FrameTimecodes denoting each scene's start/end FrameTimecode.
        cut_list: Optional list of FrameTimecode objects denoting the cut list (i.e. the frames
            in the video that need to be split to generate individual scenes). If not passed,
            the start times of each scene (besides the 0th scene) is used instead.
        css: String containing all the css information for the resulting html page.
        css_class: String containing the named css class
        image_filenames: dict where key i contains a list with n elements (filenames of
            the n saved images from that scene)
        image_width: Optional desired width of images in table in pixels
        image_height: Optional desired height of images in table in pixels
    """
    if not css:
        css = """
        table.mytable {
            font-family: times;
            font-size:12px;
            color:#000000;
            border-width: 1px;
            border-color: #eeeeee;
            border-collapse: collapse;
            background-color: #ffffff;
            width=100%;
            max-width:550px;
            table-layout:fixed;
        }
        table.mytable th {
            border-width: 1px;
            padding: 8px;
            border-style: solid;
            border-color: #eeeeee;
            background-color: #e6eed6;
            color:#000000;
        }
        table.mytable td {
            border-width: 1px;
            padding: 8px;
            border-style: solid;
            border-color: #eeeeee;
        }
        #code {
            display:inline;
            font-family: courier;
            color: #3d9400;
        }
        #string {
            display:inline;
            font-weight: bold;
        }
        """

    # Output Timecode list
    timecode_table = SimpleTable(
        [["Timecode List:"] +
         (cut_list if cut_list else [start.get_timecode() for start, _ in scene_list[1:]])],
        css_class=css_class)

    # Output list of scenes
    header_row = [
        "Scene Number", "Start Frame", "Start Timecode", "Start Time (seconds)", "End Frame",
        "End Timecode", "End Time (seconds)", "Length (frames)", "Length (timecode)",
        "Length (seconds)"
    ]
    for i, (start, end) in enumerate(scene_list):
        duration = end - start

        row = SimpleTableRow([
            '%d' % (i + 1),
            '%d' % start.get_frames(),
            start.get_timecode(),
            '%.3f' % start.get_seconds(),
            '%d' % end.get_frames(),
            end.get_timecode(),
            '%.3f' % end.get_seconds(),
            '%d' % duration.get_frames(),
            duration.get_timecode(),
            '%.3f' % duration.get_seconds()
        ])

        if image_filenames:
            for image in image_filenames[i]:
                row.add_cell(
                    SimpleTableCell(
                        SimpleTableImage(image, width=image_width, height=image_height)))

        if i == 0:
            scene_table = SimpleTable(rows=[row], header_row=header_row, css_class=css_class)
        else:
            scene_table.add_row(row=row)

    # Write html file
    page = HTMLPage()
    page.add_table(timecode_table)
    page.add_table(scene_table)
    page.css = css
    page.save(output_html_filename)


#
# TODO(v1.0): Refactor to take a SceneList object; consider moving this and save scene list
# to a better spot, or just move them to scene_list.py.
#
def save_images(scene_list: List[Tuple[FrameTimecode, FrameTimecode]],
                video: VideoStream,
                num_images: int = 3,
                frame_margin: int = 1,
                image_extension: str = 'jpg',
                encoder_param: int = 95,
                image_name_template: str = '$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER',
                output_dir: Optional[str] = None,
                show_progress: Optional[bool] = False,
                scale: Optional[float] = None,
                height: Optional[int] = None,
                width: Optional[int] = None) -> Dict[int, List[str]]:
    """ Saves a set number of images from each scene, given a list of scenes
    and the associated video/frame source.

    Arguments:
        scene_list: A list of scenes (pairs of FrameTimecode objects) returned
            from calling a SceneManager's detect_scenes() method.
        video: A VideoStream object corresponding to the scene list.
            Note that the video will be closed/re-opened and seeked through.
        num_images: Number of images to generate for each scene.  Minimum is 1.
        frame_margin: Number of frames to pad each scene around the beginning
            and end (e.g. moves the first/last image into the scene by N frames).
            Can set to 0, but will result in some video files failing to extract
            the very last frame.
        image_extension: Type of image to save (must be one of 'jpg', 'png', or 'webp').
        encoder_param: Quality/compression efficiency, based on type of image:
            'jpg' / 'webp':  Quality 0-100, higher is better quality.  100 is lossless for webp.
            'png': Compression from 1-9, where 9 achieves best filesize but is slower to encode.
        image_name_template: Template to use when creating the images on disk. Can
            use the macros $VIDEO_NAME, $SCENE_NUMBER, and $IMAGE_NUMBER. The image
            extension is applied automatically as per the argument image_extension.
        output_dir: Directory to output the images into.  If not set, the output
            is created in the working directory.
        show_progress: If True, shows a progress bar if tqdm is installed.
        scale: Optional factor by which to rescale saved images. A scaling factor of 1 would
            not result in rescaling. A value < 1 results in a smaller saved image, while a
            value > 1 results in an image larger than the original. This value is ignored if
            either the height or width values are specified.
        height: Optional value for the height of the saved images. Specifying both the height
            and width will resize images to an exact size, regardless of aspect ratio.
            Specifying only height will rescale the image to that number of pixels in height
            while preserving the aspect ratio.
        width: Optional value for the width of the saved images. Specifying both the width
            and height will resize images to an exact size, regardless of aspect ratio.
            Specifying only width will rescale the image to that number of pixels wide
            while preserving the aspect ratio.

    Returns:
        Dictionary of the format { scene_num : [image_paths] }, where scene_num is the
        number of the scene in scene_list (starting from 1), and image_paths is a list of
        the paths to the newly saved/created images.

    Raises:
        ValueError: Raised if any arguments are invalid or out of range (e.g.
        if num_images is negative).
    """

    if not scene_list:
        return {}
    if num_images <= 0 or frame_margin < 0:
        raise ValueError()

    # TODO: Validate that encoder_param is within the proper range.
    # Should be between 0 and 100 (inclusive) for jpg/webp, and 1-9 for png.
    imwrite_param = [get_cv2_imwrite_params()[image_extension], encoder_param
                    ] if encoder_param is not None else []

    video.reset()

    # Setup flags and init progress bar if available.
    completed = True
    logger.info('Generating output images (%d per scene)...', num_images)
    progress_bar = None
    if show_progress and tqdm:
        progress_bar = tqdm(total=len(scene_list) * num_images, unit='images', dynamic_ncols=True)

    filename_template = Template(image_name_template)

    scene_num_format = '%0'
    scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + 'd'
    image_num_format = '%0'
    image_num_format += str(math.floor(math.log(num_images, 10)) + 2) + 'd'

    framerate = scene_list[0][0].framerate

    # TODO(v1.0): Split up into multiple sub-expressions so auto-formatter works correctly.
    timecode_list = [
        [
            FrameTimecode(int(f), fps=framerate) for f in [
                                                                                               # middle frames
                a[len(a) // 2] if (0 < j < num_images - 1) or num_images == 1

                                                                                               # first frame
                else min(a[0] + frame_margin, a[-1]) if j == 0

                                                                                               # last frame
                else max(a[-1] - frame_margin, a[0])

                                                                                               # for each evenly-split array of frames in the scene list
                for j, a in enumerate(np.array_split(r, num_images))
            ]
        ] for i, r in enumerate([
                                                                                               # pad ranges to number of images
            r if 1 + r[-1] - r[0] >= num_images else list(r) + [r[-1]] * (num_images - len(r))
                                                                                               # create range of frames in scene
            for r in (
                range(start.get_frames(), end.get_frames())
                                                                                               # for each scene in scene list
                for start, end in scene_list)
        ])
    ]

    image_filenames = {i: [] for i in range(len(timecode_list))}
    aspect_ratio = video.aspect_ratio
    if abs(aspect_ratio - 1.0) < 0.01:
        aspect_ratio = None

    for i, scene_timecodes in enumerate(timecode_list):
        for j, image_timecode in enumerate(scene_timecodes):
            video.seek(image_timecode)
            frame_im = video.read()
            if frame_im is not None:
                file_path = '%s.%s' % (filename_template.safe_substitute(
                    VIDEO_NAME=video.name,
                    SCENE_NUMBER=scene_num_format % (i + 1),
                    IMAGE_NUMBER=image_num_format % (j + 1),
                    FRAME_NUMBER=image_timecode.get_frames()), image_extension)
                image_filenames[i].append(file_path)
                if aspect_ratio is not None:
                    frame_im = cv2.resize(
                        frame_im, (0, 0), fx=aspect_ratio, fy=1.0, interpolation=cv2.INTER_CUBIC)

                # Get frame dimensions prior to resizing or scaling
                frame_height = frame_im.shape[0]
                frame_width = frame_im.shape[1]

                # Figure out what kind of resizing needs to be done
                if height and width:
                    frame_im = cv2.resize(frame_im, (width, height), interpolation=cv2.INTER_CUBIC)
                elif height and not width:
                    factor = height / float(frame_height)
                    width = int(factor * frame_width)
                    frame_im = cv2.resize(frame_im, (width, height), interpolation=cv2.INTER_CUBIC)
                elif width and not height:
                    factor = width / float(frame_width)
                    height = int(factor * frame_height)
                    frame_im = cv2.resize(frame_im, (width, height), interpolation=cv2.INTER_CUBIC)
                elif scale:
                    frame_im = cv2.resize(
                        frame_im, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

                cv2.imwrite(get_and_create_path(file_path, output_dir), frame_im, imwrite_param)
            else:
                completed = False
                break
            if progress_bar:
                progress_bar.update(1)

    if not completed:
        logger.error('Could not generate all output images.')

    return image_filenames


##
## SceneManager Class Implementation
##


class SceneManager:
    """The SceneManager facilitates detection of scenes via the :py:meth:`detect_scenes`
    method, given a video source (:py:class:`VideoStream <scenedetect.video.VideoStream>`),
    and SceneDetector algorithms added via the :py:meth:`add_detector` method. Scene
    detection is performed in parallel with decoding the video by reading frames from the
    `VideoStream` in a background thread.
    """

    def __init__(
        self,
        stats_manager: Optional[StatsManager] = None,
    ):
        """
        Arguments:
            stats_manager: :py:class:`StatsManager` to bind to this `SceneManager`. Can be
                accessed via the `stats_manager` property of the resulting object to load
                from or save to a file on disk.
        """
        self._cutting_list = []
        self._event_list = []
        self._detector_list = []
        self._sparse_detector_list = []
        # TODO(v1.0): This class should own a StatsManager instead of taking an optional one.
        # Expose a new `stats_manager` @property from the SceneManager, and either change the
        # `stats_manager` argument to to `store_stats: bool=False``, or lazy-init one.

        # TODO(v1.0): This class should own a VideoStream as well, instead of passing one
        # to the detect_scenes method. If concatenation is required, it can be implemented as
        # a generic VideoStream wrapper.
        self._stats_manager: Optional[StatsManager] = stats_manager

        # Position of video that was first passed to detect_scenes.
        self._start_pos: FrameTimecode = None
        # Position of video on the last frame processed by detect_scenes.
        self._last_pos: FrameTimecode = None
        self._base_timecode: Optional[FrameTimecode] = None
        self._downscale: int = 1
        self._auto_downscale: bool = True
        # Boolean indicating if we have only seen EventType.CUT events so far.
        self._only_cuts: bool = True

    @property
    def stats_manager(self) -> Optional[StatsManager]:
        """Getter for the StatsManager associated with this SceneManager, if any."""
        return self._stats_manager

    @property
    def downscale(self) -> int:
        """Factor to downscale each frame by. Will always be >= 1, where 1
        indicates no scaling. Will be ignored if auto_downscale=True."""
        return self._downscale

    @downscale.setter
    def downscale(self, value: int):
        """Set to 1 for no downscaling, 2 for 2x downscaling, 3 for 3x, etc..."""
        if value < 1:
            raise ValueError("Downscale factor must be a positive integer >= 1!")
        if self.auto_downscale:
            logger.warning("Downscale factor will be ignored because auto_downscale=True!")
        if value is not None and not isinstance(value, int):
            logger.warning("Downscale factor will be truncated to integer!")
            value = int(value)
        self._downscale = value

    @property
    def auto_downscale(self) -> bool:
        """If set to True, will automatically downscale based on video frame size.

        Overrides `downscale` if set."""
        return self._auto_downscale

    @auto_downscale.setter
    def auto_downscale(self, value: bool):
        self._auto_downscale = value

    def add_detector(self, detector: SceneDetector) -> None:
        """ Adds/registers a SceneDetector (e.g. ContentDetector, ThresholdDetector) to
        run when detect_scenes is called. The SceneManager owns the detector object,
        so a temporary may be passed.

        Arguments:
            detector (SceneDetector): Scene detector to add to the SceneManager.
        """
        if self._stats_manager is None and detector.stats_manager_required():
            # Make sure the lists are empty so that the detectors don't get
            # out of sync (require an explicit statsmanager instead)
            assert not self._detector_list and not self._sparse_detector_list
            self._stats_manager = StatsManager()

        detector.stats_manager = self._stats_manager
        if self._stats_manager is not None:
            # Allow multiple detection algorithms of the same type to be added
            # by suppressing any FrameMetricRegistered exceptions due to attempts
            # to re-register the same frame metric keys.
            try:
                self._stats_manager.register_metrics(detector.get_metrics())
            except FrameMetricRegistered:
                pass

        if not issubclass(type(detector), SparseSceneDetector):
            self._detector_list.append(detector)
        else:
            self._sparse_detector_list.append(detector)

    def get_num_detectors(self) -> int:
        """ Gets number of registered scene detectors added via add_detector. """
        return len(self._detector_list)

    def clear(self) -> None:
        """ Clears all cuts/scenes and resets the SceneManager's position.

        Any statistics generated are still saved in the StatsManager object passed to the
        SceneManager's constructor, and thus, subsequent calls to detect_scenes, using the same
        frame source seeked back to the original time (or beginning of the video) will use the
        cached frame metrics that were computed and saved in the previous call to detect_scenes.
        """
        self._cutting_list.clear()
        self._event_list.clear()
        self._last_pos = None
        self._start_pos = None
        self.clear_detectors()

    def clear_detectors(self) -> None:
        """ Removes all scene detectors added to the SceneManager via add_detector(). """
        self._detector_list.clear()
        self._sparse_detector_list.clear()

    def get_scene_list(self,
                       base_timecode: Optional[FrameTimecode] = None,
                       start_in_scene: bool = False) -> List[Tuple[FrameTimecode, FrameTimecode]]:
        """ Returns a list of tuples of start/end FrameTimecodes for each detected scene.

        The scene list is generated by combining the results of all sparse detectors with
        those from dense ones (i.e. combining the results of :py:meth:`get_cut_list`
        and :py:meth:`get_event_list`).

        Returns:
            List of tuples in the form (start_time, end_time), where both start_time and
            end_time are FrameTimecode objects representing the exact time/frame where each
            detected scene in the video begins and ends.
        """
        if base_timecode is None:
            base_timecode = self._base_timecode
        if base_timecode is None:
            return []
        cut_list = self.get_cut_list(base_timecode)
        scene_list = get_scenes_from_cuts(cut_list, base_timecode, self._start_pos, self._last_pos)
        # If we didn't actually detect any cuts, make sure the resulting scene_list is empty
        # unless start_in_scene is True.
        if not cut_list and not start_in_scene:
            scene_list = []
        return sorted(self.get_event_list(base_timecode) + scene_list)

    def get_cut_list(self, base_timecode: Optional[FrameTimecode] = None) -> List[FrameTimecode]:
        """ Returns a list of FrameTimecodes of the detected scene changes/cuts.

        Unlike get_scene_list, the cutting list returns a list of FrameTimecodes representing
        the point in the input video(s) where a new scene was detected, and thus the frame
        where the input should be cut/split. The cutting list, in turn, is used to generate
        the scene list, noting that each scene is contiguous starting from the first frame
        and ending at the last frame detected.

        If only sparse detectors are used (e.g. MotionDetector), this will always be empty.

        Returns:
            List of FrameTimecode objects denoting the points in time where a scene change
            was detected in the input video(s), which can also be passed to external tools
            for automated splitting of the input into individual scenes.
        """
        if base_timecode is None:
            base_timecode = self._base_timecode
        if base_timecode is None:
            return []
        return [FrameTimecode(cut, base_timecode) for cut in self._get_cutting_list()]

    def _get_cutting_list(self) -> List[int]:
        """ Returns a sorted list of unique frame numbers of any detected scene cuts. """
        # We remove duplicates here by creating a set then back to a list and sort it.
        return sorted(list(set(self._cutting_list)))

    def get_event_list(
            self,
            base_timecode: Optional[FrameTimecode] = None
    ) -> List[Tuple[FrameTimecode, FrameTimecode]]:
        """ Returns a list of FrameTimecode pairs of the detected scenes by all sparse detectors.

        Unlike get_scene_list, the event list returns a list of FrameTimecodes representing
        the point in the input video(s) where a new scene was detected only by sparse
        detectors, otherwise it is the same.

        Returns:
            List of pairs of FrameTimecode objects denoting the detected scenes.
        """
        if base_timecode is None:
            base_timecode = self._base_timecode
        if base_timecode is None:
            return []
        return [(base_timecode + start, base_timecode + end) for start, end in self._event_list]

    def _process_frame(self,
                       frame_num: int,
                       frame_im: np.ndarray,
                       callback: Optional[Callable[[np.ndarray, int], None]] = None) -> None:
        """ Adds any cuts detected with the current frame to the cutting list. """
        for detector in self._detector_list:
            cuts = detector.process_frame(frame_num, frame_im)
            if cuts and callback:
                callback(frame_im, frame_num)
            self._cutting_list += cuts
        for detector in self._sparse_detector_list:
            events = detector.process_frame(frame_num, frame_im)
            if events and callback:
                callback(frame_im, frame_num)
            self._event_list += events

    def _is_processing_required(self, frame_num: int) -> bool:
        """ Is Processing Required: Returns True if frame metrics not in StatsManager,
        False otherwise. """
        if self.stats_manager is None:
            return True
        return all([detector.is_processing_required(frame_num) for detector in self._detector_list])

    def _post_process(self, frame_num: int) -> None:
        """ Adds any remaining cuts to the cutting list after processing the last frame. """
        for detector in self._detector_list:
            self._cutting_list += detector.post_process(frame_num)

    def detect_scenes(self,
                      video: VideoStream,
                      duration: Optional[FrameTimecode] = None,
                      end_time: Optional[FrameTimecode] = None,
                      frame_skip: int = 0,
                      show_progress: bool = False,
                      callback: Optional[Callable[[np.ndarray, int], None]] = None):
        """ Perform scene detection on the given video using the added SceneDetectors.

        Blocks until all frames in the video have been processed. Results can
        be obtained by calling either the get_scene_list() or get_cut_list() methods.
        Video decoding is performed in a background thread to allow scene detection and
        frame decoding to happen in parallel.

        Arguments:
            video: A VideoStream object pointing.
            duration: Maximum amount of frames to detect. If not specified,
                stream will be processed until end. Cannot be specified if `end_time` is set.
            end_time: Last frame number to process. If not specified,
                stream will be processed until end. Cannot be specified if `duration` is set.
            frame_skip: Not recommended except for extremely high framerate videos.
                Number of frames to skip (i.e. process every 1 in N+1 frames,
                where N is frame_skip, processing only 1/N+1 percent of the video,
                speeding up the detection time at the expense of accuracy).
                `frame_skip` **must** be 0 (the default) when using a StatsManager.
            show_progress: If True, and the ``tqdm`` module is available, displays
                a progress bar with the progress, framerate, and expected time to
                complete processing the video frame source.
            callback: If set, called after each scene/event detected.
                TODO(v1.0): Update signature.
        Returns:
            int: Number of frames read and processed from the frame source.
        Raises:
            ValueError: `frame_skip` **must** be 0 (the default) if the SceneManager
                was constructed with a StatsManager object.
        """

        if frame_skip > 0 and self.stats_manager is not None:
            raise ValueError('frame_skip must be 0 when using a StatsManager.')
        if duration is not None and end_time is not None:
            raise ValueError('duration and end_time cannot be set at the same time!')
        if duration is not None and duration < 0:
            raise ValueError('duration must be greater than or equal to 0!')
        if end_time is not None and end_time < 0:
            raise ValueError('end_time must be greater than or equal to 0!')

        self._base_timecode = video.base_timecode
        start_frame_num: int = video.frame_number

        if duration is not None:
            end_time = duration + start_frame_num

        if end_time is not None:
            end_time = self._base_timecode + end_time

        # Can only calculate total number of frames we expect to process if the duration of
        # the video is available.
        total_frames = 0
        if video.duration is not None:
            if end_time is not None and end_time < video.duration:
                total_frames = (end_time - start_frame_num) + 1
            else:
                total_frames = (video.duration.get_frames() - start_frame_num)

        # Calculate the desired downscale factor and log the effective resolution.
        if self.auto_downscale:
            downscale_factor = compute_downscale_factor(frame_width=video.frame_size[0])
        else:
            downscale_factor = self.downscale
        if downscale_factor > 1:
            logger.info('Downscale factor set to %d, effective resolution: %d x %d',
                        downscale_factor, video.frame_size[0] // downscale_factor,
                        video.frame_size[1] // downscale_factor)

        progress_bar = None
        if tqdm and show_progress:
            progress_bar = tqdm(total=int(total_frames), unit='frames', dynamic_ncols=True)

        frame_queue = queue.Queue(MAX_FRAME_QUEUE_LENGTH)
        decode_thread = threading.Thread(
            target=SceneManager._decode_thread,
            args=(self, video, frame_skip, downscale_factor, end_time, frame_queue),
            daemon=True)
        decode_thread.start()
        frame_im = None
        while True:
            next_frame, position = frame_queue.get()
            if next_frame is None and position is None:
                break
            if not next_frame is None:
                frame_im = next_frame
            self._process_frame(position.frame_num, frame_im, callback)
            if progress_bar:
                progress_bar.update(1 + frame_skip)

        decode_thread.join()

        if self._start_pos is None:
            self._start_pos = video.position
        self._last_pos = video.base_timecode + video.frame_number
        self._post_process(video.position.frame_num)
        return video.frame_number - start_frame_num

    def _decode_thread(self, video, frame_skip, downscale_factor, end_time, out_queue):
        try:
            while True:
                frame_im = None
                # We don't do any kind of locking here since the worst-case of this being wrong
                # is that we do some extra work, and this function should never mutate any data
                # (all of which should be modified under the GIL).
                if (self._is_processing_required(video.position.frame_num)):
                    frame_im = video.read()
                    if frame_im is False:
                        break
                    if downscale_factor > 1:
                        frame_im = frame_im[::downscale_factor, ::downscale_factor, :]
                else:
                    if video.read(decode=False) is False:
                        break

                out_queue.put((frame_im, video.position))

                if self._start_pos is None:
                    self._start_pos = video.position

                if frame_skip > 0:
                    for _ in range(frame_skip):
                        if not video.read(decode=False):
                            break

                if end_time is not None and video.position >= end_time:
                    break

        except Exception as ex:
            logger.critical('Fatal error: Exception raised in decode thread:\n%s', str(ex))
            out_queue.put((None, None))
            raise
        except:
            logger.critical('Fatal error: Unknown exception raised in decode thread.')
            out_queue.put((None, None))
            raise

        out_queue.put((None, None))
