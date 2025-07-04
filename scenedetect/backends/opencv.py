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
""":class:`VideoStreamCv2` is backed by the OpenCV `VideoCapture` object. This is the default
backend. Works with video files, image sequences, and network streams/URLs.

For wrapping input devices or pipes, there is also :class:`VideoCaptureAdapter` which can be
constructed from an existing `cv2.VideoCapture`. This allows performing scene detection on inputs
which do not support seeking.
"""

import math
import os.path
import typing as ty
import warnings
from fractions import Fraction
from logging import getLogger

import cv2
import numpy as np

from scenedetect.common import _USE_PTS_IN_DEVELOPMENT, MAX_FPS_DELTA, FrameTimecode, Timecode
from scenedetect.platform import get_file_name
from scenedetect.video_stream import (
    FrameRateUnavailable,
    SeekError,
    VideoOpenFailure,
    VideoStream,
)

logger = getLogger("pyscenedetect")

IMAGE_SEQUENCE_IDENTIFIER = "%"

NON_VIDEO_FILE_INPUT_IDENTIFIERS = (
    IMAGE_SEQUENCE_IDENTIFIER,  # image sequence
    "://",  # URL/network stream
    " ! ",  # gstreamer pipe
)


def _get_aspect_ratio(cap: cv2.VideoCapture, epsilon: float = 0.0001) -> float:
    """Display/pixel aspect ratio of the VideoCapture as a float (1.0 represents square pixels)."""
    # Versions of OpenCV < 3.4.1 do not support this, so we fall back to 1.0.
    if "CAP_PROP_SAR_NUM" not in dir(cv2):
        return 1.0
    num: float = cap.get(cv2.CAP_PROP_SAR_NUM)
    den: float = cap.get(cv2.CAP_PROP_SAR_DEN)
    # If numerator or denominator are close to zero, so we fall back to 1.0.
    if abs(num) < epsilon or abs(den) < epsilon:
        return 1.0
    return num / den


class VideoStreamCv2(VideoStream):
    """OpenCV `cv2.VideoCapture` backend."""

    def __init__(
        self,
        path: ty.AnyStr = None,
        framerate: ty.Optional[float] = None,
        max_decode_attempts: int = 5,
        path_or_device: ty.Union[bytes, str, int] = None,
    ):
        """Open a video file, image sequence, or network stream.

        Arguments:
            path: Path to the video. Can be a file, image sequence (`'folder/DSC_%04d.jpg'`),
                or network stream.
            framerate: If set, overrides the detected framerate.
            max_decode_attempts: Number of attempts to continue decoding the video
                after a frame fails to decode. This allows processing videos that
                have a few corrupted frames or metadata (in which case accuracy
                of detection algorithms may be lower). Once this limit is passed,
                decoding will stop and emit an error.
            path_or_device: [DEPRECATED] Specify `path` for files, image sequences, or
                network streams/URLs.  Use `VideoCaptureAdapter` for devices/pipes.

        Raises:
            OSError: file could not be found or access was denied
            VideoOpenFailure: video could not be opened (may be corrupted)
            ValueError: specified framerate is invalid
        """
        super().__init__()
        if path_or_device is not None:
            warnings.warn(
                "The `path_or_device` argument is deprecated, use `path` or `VideoCaptureAdapter` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            path = path_or_device
        if path is None:
            raise ValueError("Path must be specified!")
        if framerate is not None and framerate < MAX_FPS_DELTA:
            raise ValueError("Specified framerate (%f) is invalid!" % framerate)
        if max_decode_attempts < 0:
            raise ValueError("Maximum decode attempts must be >= 0!")

        self._path_or_device = path
        self._is_device = isinstance(self._path_or_device, int)

        # Initialized in _open_capture:
        self._cap: ty.Optional[cv2.VideoCapture] = (
            None  # Reference to underlying cv2.VideoCapture object.
        )
        self._frame_rate: ty.Optional[float] = None

        # VideoCapture state
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
        assert self._cap
        return self._cap

    #
    # VideoStream Methods/Properties
    #

    BACKEND_NAME = "opencv"
    """Unique name used to identify this backend."""

    @property
    def frame_rate(self) -> float:
        assert self._frame_rate
        return self._frame_rate

    @property
    def path(self) -> ty.Union[bytes, str]:
        if self._is_device:
            assert isinstance(self._path_or_device, (int))
            return "Device %d" % self._path_or_device
        assert isinstance(self._path_or_device, (bytes, str))
        return self._path_or_device

    @property
    def name(self) -> str:
        if self._is_device:
            return self.path
        file_name: str = get_file_name(self.path, include_extension=False)
        if IMAGE_SEQUENCE_IDENTIFIER in file_name:
            # file_name is an image sequence, trim everything including/after the %.
            # TODO: This excludes any suffix after the sequence identifier.
            file_name = file_name[: file_name.rfind(IMAGE_SEQUENCE_IDENTIFIER)]
        return file_name

    @property
    def is_seekable(self) -> bool:
        """True if seek() is allowed, False otherwise.

        Always False if opening a device/webcam."""
        return not self._is_device

    @property
    def frame_size(self) -> ty.Tuple[int, int]:
        """Size of each video frame in pixels as a tuple of (width, height)."""
        return (
            math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    @property
    def duration(self) -> ty.Optional[FrameTimecode]:
        """Duration of the stream as a FrameTimecode, or None if non terminating."""
        if self._is_device:
            return None
        return self.base_timecode + math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def aspect_ratio(self) -> float:
        """Display/pixel aspect ratio as a float (1.0 represents square pixels)."""
        return _get_aspect_ratio(self._cap)

    @property
    def timecode(self) -> Timecode:
        """Current position within stream as a Timecode. This is not frame accurate."""
        # *NOTE*: Although OpenCV has `CAP_PROP_PTS`, it doesn't seem to be reliable. For now, we
        # use `CAP_PROP_POS_MSEC` instead, with a time base of 1/1000. Unfortunately this means that
        # rounding errors will affect frame accuracy with this backend.
        pts = self._cap.get(cv2.CAP_PROP_POS_MSEC)
        time_base = Fraction(1, 1000)
        return Timecode(pts=round(pts), time_base=time_base)

    @property
    def position(self) -> FrameTimecode:
        if _USE_PTS_IN_DEVELOPMENT:
            return FrameTimecode(timecode=self.timecode, fps=self.frame_rate)
        if self.frame_number < 1:
            return self.base_timecode
        return self.base_timecode + (self.frame_number - 1)

    @property
    def position_ms(self) -> float:
        return self._cap.get(cv2.CAP_PROP_POS_MSEC)

    @property
    def frame_number(self) -> int:
        return math.trunc(self._cap.get(cv2.CAP_PROP_POS_FRAMES))

    def seek(self, target: ty.Union[FrameTimecode, float, int]):
        if self._is_device:
            raise SeekError("Cannot seek if input is a device!")
        if target < 0:
            raise ValueError("Target seek position cannot be negative!")

        # Have to seek one behind and call grab() after to that the VideoCapture
        # returns a valid timestamp when using CAP_PROP_POS_MSEC.
        target_frame_cv2 = (self.base_timecode + target).frame_num
        if target_frame_cv2 > 0:
            target_frame_cv2 -= 1
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_cv2)
        self._has_grabbed = False
        # Preemptively grab the frame behind the target position if possible.
        if target > 0:
            self._has_grabbed = self._cap.grab()
            # If we seeked past the end of the video, need to seek one frame backwards
            # from the current position and grab that frame instead.
            if not self._has_grabbed:
                seek_pos = round(self._cap.get(cv2.CAP_PROP_POS_FRAMES) - 1.0)
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, seek_pos))
                self._has_grabbed = self._cap.grab()

    def reset(self):
        """Close and re-open the VideoStream (should be equivalent to calling `seek(0)`)."""
        self._cap.release()
        self._open_capture(self._frame_rate)

    def read(self, decode: bool = True) -> ty.Union[np.ndarray, bool]:
        if not self._cap.isOpened():
            return False
        has_grabbed = self._cap.grab()
        # If we failed to grab the frame, retry a few times if required.
        if not has_grabbed:
            if self.duration > 0 and self.position < (self.duration - 1):
                for _ in range(self._max_decode_attempts):
                    has_grabbed = self._cap.grab()
                    if has_grabbed:
                        break
            # Report previous failure in debug mode.
            if has_grabbed:
                self._decode_failures += 1
                logger.debug("Frame failed to decode.")
                if not self._warning_displayed and self._decode_failures > 1:
                    logger.warning("Failed to decode some frames, results may be inaccurate.")
        # We didn't manage to grab a frame even after retrying, so just return.
        if not has_grabbed:
            return False
        self._has_grabbed = True
        # Need to make sure we actually grabbed a frame before calling retrieve.
        if decode and self._has_grabbed:
            _, frame = self._cap.retrieve()
            return frame
        return self._has_grabbed

    #
    # Private Methods
    #

    def _open_capture(self, framerate: ty.Optional[float] = None):
        """Opens capture referenced by this object and resets internal state."""
        if self._is_device and self._path_or_device < 0:
            raise ValueError("Invalid/negative device ID specified.")
        input_is_video_file = not self._is_device and not any(
            identifier in self._path_or_device for identifier in NON_VIDEO_FILE_INPUT_IDENTIFIERS
        )
        # We don't have a way of querying why opening a video fails (errors are logged at least),
        # so provide a better error message if we try to open a file that doesn't exist.
        if input_is_video_file and not os.path.exists(self._path_or_device):
            raise OSError("Video file not found.")

        cap = cv2.VideoCapture(self._path_or_device)
        if not cap.isOpened():
            raise VideoOpenFailure(
                "Ensure file is valid video and system dependencies are up to date.\n"
            )

        # Display an error if the video codec type seems unsupported (#86) as this indicates
        # potential video corruption, or may explain missing frames. We only perform this check
        # for video files on-disk (skipped for devices, image sequences, streams, etc...).
        codec_unsupported: bool = int(abs(cap.get(cv2.CAP_PROP_FOURCC))) == 0
        if codec_unsupported and input_is_video_file:
            logger.error(
                "Video codec detection failed. If output is incorrect:\n"
                "  - Re-encode the input video with ffmpeg\n"
                "  - Update OpenCV (pip install --upgrade opencv-python)\n"
                "  - Use the PyAV backend (--backend pyav)\n"
                "For details, see https://github.com/Breakthrough/PySceneDetect/issues/86"
            )

        # Ensure the framerate is correct to avoid potential divide by zero errors. This can be
        # addressed in the PyAV backend if required since it supports integer timebases.
        assert framerate is None or framerate > MAX_FPS_DELTA, "Framerate must be validated if set!"
        if framerate is None:
            framerate = cap.get(cv2.CAP_PROP_FPS)
            if framerate < MAX_FPS_DELTA:
                raise FrameRateUnavailable()

        self._cap = cap
        self._frame_rate = framerate
        self._has_grabbed = False
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1.0)  # https://github.com/opencv/opencv/issues/26795


# TODO(#168): Support non-monotonic timing for `position`. VFR timecode support is a
# prerequisite for this. Timecodes are currently calculated by multiplying the framerate
# by number of frames. Actual elapsed time can be obtained via `position_ms` for now.
class VideoCaptureAdapter(VideoStream):
    """Adapter for existing VideoCapture objects. Unlike VideoStreamCv2, this class supports
    VideoCaptures which may not support seeking.
    """

    def __init__(
        self,
        cap: cv2.VideoCapture,
        framerate: ty.Optional[float] = None,
        max_read_attempts: int = 5,
    ):
        """Create from an existing OpenCV VideoCapture object. Used for webcams, live streams,
        pipes, or other inputs which may not support seeking.

        Arguments:
            cap: The `cv2.VideoCapture` object to wrap. Must already be opened and ready to
                have `cap.read()` called on it.
            framerate: If set, overrides the detected framerate.
            max_read_attempts: Number of attempts to continue decoding the video
                after a frame fails to decode. This allows processing videos that
                have a few corrupted frames or metadata (in which case accuracy
                of detection algorithms may be lower). Once this limit is passed,
                decoding will stop and emit an error.

        Raises:
            ValueError: capture is not open, framerate or max_read_attempts is invalid
        """
        super().__init__()

        if framerate is not None and framerate < MAX_FPS_DELTA:
            raise ValueError("Specified framerate (%f) is invalid!" % framerate)
        if max_read_attempts < 0:
            raise ValueError("Maximum decode attempts must be >= 0!")
        if not cap.isOpened():
            raise ValueError("Specified VideoCapture must already be opened!")
        if framerate is None:
            framerate = cap.get(cv2.CAP_PROP_FPS)
            if framerate < MAX_FPS_DELTA:
                raise FrameRateUnavailable()

        self._cap = cap
        self._frame_rate: float = framerate
        self._num_frames = 0
        self._max_read_attempts = max_read_attempts
        self._decode_failures = 0
        self._warning_displayed = False
        self._time_base: float = 0.0

    #
    # Backend-Specific Methods/Properties
    #

    @property
    def capture(self) -> cv2.VideoCapture:
        """Returns reference to underlying VideoCapture object. Use with caution.

        Prefer to use this property only to take ownership of the underlying cv2.VideoCapture object
        backing this object. Using the read/grab methods through this property are unsupported and
        will leave this object in an inconsistent state.
        """
        assert self._cap
        return self._cap

    #
    # VideoStream Methods/Properties
    #

    BACKEND_NAME = "opencv_adapter"
    """Unique name used to identify this backend."""

    @property
    def frame_rate(self) -> float:
        """Framerate in frames/sec."""
        assert self._frame_rate
        return self._frame_rate

    @property
    def path(self) -> str:
        """Always 'CAP_ADAPTER'."""
        return "CAP_ADAPTER"

    @property
    def name(self) -> str:
        """Always 'CAP_ADAPTER'."""
        return "CAP_ADAPTER"

    @property
    def is_seekable(self) -> bool:
        """Always False, as the underlying VideoCapture is assumed to not support seeking."""
        return False

    @property
    def frame_size(self) -> ty.Tuple[int, int]:
        """Reported size of each video frame in pixels as a tuple of (width, height)."""
        return (
            math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    @property
    def duration(self) -> ty.Optional[FrameTimecode]:
        """Duration of the stream as a FrameTimecode, or None if non terminating."""
        # TODO(v0.7): This will be incorrect for VFR. See if there is another property we can use
        # to estimate the video length correctly.
        frame_count = math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count > 0:
            return self.base_timecode + frame_count
        return None

    @property
    def aspect_ratio(self) -> float:
        """Display/pixel aspect ratio as a float (1.0 represents square pixels)."""
        return _get_aspect_ratio(self._cap)

    @property
    def position(self) -> FrameTimecode:
        if self.frame_number < 1:
            return self.base_timecode
        return self.base_timecode + (self.frame_number - 1)

    @property
    def position_ms(self) -> float:
        if self._num_frames == 0:
            return 0.0
        return self._cap.get(cv2.CAP_PROP_POS_MSEC) - self._time_base

    @property
    def frame_number(self) -> int:
        return self._num_frames

    def seek(self, target: ty.Union[FrameTimecode, float, int]):
        """The underlying VideoCapture is assumed to not support seeking."""
        raise NotImplementedError("Seeking is not supported.")

    def reset(self):
        """Not supported."""
        raise NotImplementedError("Reset is not supported.")

    def read(self, decode: bool = True) -> ty.Union[np.ndarray, bool]:
        if not self._cap.isOpened():
            return False
        has_grabbed = self._cap.grab()
        # If we failed to grab the frame, retry a few times if required.
        if not has_grabbed:
            for _ in range(self._max_read_attempts):
                has_grabbed = self._cap.grab()
                if has_grabbed:
                    break
            # Report previous failure in debug mode.
            if has_grabbed:
                self._decode_failures += 1
                logger.debug("Frame failed to decode.")
                if not self._warning_displayed and self._decode_failures > 1:
                    logger.warning("Failed to decode some frames, results may be inaccurate.")
        # We didn't manage to grab a frame even after retrying, so just return.
        if not has_grabbed:
            return False
        if self._num_frames == 0:
            self._time_base = self._cap.get(cv2.CAP_PROP_POS_MSEC)
        self._num_frames += 1
        # Need to make sure we actually grabbed a frame before calling retrieve.
        if decode and self._num_frames > 0:
            _, frame = self._cap.retrieve()
            return frame
        return True
