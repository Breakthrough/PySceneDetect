# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""":py:class:`VideoStreamCv2` provides an adapter for the OpenCV cv2.VideoCapture object.

Uses string identifier ``'opencv'``.
"""

from logging import getLogger
import math
from typing import Tuple, Union, Optional
import os.path

import cv2
from numpy import ndarray

from scenedetect.frame_timecode import FrameTimecode, MAX_FPS_DELTA
from scenedetect.platform import get_aspect_ratio, get_file_name
from scenedetect.video_stream import VideoStream, SeekError, VideoOpenFailure, FrameRateUnavailable

logger = getLogger('pyscenedetect')


class VideoStreamCv2(VideoStream):
    """OpenCV `cv2.VideoCapture` backend."""

    def __init__(
        self,
        path_or_device: Union[bytes, str, int],
        framerate: Optional[float] = None,
        max_decode_attempts: int = 5,
    ):
        """Open a video or device.

        Arguments:
            path_or_device: Path to video, or device ID as integer.
            framerate: If set, overrides the detected framerate.
            max_decode_attempts: Number of attempts to continue decoding the video
                after a frame fails to decode. This allows processing videos that
                have a few corrupted frames or metadata (in which case accuracy
                of detection algorithms may be lower). Once this limit is passed,
                decoding will stop and emit an error.

        Raises:
            OSError: file could not be found or access was denied
            VideoOpenFailure: video could not be opened (may be corrupted)
            ValueError: specified framerate is invalid
        """
        super().__init__()

        if framerate is not None and framerate < MAX_FPS_DELTA:
            raise ValueError('Specified framerate (%f) is invalid!' % framerate)

        self._path_or_device = path_or_device
        self._is_device = isinstance(self._path_or_device, int)

        # Initialized in _open_capture:
        self._cap = None # Reference to underlying cv2.VideoCapture object.
        self._frame_rate = None

        # VideoCapture state
        self._has_seeked = False
        self._has_grabbed = False
        self._max_decode_attempts = max_decode_attempts
        self._decode_failures = 0
        self._warning_displayed = False

        self._open_capture(framerate)

    #
    # Backend-Specific Methods/Properties
    #

    @property
    def capture(self) -> cv2.VideoCapture:
        """Returns reference to underlying VideoCapture object. Use with caution.

        Prefer to use this property only to take ownership of the underlying cv2.VideoCapture object
        backing this object. Seeking or using the read/grab methods through this property are
        unsupported and will leave this object in an inconsistent state.
        """
        return self._cap

    #
    # VideoStream Methods/Properties
    #

    BACKEND_NAME = 'opencv'
    """Unique name used to identify this backend."""

    @property
    def frame_rate(self) -> float:
        """Framerate in frames/sec."""
        return self._frame_rate

    @property
    def path(self) -> Union[bytes, str]:
        """Video or device path."""
        if self._is_device:
            return "Device %d" % self._path_or_device
        return self._path_or_device

    @property
    def name(self) -> Union[bytes, str]:
        """Name of the video, without extension, or device."""
        if self._is_device:
            return self.path
        file_name = get_file_name(self.path, include_extension=False)
        if '%' in file_name:
            # file_name is an image sequence, trim everything including/after the %.
            file_name = file_name[:file_name.rfind('%')]
        return file_name

    @property
    def is_seekable(self) -> bool:
        """True if seek() is allowed, False otherwise.

        Always False if opening a device/webcam."""
        return not self._is_device

    @property
    def frame_size(self) -> Tuple[int, int]:
        """Size of each video frame in pixels as a tuple of (width, height)."""
        return (math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    @property
    def duration(self) -> Optional[FrameTimecode]:
        """Duration of the stream as a FrameTimecode, or None if non terminating."""
        if self._is_device:
            return None
        return self.base_timecode + math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def aspect_ratio(self) -> float:
        """Display/pixel aspect ratio as a float (1.0 represents square pixels)."""
        return get_aspect_ratio(self._cap)

    @property
    def position(self) -> FrameTimecode:
        """Current position within stream as FrameTimecode.

        This can be interpreted as presentation time stamp of the last frame which was
        decoded by calling `read` with advance=True.

        This method will always return 0 (e.g. be equal to `base_timecode`) if no frames
        have been `read`."""
        if self.frame_number < 1:
            return self.base_timecode
        return self.base_timecode + (self.frame_number - 1)

    @property
    def position_ms(self) -> float:
        """Current position within stream as a float of the presentation time in milliseconds.
        The first frame has a time of 0.0 ms.

        This method will always return 0.0 if no frames have been `read`."""
        return self._cap.get(cv2.CAP_PROP_POS_MSEC)

    @property
    def frame_number(self) -> int:
        """Current position within stream in frames as an int.

        1 indicates the first frame was just decoded by the last call to `read` with advance=True,
        whereas 0 indicates that no frames have been `read`.

        This method will always return 0 if no frames have been `read`."""
        return math.trunc(self._cap.get(cv2.CAP_PROP_POS_FRAMES))

    def seek(self, target: Union[FrameTimecode, float, int]):
        """Seek to the given timecode. If given as a frame number, represents the current seek
        pointer (e.g. if seeking to 0, the next frame decoded will be the first frame of the video).

        For 1-based indices (first frame is frame #1), the target frame number needs to be converted
        to 0-based by subtracting one. For example, if we want to seek to the first frame, we call
        seek(0) followed by read(). If we want to seek to the 5th frame, we call seek(4) followed
        by read(), at which point frame_number will be 5.

        Not supported if the VideoStream is a device/camera. Untested with web streams.

        Arguments:
            target: Target position in video stream to seek to.
                If float, interpreted as time in seconds.
                If int, interpreted as frame number.
        Raises:
            SeekError: An error occurs while seeking, or seeking is not supported.
            ValueError: `target` is not a valid value (i.e. it is negative).
        """
        if self._is_device:
            raise SeekError("Cannot seek if input is a device!")
        if target < 0:
            raise ValueError("Target seek position cannot be negative!")

        # Have to seek one behind and call grab() after to that the VideoCapture
        # returns a valid timestamp when using CAP_PROP_POS_MSEC.
        target_frame_cv2 = (self.base_timecode + target).get_frames()
        if target_frame_cv2 > 0:
            target_frame_cv2 -= 1
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_cv2)
        if target > 0:
            self._cap.grab()
            self._has_grabbed = True
            self._has_seeked = False
        else:
            self._has_grabbed = False
            self._has_seeked = True

    def reset(self):
        """ Close and re-open the VideoStream (should be equivalent to calling `seek(0)`). """
        self._cap.release()
        self._open_capture(self._frame_rate)

    def read(self, decode: bool = True, advance: bool = True) -> Union[ndarray, bool]:
        """ Return next frame (or current if advance = False), or False if end of video.

        Arguments:
            decode: Decode and return the frame.
            advance: Seek to the next frame. If False, will remain on the current frame.

        Returns:
            If decode = True, returns either the decoded frame, or False if end of video.
            If decode = False, a boolean indicating if the next frame was advanced to or not is
            returned.
        """
        if not self._cap.isOpened():
            return False
        if advance:
            self._has_grabbed = self._cap.grab()
            if not self._has_grabbed:
                if self.duration > 0 and self.position < (self.duration-1):
                    for _ in range(self._max_decode_attempts):
                        self._has_grabbed = self._cap.grab()
                        if self._has_grabbed:
                            break
                # Report previous failure in debug mode.
                if self._has_grabbed:
                    self._decode_failures += 1
                    logger.debug('Frame failed to decode.')
                    if not self._warning_displayed and self._decode_failures > 1:
                        logger.warning('Failed to decode some frames, results may be inaccurate.')
            self._has_seeked = False
        if decode and self._has_grabbed:
            _, frame = self._cap.retrieve()
            return frame
        return self._has_grabbed

    #
    # Private Methods
    #

    def _open_capture(self, framerate: Optional[float] = None):
        """Opens capture referenced by this object and resets internal state."""
        if self._is_device and self._path_or_device < 0:
            raise ValueError('Invalid/negative device ID specified.')
        # Check if files exist if passed video file is not an image sequence
        # (checked with presence of % in filename) or not a URL (://).
        if not self._is_device and not ('%' in self._path_or_device
                                        or '://' in self._path_or_device):
            if not os.path.exists(self._path_or_device):
                raise OSError('Video file not found.')

        cap = cv2.VideoCapture(self._path_or_device)
        if not cap.isOpened():
            raise VideoOpenFailure(
                'VideoCapture.isOpened() returned False. Ensure the input file is a valid video,'
                ' and check that OpenCV is installed correctly.\n')

        # Display a warning if the video codec type seems unsupported (#86).
        # We don't do the check if this is a webcam/video capture device or an image sequence.
        if not (self._is_device or '%' in self._path_or_device) and int(
                abs(cap.get(cv2.CAP_PROP_FOURCC))) == 0:
            logger.error(
                'Video codec detection failed, output may be incorrect.\nThis could be caused'
                ' by using an outdated version of OpenCV, or using codecs that currently are'
                ' not well supported (e.g. VP9).\n'
                'As a workaround, consider re-encoding the source material before processing.\n'
                'For details, see https://github.com/Breakthrough/PySceneDetect/issues/86')

        # Ensure the framerate is correct to avoid potential divide by zero errors. This can be
        # addressed in the PyAV backend if required since it supports integer timebases.
        assert framerate is None or framerate > MAX_FPS_DELTA, "Framerate must be validated if set!"
        if framerate is None:
            framerate = cap.get(cv2.CAP_PROP_FPS)
            if framerate < MAX_FPS_DELTA:
                raise FrameRateUnavailable()

        self._cap = cap
        self._frame_rate = framerate
        self._has_seeked = False
        self._has_grabbed = False
