#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2022 Brandon Castellano <http://www.bcastell.com>.
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
import os
import os.path
import warnings
from fractions import Fraction
from logging import getLogger

import cv2
import numpy as np

from scenedetect.common import (
    MAX_FPS_DELTA,
    FrameRate,
    FrameTimecode,
    Timecode,
    TimecodeLike,
    framerate_to_fraction,
    parse_frame_or_time,
)
from scenedetect.platform import StrPath, get_file_name
from scenedetect.video_stream import (
    FrameNumbering,
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


def _get_capture_api(path: str) -> int:
    """API preference to use when opening `path` with `cv2.VideoCapture`. This exists as a
    workaround for https://scenedetect.com/issue/575, where certain versions of the opencv-python
    package cause intermittent segfaults on exit. The issue only happens on Windows when opening
    PNG image sequences.

    By default OpenCV resolves any capture backend by probing for compatibility, and tries FFmpeg
    first. Usually this fails, and it falls back gracefully to CAP_IMAGES. However, this also seems
    to cause issues on interpreter exit, as the stack trace implicates something in the ffmpeg DLL.
    """
    is_local = not any(identifier in path for identifier in ("://", " ! "))
    if os.name == "nt" and is_local and path.lower().endswith(".png"):
        return cv2.CAP_IMAGES
    return cv2.CAP_ANY


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
        path: StrPath | None = None,
        frame_rate: FrameRate | None = None,
        max_decode_attempts: int = 5,
        path_or_device: StrPath | int | None = None,
        framerate: float | None = None,
        *,
        frame_numbering: FrameNumbering = FrameNumbering.RELATIVE,
    ):
        """Open a video file, image sequence, or network stream.

        Arguments:
            path: Path to the video. Can be a file, image sequence (`'folder/DSC_%04d.jpg'`),
                or network stream.
            frame_rate: If set, overrides the detected frame rate. Takes precedence over
                `framerate`.
            max_decode_attempts: Number of attempts to continue decoding the video
                after a frame fails to decode. This allows processing videos that
                have a few corrupted frames or metadata (in which case accuracy
                of detection algorithms may be lower). If all attempts fail,
                `read()` returns False.
            path_or_device: [DEPRECATED] Specify `path` for files, image sequences, or
                network streams/URLs.  Use `VideoCaptureAdapter` for devices/pipes.
            framerate: [DEPRECATED] Use `frame_rate` instead. Retained as a deprecated
                alias for backwards compatibility; ignored when `frame_rate` is provided.
            frame_numbering: RELATIVE (default) numbers the first frame read after each
                successful seek as 0. SOURCE counts from the source beginning, including
                seek preroll. Neither mode resets presentation timestamps.

        Raises:
            OSError: file could not be found or access was denied
            VideoOpenFailure: video could not be opened (may be corrupted)
            ValueError: specified frame rate is invalid
        """
        super().__init__(frame_numbering=frame_numbering)
        if framerate is not None:
            warnings.warn(
                "`framerate` is deprecated and scheduled for removal in v0.9; "
                "use `frame_rate` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        if frame_rate is None:
            frame_rate = framerate
        if path_or_device is not None:
            warnings.warn(
                "The `path_or_device` argument is deprecated, use `path` or `VideoCaptureAdapter`"
                " instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            resolved: str | int = (
                path_or_device if isinstance(path_or_device, int) else os.fspath(path_or_device)
            )
        elif path is None:
            raise ValueError("Path must be specified!")
        else:
            resolved = os.fspath(path)
        if frame_rate is not None and frame_rate < MAX_FPS_DELTA:
            raise ValueError(f"Specified frame rate ({float(frame_rate):f}) is invalid!")
        if max_decode_attempts < 0:
            raise ValueError("Maximum decode attempts must be >= 0!")

        self._path_or_device: str | int = resolved
        self._is_device = isinstance(self._path_or_device, int)

        # VideoCapture state
        self._pending_grab = False
        self._max_decode_attempts = max_decode_attempts
        self._decode_failures = 0
        self._warning_displayed = False

        # `_open_capture` populates `_cap` and `_frame_rate`.
        self._open_capture(frame_rate)

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

    BACKEND_NAME = "opencv"
    """Unique name used to identify this backend."""

    @property
    def frame_rate(self) -> Fraction:
        return self._frame_rate

    @property
    def path(self) -> str:
        if self._is_device:
            assert isinstance(self._path_or_device, int)
            return f"Device {self._path_or_device}"
        assert isinstance(self._path_or_device, str)
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
    def frame_size(self) -> tuple[int, int]:
        """Size of each video frame in pixels as a tuple of (width, height)."""
        return (
            math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    @property
    def duration(self) -> FrameTimecode | None:
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
        """Timestamp of the current capture frame.

        Video timestamps are rounded to integer microseconds from CAP_PROP_POS_MSEC.
        Image-sequence timestamps use the source image index and configured frame rate.
        """
        if self._cap.get(cv2.CAP_PROP_BACKEND) == cv2.CAP_IMAGES:
            source_index = max(
                0, math.trunc(self._cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            )
            return Timecode(
                pts=source_index,
                time_base=1 / self.frame_rate,
            )
        # *NOTE*: CAP_PROP_PTS can be unreliable, so use CAP_PROP_POS_MSEC instead.
        # Its FPS-based units can discard VFR timestamp precision.
        ms = self._cap.get(cv2.CAP_PROP_POS_MSEC)
        time_base = Fraction(1, 1000000)
        return Timecode(pts=round(ms * 1000), time_base=time_base)

    def seek(self, target: TimecodeLike):
        """Position the next read at a source frame ordinal or presentation time.

        Integer targets use sequential grabbing in both numbering modes. RELATIVE numbering
        restarts at 0; SOURCE numbering includes the skipped prefix. Image-sequence time
        targets select the first image at or after the target using the configured frame rate.

        Other time targets use native seeking in RELATIVE mode and sequential grabbing in
        SOURCE mode. Preroll retains the first qualifying frame for the next read. Comparisons
        use microsecond precision. Native seeking can land late and skip eligible frames.

        Arguments:
            target: A zero-based source ordinal (int or digit-only string), or a presentation
                time (float seconds, time string, or Timecode).

        Raises:
            SeekError: Seeking is unsupported or the required preroll cannot be completed.
            TypeError: The target type is unsupported.
            ValueError: The target is negative, non-finite, malformed, or has an invalid time base.
        """
        if not self.is_seekable:
            raise SeekError("Cannot seek if input is a device!")
        parsed = parse_frame_or_time(target)
        if parsed < 0:
            raise ValueError("Target seek position cannot be negative!")

        # TODO: Optimize seeking for CAP_IMAGES
        if (
            isinstance(parsed, Fraction)
            and self._cap.get(cv2.CAP_PROP_BACKEND) == cv2.CAP_IMAGES
        ):
            parsed = math.ceil(parsed * self.frame_rate)
        if isinstance(parsed, Fraction):
            # Compare the target at the same precision as the reported video timestamps.
            target_time = Fraction(round(parsed * 1_000_000), 1_000_000)
            if self.frame_numbering is FrameNumbering.RELATIVE:
                self._pending_grab = False
                if not self._cap.set(cv2.CAP_PROP_POS_MSEC, float(parsed * 1000)):
                    raise SeekError("Could not seek to the requested time.")
            elif (
                self._position is not None
                and self._position.timecode.seconds >= target_time
            ):
                self.reset()

            while self._grab_next_frame():
                if self.timecode.seconds >= target_time:
                    self._pending_grab = True
                    if self.frame_numbering is FrameNumbering.RELATIVE:
                        self._position = None
                    return
                if self.frame_numbering is FrameNumbering.SOURCE:
                    self._record_frame(self.timecode)

            raise SeekError("Could not seek to the requested time.")

        else:
            if (self.frame_numbering is FrameNumbering.RELATIVE
                or self.frame_number >= parsed):
                self.reset()
            for _ in range(self.frame_number+1, parsed):
                if not self._grab_next_frame():
                    raise SeekError("Could not seek to the requested frame.")
                if self.frame_numbering is FrameNumbering.SOURCE:
                    self._record_frame(self.timecode)

            return


    def reset(self):
        """Reopen at the source beginning and clear the recorded position and pending frame."""
        self._cap.release()
        self._open_capture(float(self._frame_rate))

    def read(self, decode: bool = True) -> np.ndarray | bool:
        if not self._grab_next_frame():
            return False
        self._record_frame(self.timecode)
        # Need to make sure we actually grabbed a frame before calling retrieve.
        if decode:
            success, frame = self._cap.retrieve()
            return frame if success else False
        return True

    #
    # Private Methods
    #

    def _open_capture(self, frame_rate: FrameRate | None = None):
        """Opens capture referenced by this object and resets internal state."""
        if self._is_device:
            assert isinstance(self._path_or_device, int)
            if self._path_or_device < 0:
                raise ValueError("Invalid/negative device ID specified.")
            input_is_video_file = False
            capture_api = cv2.CAP_ANY
        else:
            assert isinstance(self._path_or_device, str)
            capture_api = _get_capture_api(self._path_or_device)
            input_is_video_file = not any(
                identifier in self._path_or_device
                for identifier in NON_VIDEO_FILE_INPUT_IDENTIFIERS
            )
            # We don't have a way of querying why opening a video fails (errors are logged at
            # least), so provide a better error message if we try to open a missing file.
            if input_is_video_file and not os.path.exists(self._path_or_device):
                raise OSError("Video file not found.")

        cap = cv2.VideoCapture(self._path_or_device, capture_api)
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
        assert frame_rate is None or frame_rate > MAX_FPS_DELTA, (
            "Frame rate must be validated if set!"
        )
        if frame_rate is None:
            frame_rate = cap.get(cv2.CAP_PROP_FPS)
            if frame_rate < MAX_FPS_DELTA:
                raise FrameRateUnavailable()

        self._cap: cv2.VideoCapture = cap
        self._position = None
        self._frame_rate: Fraction = framerate_to_fraction(frame_rate)
        self._pending_grab = False
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1.0)  # https://github.com/opencv/opencv/issues/26795

    def _grab_next_frame(self) -> bool:
        """Consume a pending seek frame or grab the next frame without recording a position."""
        if self._pending_grab:
            self._pending_grab = False
            return True
        if not self._cap.isOpened():
            return False
        has_grabbed = self._cap.grab()
        # If we failed to grab the frame, retry a few times if required.
        if not has_grabbed:
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
        return has_grabbed


class VideoCaptureAdapter(VideoStream):
    """Adapter for existing VideoCapture objects. Unlike VideoStreamCv2, this class supports
    VideoCaptures which may not support seeking.

    Ordinals and timestamps start at zero with the first frame read through this adapter,
    even if the capture was already advanced. Timestamps use frame count and frame_rate,
    not capture-provided timestamps, so variable frame intervals are not preserved.
    """

    def __init__(
        self,
        cap: cv2.VideoCapture,
        frame_rate: FrameRate | None = None,
        max_read_attempts: int = 5,
        framerate: float | None = None,
    ):
        """Create from an existing OpenCV VideoCapture object. Used for webcams, live streams,
        pipes, or other inputs which may not support seeking.

        Arguments:
            cap: The `cv2.VideoCapture` object to wrap. Must already be opened and ready to
                have `cap.read()` called on it.
            frame_rate: If set, overrides the detected frame rate. Takes precedence over
                `framerate`.
            max_read_attempts: Number of attempts to continue decoding the video
                after a frame fails to decode. This allows processing videos that
                have a few corrupted frames or metadata (in which case accuracy
                of detection algorithms may be lower). If all attempts fail,
                `read()` returns False.
            framerate: [DEPRECATED] Use `frame_rate` instead. Retained as a deprecated
                alias for backwards compatibility; ignored when `frame_rate` is provided.

        Raises:
            ValueError: capture is not open, frame rate or max_read_attempts is invalid
        """
        super().__init__()

        if framerate is not None:
            warnings.warn(
                "`framerate` is deprecated and scheduled for removal in v0.9; "
                "use `frame_rate` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        if frame_rate is None:
            frame_rate = framerate
        if frame_rate is not None and frame_rate < MAX_FPS_DELTA:
            raise ValueError(f"Specified frame rate ({float(frame_rate):f}) is invalid!")
        if max_read_attempts < 0:
            raise ValueError("Maximum decode attempts must be >= 0!")
        if not cap.isOpened():
            raise ValueError("Specified VideoCapture must already be opened!")
        if frame_rate is None:
            frame_rate = cap.get(cv2.CAP_PROP_FPS)
            if frame_rate < MAX_FPS_DELTA:
                raise FrameRateUnavailable()

        self._cap = cap
        self._frame_rate: Fraction = framerate_to_fraction(frame_rate)
        self._max_read_attempts = max_read_attempts
        self._decode_failures = 0
        self._warning_displayed = False

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
        return self._cap

    #
    # VideoStream Methods/Properties
    #

    BACKEND_NAME = "opencv_adapter"
    """Unique name used to identify this backend."""

    @property
    def frame_rate(self) -> Fraction:
        """Framerate in frames/sec."""
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
        """Always False; this adapter does not expose seeking."""
        return False

    @property
    def frame_size(self) -> tuple[int, int]:
        """Reported size of each video frame in pixels as a tuple of (width, height)."""
        return (
            math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    @property
    def duration(self) -> FrameTimecode | None:
        """Duration of the stream as a FrameTimecode, or None if non terminating."""
        frame_count = math.trunc(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count > 0:
            return self.base_timecode + frame_count
        return None

    @property
    def aspect_ratio(self) -> float:
        """Display/pixel aspect ratio as a float (1.0 represents square pixels)."""
        return _get_aspect_ratio(self._cap)

    def seek(self, target: TimecodeLike):
        """Seeking is not supported by this adapter."""
        raise NotImplementedError("Seeking is not supported.")

    def reset(self):
        """Not supported."""
        raise NotImplementedError("Reset is not supported.")

    def read(self, decode: bool = True) -> np.ndarray | bool:
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
        # TODO: Define a timestamp policy for timed and untimed captures.
        # The FPS-derived clock below does not preserve variable frame intervals.
        self._record_frame(
            Timecode(
                pts=self.frame_number+1,
                time_base=1 / self.frame_rate
            )
        )
        # Need to make sure we actually grabbed a frame before calling retrieve.
        if decode:
            success, frame = self._cap.retrieve()
            return frame if success else False
        return True
