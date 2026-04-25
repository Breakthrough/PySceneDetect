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
""":class:`VideoStreamMoviePy` provides an adapter for MoviePy's `FFMPEG_VideoReader`.

MoviePy launches ffmpeg as a subprocess, and can be used with various types of inputs. Generally,
the input should support seeking, but does not necessarily have to be a video. For example,
image sequences or AviSynth scripts are supported as inputs.
"""

import os
import time
import typing as ty
from fractions import Fraction
from logging import getLogger

import cv2
import numpy as np
from moviepy.video.io.ffmpeg_reader import FFMPEG_VideoReader

from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.common import (
    FrameTimecode,
    Timecode,
    TimecodeLike,
    framerate_to_fraction,
)
from scenedetect.platform import StrPath, get_file_name
from scenedetect.video_stream import SeekError, VideoOpenFailure, VideoStream

logger = getLogger("pyscenedetect")

# MoviePy spawns ffmpeg as a subprocess and reads frame bytes over stdout. Under
# load the parent can read before the child has flushed its first write, which
# surfaces as OSError (see #496). A short retry clears nearly all such flakes.
_FFMPEG_RETRY_COUNT = 2
_FFMPEG_RETRY_BACKOFF_SECS = 0.5


def _retry_on_oserror(op_name: str, fn: ty.Callable):
    """Run ``fn``, retrying up to ``_FFMPEG_RETRY_COUNT`` times on ``OSError``."""
    last_exc: OSError | None = None
    for attempt in range(_FFMPEG_RETRY_COUNT + 1):
        try:
            return fn()
        except OSError as ex:
            last_exc = ex
            if attempt < _FFMPEG_RETRY_COUNT:
                logger.warning(
                    "ffmpeg %s failed (attempt %d/%d), retrying: %s",
                    op_name,
                    attempt + 1,
                    _FFMPEG_RETRY_COUNT + 1,
                    ex,
                )
                time.sleep(_FFMPEG_RETRY_BACKOFF_SECS)
    assert last_exc is not None
    raise last_exc


class VideoStreamMoviePy(VideoStream):
    """MoviePy `FFMPEG_VideoReader` backend."""

    def __init__(self, path: StrPath, framerate: float | None = None, print_infos: bool = False):
        """Open a video or device.

        Arguments:
            path: Path to video,.
            framerate: If set, overrides the detected framerate.
            print_infos: If True, prints information about the opened video to stdout.

        Raises:
            OSError: file could not be found, access was denied, or the video is corrupt
            VideoOpenFailure: video could not be opened (may be corrupted)
        """
        super().__init__()

        # TODO: Investigate how MoviePy handles ffmpeg not being on PATH.
        # TODO: Add framerate override.
        if framerate is not None:
            raise NotImplementedError(
                "VideoStreamMoviePy does not support the `framerate` argument yet."
            )

        self._path: str = os.fspath(path)
        # TODO: Need to map errors based on the strings, since several failure
        # cases return IOErrors (e.g. could not read duration/video resolution). These
        # should be mapped to specific errors, e.g. write a function to map MoviePy
        # exceptions to a new set of equivalents.
        self._reader = _retry_on_oserror(
            "open", lambda: FFMPEG_VideoReader(self._path, print_infos=print_infos)
        )
        # This will always be one behind self._reader.lastread when we finally call read()
        # as MoviePy caches the first frame when opening the video. Thus self._last_frame
        # will always be the current frame, and self._reader.lastread will be the next.
        self._last_frame: bool | np.ndarray = False
        self._last_frame_rgb: np.ndarray | None = None
        # Older versions don't track the video position when calling read_frame so we need
        # to keep track of the current frame number.
        self._frame_number = 0
        # We need to manually keep track of EOF as duration may not be accurate.
        self._eof = False
        self._aspect_ratio: float | None = None

    #
    # VideoStream Methods/Properties
    #

    BACKEND_NAME = "moviepy"
    """Unique name used to identify this backend."""

    @property
    def frame_rate(self) -> Fraction:
        """Framerate in frames/sec as a rational Fraction."""
        return framerate_to_fraction(self._reader.fps)

    @property
    def path(self) -> str:
        """Video path."""
        return self._path

    @property
    def name(self) -> str:
        """Name of the video, without extension, or device."""
        return get_file_name(self.path, include_extension=False)

    @property
    def is_seekable(self) -> bool:
        """True if seek() is allowed, False otherwise."""
        return True

    @property
    def frame_size(self) -> tuple[int, int]:
        """Size of each video frame in pixels as a tuple of (width, height)."""
        return tuple(self._reader.infos["video_size"])

    @property
    def duration(self) -> FrameTimecode | None:
        """Duration of the stream as a FrameTimecode, or None if non terminating."""
        assert isinstance(self._reader.infos["duration"], float)
        return self.base_timecode + self._reader.infos["duration"]

    @property
    def aspect_ratio(self) -> float:
        """Display/pixel aspect ratio as a float (1.0 represents square pixels)."""
        # TODO: Use cached_property.
        if self._aspect_ratio is None:
            # MoviePy doesn't support extracting the aspect ratio yet, so for now we just fall
            # back to using OpenCV to determine it.
            try:
                self._aspect_ratio = VideoStreamCv2(self._path).aspect_ratio
            except VideoOpenFailure as ex:
                logger.warning("Unable to determine aspect ratio: %s", str(ex))
                self._aspect_ratio = 1.0
        return self._aspect_ratio

    @property
    def position(self) -> FrameTimecode:
        """Current position within stream as FrameTimecode.

        This can be interpreted as presentation time stamp of the last frame which was decoded by
        calling `read`. This will always return 0 (e.g. be equal to `base_timecode`) if no frames
        have been `read` yet."""
        frame_number = max(self._frame_number - 1, 0)
        # Synthesize a Timecode from the frame count and rational framerate.
        # MoviePy assumes CFR, so this is equivalent to frame-based timing.
        # Use the framerate denominator as the time_base denominator for exact timing.
        fps = self.frame_rate
        time_base = Fraction(1, fps.numerator)
        pts = frame_number * fps.denominator
        timecode = Timecode(pts=pts, time_base=time_base)
        return FrameTimecode(timecode=timecode, fps=fps)

    @property
    def position_ms(self) -> float:
        """Current position within stream as a float of the presentation time in milliseconds.
        The first frame has a time of 0.0 ms.

        This method will always return 0.0 if no frames have been `read`."""
        return self.position.seconds * 1000.0

    @property
    def frame_number(self) -> int:
        """Current position within stream in frames as an int.

        0 indicates that no frames have been `read`, 1 indicates the first frame was just read.
        """
        return self._frame_number

    def seek(self, target: TimecodeLike):
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
        success = False
        if not isinstance(target, FrameTimecode):
            target = FrameTimecode(target, self.frame_rate)
        duration = self.duration
        assert duration is not None
        try:
            self._last_frame = _retry_on_oserror(
                "seek", lambda: self._reader.get_frame(target.seconds)
            )
            if hasattr(self._reader, "last_read") and target >= duration:
                raise SeekError("MoviePy > 2.0 does not have proper EOF semantics (#461).")
            self._frame_number = min(
                target.frame_num,
                FrameTimecode(self._reader.infos["duration"], self.frame_rate).frame_num - 1,
            )
            success = True
        except OSError as ex:
            # TODO(https://scenedetect.com/issues/380): Other backends do not currently throw an
            # exception if attempting to seek past EOF.
            #
            # We need to ensure consistency for seeking past end of video with respect to errors and
            # behaviour, and should probably gracefully stop at the last frame instead of throwing.
            if target >= duration:
                raise SeekError("Target frame is beyond end of video!") from ex
            raise
        finally:
            # Leave the object in a valid state on any errors.
            if not success:
                self.reset()

    def reset(self, print_infos=False):
        """Close and re-open the VideoStream (should be equivalent to calling `seek(0)`)."""
        self._last_frame = False
        self._last_frame_rgb = None
        self._frame_number = 0
        self._eof = False
        self._reader = _retry_on_oserror(
            "reset", lambda: FFMPEG_VideoReader(self._path, print_infos=print_infos)
        )

    def read(self, decode: bool = True) -> np.ndarray | bool:
        if not hasattr(self._reader, "lastread") or self._eof:
            return False
        has_last_read = hasattr(self._reader, "last_read")
        # In MoviePy 2.0 there is a separate property we need to read named differently (#461).
        self._last_frame = self._reader.last_read if has_last_read else self._reader.lastread
        # Read the *next* frame for the following call to read, and to check for EOF.
        frame = self._reader.read_frame()
        if frame is self._last_frame:
            if self._eof:
                return False
            self._eof = True
        self._frame_number += 1
        if decode and isinstance(self._last_frame, np.ndarray):
            self._last_frame_rgb = cv2.cvtColor(self._last_frame, cv2.COLOR_BGR2RGB)
            assert self._last_frame_rgb is not None
            return self._last_frame_rgb
        return not self._eof
