# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2020 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
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
SceneDetectors and frame sources (:py:class:`VideoManager <scenedetect.video_manager.VideoManager>`
or ``cv2.VideoCapture``).  This includes creating a cut list (see
:py:meth:`SceneManager.get_cut_list`) and event list (see :py:meth:`SceneManager.get_event_list`)
of all changes in scene, which is used to generate a final list of scenes (see
:py:meth:`SceneManager.get_scene_list`) in the form of a list of start/end
:py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>` objects at each scene boundary.

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

# Standard Library Imports
from __future__ import print_function
from string import Template
import math

# Third-Party Library Imports
import cv2
from scenedetect.platform import tqdm
from scenedetect.platform import get_and_create_path

# PySceneDetect Library Imports
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.platform import get_csv_writer
from scenedetect.platform import get_cv2_imwrite_params
from scenedetect.stats_manager import FrameMetricRegistered
from scenedetect.scene_detector import SparseSceneDetector

from scenedetect.thirdparty.simpletable import SimpleTableCell, SimpleTableImage
from scenedetect.thirdparty.simpletable import SimpleTableRow, SimpleTable, HTMLPage



##
## SceneManager Helper Functions
##

def get_scenes_from_cuts(cut_list, base_timecode, num_frames, start_frame=0):
    # type: List[FrameTimecode], FrameTimecode, Union[int, FrameTimecode],
    #       Optional[Union[int, FrameTimecode]] -> List[Tuple[FrameTimecode, FrameTimecode]]
    """ Returns a list of tuples of start/end FrameTimecodes for each scene based on a
    list of detected scene cuts/breaks.

    This function is called when using the :py:meth:`SceneManager.get_scene_list` method.
    The scene list is generated from a cutting list (:py:meth:`SceneManager.get_cut_list`),
    noting that each scene is contiguous, starting from the first to last frame of the input.


    Arguments:
        cut_list (List[FrameTimecode]): List of FrameTimecode objects where scene cuts/breaks occur.
        base_timecode (FrameTimecode): The base_timecode of which all FrameTimecodes in the cut_list
            are based on.
        num_frames (int or FrameTimecode): The number of frames, or FrameTimecode representing
            duration, of the video that was processed (used to generate last scene's end time).
        start_frame (int or FrameTimecode): The start frame or FrameTimecode of the cut list.
            Used to generate the first scene's start time.
    Returns:
        List of tuples in the form (start_time, end_time), where both start_time and
        end_time are FrameTimecode objects representing the exact time/frame where each
        scene occupies based on the input cut_list.
    """
    # Scene list, where scenes are tuples of (Start FrameTimecode, End FrameTimecode).
    scene_list = []
    if not cut_list:
        scene_list.append((base_timecode + start_frame, base_timecode + start_frame + num_frames))
        return scene_list
    # Initialize last_cut to the first frame we processed,as it will be
    # the start timecode for the first scene in the list.
    last_cut = base_timecode + start_frame
    for cut in cut_list:
        scene_list.append((last_cut, cut))
        last_cut = cut
    # Last scene is from last cut to end of video.
    scene_list.append((last_cut, base_timecode + start_frame + num_frames))

    return scene_list


def write_scene_list(output_csv_file, scene_list, cut_list=None):
    # type: (File, List[Tuple[FrameTimecode, FrameTimecode]], Optional[List[FrameTimecode]]) -> None
    """ Writes the given list of scenes to an output file handle in CSV format.

    Arguments:
        output_csv_file: Handle to open file in write mode.
        scene_list: List of pairs of FrameTimecodes denoting each scene's start/end FrameTimecode.
        cut_list: Optional list of FrameTimecode objects denoting the cut list (i.e. the frames
            in the video that need to be split to generate individual scenes). If not passed,
            the start times of each scene (besides the 0th scene) is used instead.
    """
    csv_writer = get_csv_writer(output_csv_file)
    # Output Timecode List
    csv_writer.writerow(
        ["Timecode List:"] +
        cut_list if cut_list else [start.get_timecode() for start, _ in scene_list[1:]])
    csv_writer.writerow([
        "Scene Number",
        "Start Frame", "Start Timecode", "Start Time (seconds)",
        "End Frame", "End Timecode", "End Time (seconds)",
        "Length (frames)", "Length (timecode)", "Length (seconds)"])
    for i, (start, end) in enumerate(scene_list):
        duration = end - start
        csv_writer.writerow([
            '%d' % (i+1),
            '%d' % start.get_frames(), start.get_timecode(), '%.3f' % start.get_seconds(),
            '%d' % end.get_frames(), end.get_timecode(), '%.3f' % end.get_seconds(),
            '%d' % duration.get_frames(), duration.get_timecode(), '%.3f' % duration.get_seconds()])


def write_scene_list_html(output_html_filename, scene_list, cut_list=None, css=None,
                          css_class='mytable', image_filenames=None, image_width=None,
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
    timecode_table = SimpleTable([["Timecode List:"] +
                                  (cut_list if cut_list else
                                   [start.get_timecode() for start, _ in scene_list[1:]])],
                                 css_class=css_class)

    # Output list of scenes
    header_row = ["Scene Number", "Start Frame", "Start Timecode", "Start Time (seconds)",
                  "End Frame", "End Timecode", "End Time (seconds)",
                  "Length (frames)", "Length (timecode)", "Length (seconds)"]
    for i, (start, end) in enumerate(scene_list):
        duration = end - start

        row = SimpleTableRow([
            '%d' % (i+1),
            '%d' % start.get_frames(), start.get_timecode(), '%.3f' % start.get_seconds(),
            '%d' % end.get_frames(), end.get_timecode(), '%.3f' % end.get_seconds(),
            '%d' % duration.get_frames(), duration.get_timecode(), '%.3f' % duration.get_seconds()])

        if image_filenames:
            for image in image_filenames[i]:
                row.add_cell(SimpleTableCell(SimpleTableImage(
                    image, width=image_width, height=image_height)))

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
# TODO - Add a method to scene_manager called save_images which calls this function.
#
def generate_images(scene_list, video_manager, video_name, num_images=2,
                    image_extension='jpg', quality_or_compression=95,
                    image_name_template='$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER',
                    output_dir=None, downscale_factor=1, show_progress=False):
    # type: (...) -> bool
    """

    TODO: Documentation.

    Arguments:
        quality_or_compression: For image_extension=jpg or webp, represents encoding quality,
        from 0-100 (higher indicates better quality). For WebP, 100 indicates lossless.
        Default value in the CLI is 95 for JPEG, and 100 for WebP.

        If image_extension=png, represents the compression rate, from 0-9. Higher values
        produce smaller files but result in longer compression time. This setting does not
        affect image quality (lossless PNG), only file size. Default value in the CLI is 3.

        [default: 95]

    Returns:
        True if all requested images were generated & saved successfully, False otherwise.

    """

    if not scene_list:
        return True
    if num_images <= 0:
        raise ValueError()

    imwrite_param = []
    available_extensions = get_cv2_imwrite_params()
    if quality_or_compression is not None:
        if image_extension in available_extensions:
            imwrite_param = [available_extensions[image_extension], quality_or_compression]
        else:
            valid_extensions = str(list(available_extensions.keys()))
            raise RuntimeError(
                'Invalid image extension, must be one of (case-sensitive): %s' %
                valid_extensions)

    # Reset video manager and downscale factor.
    video_manager.release()
    video_manager.reset()
    video_manager.set_downscale_factor(downscale_factor)
    video_manager.start()

    # Setup flags and init progress bar if available.
    completed = True
    progress_bar = None
    if tqdm and show_progress:
        progress_bar = tqdm(
            total=len(scene_list) * num_images, unit='images')

    filename_template = Template(image_name_template)

    scene_num_format = '%0'
    scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + 'd'
    image_num_format = '%0'
    image_num_format += str(math.floor(math.log(num_images, 10)) + 2) + 'd'

    timecode_list = dict()

    for i in range(len(scene_list)):
        timecode_list[i] = []

    if num_images == 1:
        for i, (start_time, end_time) in enumerate(scene_list):
            duration = end_time - start_time
            timecode_list[i].append(start_time + int(duration.get_frames() / 2))
    else:
        middle_images = num_images - 2
        for i, (start_time, end_time) in enumerate(scene_list):
            timecode_list[i].append(start_time)

            if middle_images > 0:
                duration = (end_time.get_frames() - 1) - start_time.get_frames()
                duration_increment = None
                duration_increment = int(duration / (middle_images + 1))
                for j in range(middle_images):
                    timecode_list[i].append(start_time + ((j+1) * duration_increment))
            # End FrameTimecode is always the same frame as the next scene's start_time
            # (one frame past the end), so we need to subtract 1 here.
            timecode_list[i].append(end_time - 1)

    for i in timecode_list:
        for j, image_timecode in enumerate(timecode_list[i]):
            video_manager.seek(image_timecode)
            video_manager.grab()
            ret_val, frame_im = video_manager.retrieve()
            if ret_val:
                file_path = '%s.%s' % (filename_template.safe_substitute(
                    VIDEO_NAME=video_name,
                    SCENE_NUMBER=scene_num_format % (i + 1),
                    IMAGE_NUMBER=image_num_format % (j + 1)),
                                       image_extension)
                cv2.imwrite(
                    get_and_create_path(file_path, output_dir),
                    frame_im, imwrite_param)
            else:
                completed = False
                break
            if progress_bar:
                progress_bar.update(1)

    return completed


##
## SceneManager Class Implementation
##

class SceneManager(object):
    """ The SceneManager facilitates detection of scenes via the :py:meth:`detect_scenes` method,
    given a video source (:py:class:`VideoManager <scenedetect.video_manager.VideoManager>`
    or cv2.VideoCapture), and SceneDetector algorithms added via the :py:meth:`add_detector` method.

    Can also optionally take a StatsManager instance during construction to cache intermediate
    scene detection calculations, making subsequent calls to :py:meth:`detect_scenes` much faster,
    allowing the cached values to be saved/loaded to/from disk, and also manually determining
    the optimal threshold values or other options for various detection algorithms.
    """

    def __init__(self, stats_manager=None):
        # type: (Optional[StatsManager])
        self._cutting_list = []
        self._event_list = []
        self._detector_list = []
        self._sparse_detector_list = []
        self._stats_manager = stats_manager
        self._num_frames = 0
        self._start_frame = 0


    def add_detector(self, detector):
        # type: (SceneDetector) -> None
        """ Adds/registers a SceneDetector (e.g. ContentDetector, ThresholdDetector) to
        run when detect_scenes is called. The SceneManager owns the detector object,
        so a temporary may be passed.

        Arguments:
            detector (SceneDetector): Scene detector to add to the SceneManager.
        """
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


    def get_num_detectors(self):
        # type: () -> int
        """ Gets number of registered scene detectors added via add_detector. """
        return len(self._detector_list)


    def clear(self):
        # type: () -> None
        """ Clears all cuts/scenes and resets the SceneManager's position.

        Any statistics generated are still saved in the StatsManager object
        passed to the SceneManager's constructor, and thus, subsequent
        calls to detect_scenes, using the same frame source reset at the
        initial time (if it is a VideoManager, use the reset() method),
        will use the cached frame metrics that were computed and saved
        in the previous call to detect_scenes.
        """
        self._cutting_list.clear()
        self._event_list.clear()
        self._num_frames = 0
        self._start_frame = 0


    def clear_detectors(self):
        # type: () -> None
        """ Removes all scene detectors added to the SceneManager via add_detector(). """
        self._detector_list.clear()
        self._sparse_detector_list.clear()


    def get_scene_list(self, base_timecode):
        # type: (FrameTimecode) -> List[Tuple[FrameTimecode, FrameTimecode]]
        """ Returns a list of tuples of start/end FrameTimecodes for each detected scene.

        The scene list is generated by combining the results of all sparse detectors with
        those from dense ones (i.e. combining the results of :py:meth:`get_cut_list`
        and :py:meth:`get_event_list`).

        Returns:
            List of tuples in the form (start_time, end_time), where both start_time and
            end_time are FrameTimecode objects representing the exact time/frame where each
            detected scene in the video begins and ends.
        """
        return sorted(self.get_event_list(base_timecode) + get_scenes_from_cuts(
            self.get_cut_list(base_timecode), base_timecode,
            self._num_frames, self._start_frame))


    def get_cut_list(self, base_timecode):
        # type: (FrameTimecode) -> List[FrameTimecode]
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

        return [FrameTimecode(cut, base_timecode)
                for cut in self._get_cutting_list()]


    def _get_cutting_list(self):
        # type: () -> list
        """ Returns a sorted list of unique frame numbers of any detected scene cuts. """
        # We remove duplicates here by creating a set then back to a list and sort it.
        return sorted(list(set(self._cutting_list)))


    def get_event_list(self, base_timecode):
        # type: (FrameTimecode) -> List[FrameTimecode]
        """ Returns a list of FrameTimecode pairs of the detected scenes by all sparse detectors.

        Unlike get_scene_list, the event list returns a list of FrameTimecodes representing
        the point in the input video(s) where a new scene was detected only by sparse
        detectors, otherwise it is the same.

        Returns:
            List of pairs of FrameTimecode objects denoting the detected scenes.
        """
        return [(base_timecode + start, base_timecode + end)
                for start, end in self._event_list]


    def _process_frame(self, frame_num, frame_im):
        # type(int, numpy.ndarray) -> None
        """ Adds any cuts detected with the current frame to the cutting list. """
        for detector in self._detector_list:
            self._cutting_list += detector.process_frame(frame_num, frame_im)
        for detector in self._sparse_detector_list:
            self._event_list += detector.process_frame(frame_num, frame_im)


    def _is_processing_required(self, frame_num):
        # type(int) -> bool
        """ Is Processing Required: Returns True if frame metrics not in StatsManager,
        False otherwise.
        """
        return all([detector.is_processing_required(frame_num) for detector in self._detector_list])


    def _post_process(self, frame_num):
        # type(int, numpy.ndarray) -> None
        """ Adds any remaining cuts to the cutting list after processing the last frame. """
        for detector in self._detector_list:
            self._cutting_list += detector.post_process(frame_num)

    def detect_scenes(self, frame_source, end_time=None, frame_skip=0,
                      show_progress=True):
        # type: (VideoManager, Union[int, FrameTimecode],
        #        Optional[Union[int, FrameTimecode]], Optional[bool]) -> int
        """ Perform scene detection on the given frame_source using the added SceneDetectors.

        Blocks until all frames in the frame_source have been processed. Results can
        be obtained by calling either the get_scene_list() or get_cut_list() methods.

        Arguments:
            frame_source (scenedetect.video_manager.VideoManager or cv2.VideoCapture):
                A source of frames to process (using frame_source.read() as in VideoCapture).
                VideoManager is preferred as it allows concatenation of multiple videos
                as well as seeking, by defining start time and end time/duration.
            end_time (int or FrameTimecode): Maximum number of frames to detect
                (set to None to detect all available frames). Only needed for OpenCV
                VideoCapture objects; for VideoManager objects, use set_duration() instead.
            frame_skip (int): Not recommended except for extremely high framerate videos.
                Number of frames to skip (i.e. process every 1 in N+1 frames,
                where N is frame_skip, processing only 1/N+1 percent of the video,
                speeding up the detection time at the expense of accuracy).
                `frame_skip` **must** be 0 (the default) when using a StatsManager.
            show_progress (bool): If True, and the ``tqdm`` module is available, displays
                a progress bar with the progress, framerate, and expected time to
                complete processing the video frame source.
        Returns:
            int: Number of frames read and processed from the frame source.
        Raises:
            ValueError: `frame_skip` **must** be 0 (the default) if the SceneManager
                was constructed with a StatsManager object.
        """

        if frame_skip > 0 and self._stats_manager is not None:
            raise ValueError('frame_skip must be 0 when using a StatsManager.')

        start_frame = 0
        curr_frame = 0
        end_frame = None

        total_frames = math.trunc(frame_source.get(cv2.CAP_PROP_FRAME_COUNT))

        start_time = frame_source.get(cv2.CAP_PROP_POS_FRAMES)
        if isinstance(start_time, FrameTimecode):
            start_frame = start_time.get_frames()
        elif start_time is not None:
            start_frame = int(start_time)
        self._start_frame = start_frame

        curr_frame = start_frame

        if isinstance(end_time, FrameTimecode):
            end_frame = end_time.get_frames()
        elif end_time is not None:
            end_frame = int(end_time)

        if end_frame is not None:
            total_frames = end_frame

        if start_frame is not None and not isinstance(start_time, FrameTimecode):
            total_frames -= start_frame

        if total_frames < 0:
            total_frames = 0

        progress_bar = None
        if tqdm and show_progress:
            progress_bar = tqdm(
                total=total_frames, unit='frames')
        try:

            while True:
                if end_frame is not None and curr_frame >= end_frame:
                    break
                # We don't compensate for frame_skip here as the frame_skip option
                # is not allowed when using a StatsManager - thus, processing is
                # *always* required for *all* frames when frame_skip > 0.
                if (self._is_processing_required(self._num_frames + start_frame)
                        or self._is_processing_required(self._num_frames + start_frame + 1)):
                    ret_val, frame_im = frame_source.read()
                else:
                    ret_val = frame_source.grab()
                    frame_im = None

                if not ret_val:
                    break
                self._process_frame(self._num_frames + start_frame, frame_im)

                curr_frame += 1
                self._num_frames += 1
                if progress_bar:
                    progress_bar.update(1)

                if frame_skip > 0:
                    for _ in range(frame_skip):
                        if not frame_source.grab():
                            break
                        curr_frame += 1
                        self._num_frames += 1
                        if progress_bar:
                            progress_bar.update(1)

            self._post_process(curr_frame)

            num_frames = curr_frame - start_frame

        finally:

            if progress_bar:
                progress_bar.close()

        return num_frames
