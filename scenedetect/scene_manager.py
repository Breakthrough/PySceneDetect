#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""``scenedetect.scene_manager`` Module

This module implements :class:`SceneManager`, coordinates running a
:mod:`SceneDetector <scenedetect.detectors>` over the frames of a video
(:mod:`VideoStream <scenedetect.video_stream>`). Video decoding is done in a separate thread to
improve performance.

===============================================================
Usage
===============================================================

The following example shows basic usage of a :class:`SceneManager`:

.. code:: python

    from scenedetect import open_video, SceneManager, ContentDetector
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    # Detect all scenes in video from current position to end.
    scene_manager.detect_scenes(video)
    # `get_scene_list` returns a list of start/end timecode pairs
    # for each scene that was found.
    scenes = scene_manager.get_scene_list()

An optional callback can also be invoked on each detected scene, for example:

.. code:: python

    from scenedetect import open_video, SceneManager, ContentDetector

    # Callback to invoke on the first frame of every new scene detection.
    def on_new_scene(frame_img: numpy.ndarray, frame_num: int):
        print("New scene found at frame %d." % frame_num)

    video = open_video(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video, callback=on_new_scene)

To use a `SceneManager` with a webcam/device or existing `cv2.VideoCapture` device, use the
:class:`VideoCaptureAdapter <scenedetect.backends.opencv.VideoCaptureAdapter>` instead of
`open_video`.

=======================================================================
Storing Per-Frame Statistics
=======================================================================

`SceneManager` can use an optional
:class:`StatsManager <scenedetect.stats_manager.StatsManager>` to save frame statistics to disk:

.. code:: python

    from scenedetect import open_video, ContentDetector, SceneManager, StatsManager
    video = open_video(test_video_file)
    scene_manager = SceneManager(stats_manager=StatsManager())
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()
    print_scenes(scene_list=scene_list)
    # Save per-frame statistics to disk.
    scene_manager.stats_manager.save_to_csv(csv_file=STATS_FILE_PATH)

The statsfile can be used to find a better threshold for certain inputs, or perform statistical
analysis of the video.
"""

import logging
import queue
import sys
import threading
import typing as ty

import cv2
import numpy as np

from scenedetect.common import (
    _USE_PTS_IN_DEVELOPMENT,
    CropRegion,
    CutList,
    FrameTimecode,
    Interpolation,
    SceneList,
)
from scenedetect.detector import SceneDetector
from scenedetect.platform import tqdm
from scenedetect.stats_manager import StatsManager
from scenedetect.video_stream import VideoStream

logger = logging.getLogger("pyscenedetect")

# TODO: This value can and should be tuned for performance improvements as much as possible,
# until accuracy falls, on a large enough dataset. This has yet to be done, but the current
# value doesn't seem to have caused any issues at least.
DEFAULT_MIN_WIDTH: int = 256
"""The default minimum width a frame will be downscaled to when calculating a downscale factor."""

MAX_FRAME_QUEUE_LENGTH: int = 4
"""Maximum number of decoded frames which can be buffered while waiting to be processed."""

MAX_FRAME_SIZE_ERRORS: int = 16
"""Maximum number of frame size error messages that can be logged."""

PROGRESS_BAR_DESCRIPTION = "  Detected: %d | Progress"
"""Template to use for progress bar."""


def compute_downscale_factor(frame_width: int, effective_width: int = DEFAULT_MIN_WIDTH) -> float:
    """Get the optimal default downscale factor based on a video's resolution (currently only
    the width in pixels is considered).

    The resulting effective width of the video will be between frame_width and 1.5 * frame_width
    pixels (e.g. if frame_width is 200, the range of effective widths will be between 200 and 300).

    Arguments:
        frame_width: Actual width of the video frame in pixels.
        effective_width: Desired minimum width in pixels.

    Returns:
        int: The default downscale factor to use to achieve at least the target effective_width.
    """
    assert frame_width > 0 and effective_width > 0
    if frame_width < effective_width:
        return 1
    return frame_width / float(effective_width)


def get_scenes_from_cuts(
    cut_list: CutList,
    start_pos: ty.Union[int, FrameTimecode],
    end_pos: ty.Union[int, FrameTimecode],
) -> SceneList:
    """Returns a list of tuples of start/end FrameTimecodes for each scene based on a
    list of detected scene cuts/breaks.

    This function is called when using the :meth:`SceneManager.get_scene_list` method.
    The scene list is generated from a cutting list (:meth:`SceneManager.get_cut_list`),
    noting that each scene is contiguous, starting from the first to last frame of the input.
    If `cut_list` is empty, the resulting scene will span from `start_pos` to `end_pos`.

    Arguments:
        cut_list: List of FrameTimecode objects where scene cuts/breaks occur.
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
        scene_list.append((start_pos, end_pos))
        return scene_list
    # Initialize last_cut to the first frame we processed,as it will be
    # the start timecode for the first scene in the list.
    last_cut = start_pos
    for cut in cut_list:
        scene_list.append((last_cut, cut))
        last_cut = cut
    # Last scene is from last cut to end of video.
    scene_list.append((last_cut, end_pos))

    return scene_list


##
## SceneManager Class Implementation
##


class SceneManager:
    """The SceneManager facilitates detection of scenes (:meth:`detect_scenes`) on a video
    (:class:`VideoStream <scenedetect.video_stream.VideoStream>`) using a detector
    (:meth:`add_detector`). Video decoding is done in parallel in a background thread.
    """

    def __init__(
        self,
        stats_manager: ty.Optional[StatsManager] = None,
    ):
        """
        Arguments:
            stats_manager: :class:`StatsManager` to bind to this `SceneManager`. Can be
                accessed via the `stats_manager` property of the resulting object to save to disk.
        """
        self._cutting_list: ty.List[FrameTimecode] = []
        self._detector_list: ty.List[SceneDetector] = []
        # TODO(v1.0): This class should own a StatsManager instead of taking an optional one.
        # Expose a new `stats_manager` @property from the SceneManager, and either change the
        # `stats_manager` argument to to `store_stats: bool=False`, or lazy-init one.

        # TODO(v1.0): This class should own a VideoStream as well, instead of passing one
        # to the detect_scenes method. If concatenation is required, it can be implemented as
        # a generic VideoStream wrapper.
        self._stats_manager: ty.Optional[StatsManager] = stats_manager

        # Position of video that was first passed to detect_scenes.
        self._start_pos: FrameTimecode = None
        # Position of video on the last frame processed by detect_scenes.
        self._last_pos: FrameTimecode = None
        # Size of the decoded frames.
        self._frame_size: ty.Tuple[int, int] = None
        self._frame_size_errors: int = 0
        self._base_timecode: ty.Optional[FrameTimecode] = None
        self._downscale: int = 1
        self._auto_downscale: bool = True
        # Interpolation method to use when downscaling. Defaults to linear interpolation
        # as a good balance between quality and performance.
        self._interpolation: Interpolation = Interpolation.LINEAR
        # Boolean indicating if we have only seen EventType.CUT events so far.
        self._only_cuts: bool = True
        # Set by decode thread when an exception occurs.
        self._exception_info = None
        self._stop = threading.Event()

        self._frame_buffer = []
        self._frame_buffer_size = 0
        self._crop = None

    @property
    def interpolation(self) -> Interpolation:
        """Interpolation method to use when downscaling frames. Must be one of cv2.INTER_*."""
        return self._interpolation

    @interpolation.setter
    def interpolation(self, value: Interpolation):
        self._interpolation = value

    @property
    def stats_manager(self) -> ty.Optional[StatsManager]:
        """Getter for the StatsManager associated with this SceneManager, if any."""
        return self._stats_manager

    @property
    def crop(self) -> ty.Optional[CropRegion]:
        """Portion of the frame to crop. Tuple of 4 ints in the form (X0, Y0, X1, Y1) where X0, Y0
        describes one point and X1, Y1 is another which describe a rectangle inside of the frame.
        Coordinates start from 0 and are inclusive. For example, with a 100x100 pixel video,
        (0, 0, 99, 99) covers the entire frame."""
        if self._crop is None:
            return None
        (x0, y0, x1, y1) = self._crop
        return (x0, y0, x1 - 1, y1 - 1)

    @crop.setter
    def crop(self, value: CropRegion):
        """Raises:
        ValueError: All coordinates must be >= 0.
        """
        if value is None:
            self._crop = None
            return
        if not (len(value) == 4 and all(isinstance(v, int) for v in value)):
            raise TypeError("crop region must be tuple of 4 ints")
        # Verify that the provided crop results in a non-empty portion of the frame.
        if any(coordinate < 0 for coordinate in value):
            raise ValueError("crop coordinates must be >= 0")
        (x0, y0, x1, y1) = value
        # Internally we store the value in the form used to de-reference the image, which must be
        # one-past the end.
        self._crop = (min(x0, x1), min(y0, y1), max(x0, x1) + 1, max(y0, y1) + 1)

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
        """Add/register a SceneDetector (e.g. ContentDetector, ThresholdDetector) to
        run when detect_scenes is called. The SceneManager owns the detector object,
        so a temporary may be passed.

        Arguments:
            detector (SceneDetector): Scene detector to add to the SceneManager.
        """
        if self._stats_manager is None and detector.stats_manager_required():
            assert not self._detector_list
            self._stats_manager = StatsManager()

        detector.stats_manager = self._stats_manager
        if self._stats_manager is not None:
            self._stats_manager.register_metrics(detector.get_metrics())

        self._detector_list.append(detector)

        self._frame_buffer_size = max(detector.event_buffer_length, self._frame_buffer_size)

    def get_num_detectors(self) -> int:
        """Get number of registered scene detectors added via add_detector."""
        return len(self._detector_list)

    def clear(self) -> None:
        """Clear all cuts/scenes and resets the SceneManager's position.

        Any statistics generated are still saved in the StatsManager object passed to the
        SceneManager's constructor, and thus, subsequent calls to detect_scenes, using the same
        frame source seeked back to the original time (or beginning of the video) will use the
        cached frame metrics that were computed and saved in the previous call to detect_scenes.
        """
        self._cutting_list.clear()
        self._last_pos = None
        self._start_pos = None
        self._frame_size = None
        self.clear_detectors()

    def clear_detectors(self) -> None:
        """Remove all scene detectors added to the SceneManager via add_detector()."""
        self._detector_list.clear()

    def get_scene_list(self, start_in_scene: bool = False) -> SceneList:
        """Return a list of tuples of start/end FrameTimecodes for each detected scene.

        Arguments:
            start_in_scene: Assume the video begins in a scene. This means that when detecting
                fast cuts with `ContentDetector`, if no cuts are found, the resulting scene list
                will contain a single scene spanning the entire video (instead of no scenes).
                When detecting fades with `ThresholdDetector`, the beginning portion of the video
                will always be included until the first fade-out event is detected.

        Returns:
            List of tuples in the form (start_time, end_time), where both start_time and
            end_time are FrameTimecode objects representing the exact time/frame where each
            detected scene in the video begins and ends.
        """
        if self._base_timecode is None:
            return []
        cut_list = self._get_cutting_list()
        scene_list = get_scenes_from_cuts(
            cut_list=cut_list, start_pos=self._start_pos, end_pos=self._last_pos + 1
        )
        # If we didn't actually detect any cuts, make sure the resulting scene_list is empty
        # unless start_in_scene is True.
        if not cut_list and not start_in_scene:
            scene_list = []
        return sorted(scene_list)

    def _get_cutting_list(self) -> ty.List[FrameTimecode]:
        """Return a sorted list of unique frame numbers of any detected scene cuts."""
        if not self._cutting_list:
            return []
        # Ensure all cuts are unique by using a set to remove all duplicates.
        return [cut for cut in sorted(set(self._cutting_list))]

    def _process_frame(
        self,
        position: FrameTimecode,
        frame_im: np.ndarray,
        callback: ty.Optional[ty.Callable[[np.ndarray, int], None]] = None,
    ) -> bool:
        """Add any cuts detected with the current frame to the cutting list. Returns True if any new
        cuts were detected, False otherwise."""
        new_cuts = False
        # TODO(#283): This breaks with AdaptiveDetector as cuts differ from the frame number
        # being processed. Allow detectors to specify the max frame lookahead they require
        # (i.e. any event will never be more than N frames behind the current one).
        self._frame_buffer.append(frame_im)
        # frame_buffer[-1] is current frame, -2 is one behind, etc
        # so index based on cut frame should be [event_frame - (frame_num + 1)]
        self._frame_buffer = self._frame_buffer[-(self._frame_buffer_size + 1) :]
        for detector in self._detector_list:
            cuts = detector.process_frame(position, frame_im)
            self._cutting_list += cuts
            new_cuts = True if cuts else False
            # TODO: Support callbacks with PTS.
            if callback:
                if _USE_PTS_IN_DEVELOPMENT:
                    raise NotImplementedError()
                for cut in cuts:
                    buffer_index = cut.frame_num - (position.frame_num + 1)
                    callback(self._frame_buffer[buffer_index], cut.frame_num)
        return new_cuts

    def _post_process(self, timecode: FrameTimecode) -> None:
        """Add remaining cuts to the cutting list, after processing the last frame."""
        for detector in self._detector_list:
            self._cutting_list += detector.post_process(timecode)

    def stop(self) -> None:
        """Stop the current :meth:`detect_scenes` call, if any. Thread-safe."""
        self._stop.set()

    def detect_scenes(
        self,
        video: VideoStream = None,
        duration: ty.Optional[FrameTimecode] = None,
        end_time: ty.Optional[FrameTimecode] = None,
        frame_skip: int = 0,
        show_progress: bool = False,
        callback: ty.Optional[ty.Callable[[np.ndarray, int], None]] = None,
        frame_source: ty.Optional[VideoStream] = None,
    ) -> int:
        """Perform scene detection on the given video using the added SceneDetectors, returning the
        number of frames processed. Results can be obtained by calling :meth:`get_scene_list` or
        :meth:`get_cut_list`.

        Video decoding is performed in a background thread to allow scene detection and frame
        decoding to happen in parallel. Detection will continue until no more frames are left,
        the specified duration or end time has been reached, or :meth:`stop` was called.

        Arguments:
            video: VideoStream obtained from either `scenedetect.open_video`, or by creating
                one directly (e.g. `scenedetect.backends.opencv.VideoStreamCv2`).
            duration: Amount of time to detect from current video position. Cannot be
                specified if `end_time` is set.
            end_time: Time to stop processing at. Cannot be specified if `duration` is set.
            frame_skip: Not recommended except for extremely high framerate videos.
                Number of frames to skip (i.e. process every 1 in N+1 frames,
                where N is frame_skip, processing only 1/N+1 percent of the video,
                speeding up the detection time at the expense of accuracy).
                `frame_skip` **must** be 0 (the default) when using a StatsManager.
            show_progress: If True, and the ``tqdm`` module is available, displays
                a progress bar with the progress, framerate, and expected time to
                complete processing the video frame source.
            callback: If set, called after each scene/event detected.
            frame_source: [DEPRECATED] DO NOT USE. For compatibility with previous version.
        Returns:
            int: Number of frames read and processed from the frame source.
        Raises:
            ValueError: `frame_skip` **must** be 0 (the default) if the SceneManager
                was constructed with a StatsManager object.
        """
        # TODO(v0.7): Add DeprecationWarning that `frame_source` will be removed in v0.8.
        if frame_source is not None:
            video = frame_source
        # TODO(v0.8): Remove default value for `video` after `frame_source` is removed.
        if video is None:
            raise TypeError("detect_scenes() missing 1 required positional argument: 'video'")
        if frame_skip > 0 and self.stats_manager is not None:
            raise ValueError("frame_skip must be 0 when using a StatsManager.")
        if duration is not None and end_time is not None:
            raise ValueError("duration and end_time cannot be set at the same time!")
        # TODO: These checks should be handled by the FrameTimecode constructor.
        if duration is not None and isinstance(duration, (int, float)) and duration < 0:
            raise ValueError("duration must be greater than or equal to 0!")
        if end_time is not None and isinstance(end_time, (int, float)) and end_time < 0:
            raise ValueError("end_time must be greater than or equal to 0!")

        effective_frame_size = video.frame_size
        if self._crop:
            logger.debug(f"Crop set: top left = {self.crop[0:2]}, bottom right = {self.crop[2:4]}")
            x0, y0, x1, y1 = self._crop
            min_x, min_y = (min(x0, x1), min(y0, y1))
            max_x, max_y = (max(x0, x1), max(y0, y1))
            frame_width, frame_height = video.frame_size
            if min_x >= frame_width or min_y >= frame_height:
                raise ValueError("crop starts outside video boundary")
            if max_x >= frame_width or max_y >= frame_height:
                logger.warning("Warning: crop ends outside of video boundary.")
            effective_frame_size = (
                1 + min(max_x, frame_width) - min_x,
                1 + min(max_y, frame_height) - min_y,
            )
        # Calculate downscale factor and log effective resolution.
        if self.auto_downscale:
            downscale_factor = compute_downscale_factor(max(effective_frame_size))
        else:
            downscale_factor = self.downscale
        logger.debug(
            "Processing resolution: %d x %d, downscale: %1.1f",
            int(effective_frame_size[0] / downscale_factor),
            int(effective_frame_size[1] / downscale_factor),
            downscale_factor,
        )

        self._base_timecode = video.base_timecode

        # TODO: Figure out a better solution for communicating framerate to StatsManager.
        if self._stats_manager is not None:
            self._stats_manager._base_timecode = self._base_timecode

        start_frame_num: int = video.frame_number
        if end_time is not None:
            end_time = self._base_timecode + end_time
        elif duration is not None:
            end_time = (self._base_timecode + duration) + start_frame_num

        total_frames = 0
        if video.duration is not None:
            if end_time is not None and end_time < video.duration:
                total_frames = end_time - start_frame_num
            else:
                total_frames = video.duration.get_frames() - start_frame_num

        progress_bar = None
        if show_progress:
            progress_bar = tqdm(
                total=int(total_frames),
                unit="frames",
                desc=PROGRESS_BAR_DESCRIPTION % 0,
                dynamic_ncols=True,
            )

        frame_queue = queue.Queue(MAX_FRAME_QUEUE_LENGTH)
        self._stop.clear()
        decode_thread = threading.Thread(
            target=SceneManager._decode_thread,
            args=(self, video, frame_skip, downscale_factor, end_time, frame_queue),
            daemon=True,
        )
        decode_thread.start()
        frame_im = None

        logger.info("Detecting scenes...")
        while not self._stop.is_set():
            next_frame, position = frame_queue.get()
            if next_frame is None and position is None:
                break
            if next_frame is not None:
                frame_im = next_frame
            new_cuts = self._process_frame(position, frame_im, callback)
            if progress_bar is not None:
                if new_cuts:
                    progress_bar.set_description(
                        PROGRESS_BAR_DESCRIPTION % len(self._cutting_list), refresh=False
                    )
                progress_bar.update(1 + frame_skip)

        if progress_bar is not None:
            progress_bar.set_description(
                PROGRESS_BAR_DESCRIPTION % len(self._cutting_list), refresh=True
            )
            progress_bar.close()
        # Unblock any puts in the decode thread before joining. This can happen if the main
        # processing thread stops before the decode thread.
        while not frame_queue.empty():
            frame_queue.get_nowait()
        decode_thread.join()

        if self._exception_info is not None:
            raise self._exception_info[1].with_traceback(self._exception_info[2])

        self._last_pos = video.position
        self._post_process(video.position)

        return video.frame_number - start_frame_num

    def _decode_thread(
        self,
        video: VideoStream,
        frame_skip: int,
        downscale_factor: float,
        end_time: FrameTimecode,
        out_queue: queue.Queue,
    ):
        try:
            while not self._stop.is_set():
                frame_im = None
                # We don't do any kind of locking here since the worst-case of this being wrong
                # is that we do some extra work, and this function should never mutate any data
                # (all of which should be modified under the GIL).
                frame_im = video.read()
                if frame_im is False:
                    break
                # Verify the decoded frame size against the video container's reported
                # resolution, and also verify that consecutive frames have the correct size.
                decoded_size = (frame_im.shape[1], frame_im.shape[0])
                if self._frame_size is None:
                    self._frame_size = decoded_size
                    if video.frame_size != decoded_size:
                        logger.warn(
                            f"WARNING: Decoded frame size ({decoded_size}) does not match "
                            f" video resolution {video.frame_size}, possible corrupt input."
                        )
                elif self._frame_size != decoded_size:
                    self._frame_size_errors += 1
                    if self._frame_size_errors <= MAX_FRAME_SIZE_ERRORS:
                        logger.error(
                            f"ERROR: Frame at {str(video.position)} has incorrect size and "
                            f"cannot be processed: decoded size = {decoded_size}, "
                            f"expected = {self._frame_size}. Video may be corrupt."
                        )
                    if self._frame_size_errors == MAX_FRAME_SIZE_ERRORS:
                        logger.warn("WARNING: Too many errors emitted, skipping future messages.")
                    # Skip processing frames that have an incorrect size.
                    continue

                if self._crop:
                    (x0, y0, x1, y1) = self._crop
                    frame_im = frame_im[y0:y1, x0:x1]

                if downscale_factor > 1.0:
                    frame_im = cv2.resize(
                        frame_im,
                        (
                            max(1, round(frame_im.shape[1] / downscale_factor)),
                            max(1, round(frame_im.shape[0] / downscale_factor)),
                        ),
                        interpolation=self._interpolation.value,
                    )

                # Set the start position now that we decoded at least the first frame.
                if self._start_pos is None:
                    self._start_pos = video.position

                out_queue.put((frame_im, video.position))

                if frame_skip > 0:
                    for _ in range(frame_skip):
                        if not video.read(decode=False):
                            break
                # End time includes the presentation time of the frame, but the `position`
                # property of a VideoStream references the beginning of the frame in time.
                if end_time is not None and not (video.position + 1) < end_time:
                    break

        # If *any* exceptions occur, we re-raise them in the main thread so that the caller of
        # detect_scenes can handle it.
        except KeyboardInterrupt:
            logger.debug("Received KeyboardInterrupt.")
            self._stop.set()
        except BaseException:
            logger.critical("Fatal error: Exception raised in decode thread.")
            self._exception_info = sys.exc_info()
            self._stop.set()

        finally:
            # Handle case where start position was never set if we did not decode any frames.
            if self._start_pos is None:
                self._start_pos = video.position
            # Make sure main thread stops processing loop.
            out_queue.put((None, None))

    #
    # Deprecated Methods
    #

    def get_cut_list(
        self,
        show_warning: bool = True,
    ) -> CutList:
        """[DEPRECATED] Return a list of FrameTimecodes of the detected scene changes/cuts.

        Unlike get_scene_list, the cutting list returns a list of FrameTimecodes representing
        the point in the input video where a new scene was detected, and thus the frame
        where the input should be cut/split. The cutting list, in turn, is used to generate
        the scene list, noting that each scene is contiguous starting from the first frame
        and ending at the last frame detected.

        Arguments:
            show_warning: If set to False, suppresses the error from being warned. In v0.7,
                this will have no effect and the error will become a Python warning.

        Returns:
            List of FrameTimecode objects denoting the points in time where a scene change
            was detected in the input video, which can also be passed to external tools
            for automated splitting of the input into individual scenes.

        :meta private:
        """
        # TODO(v0.7): Use the warnings module to turn this into a warning.
        if show_warning:
            logger.error("`get_cut_list()` is deprecated and will be removed in a future release.")
        return self._get_cutting_list()
