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
""":class:`VideoStreamMoviePy` provides an adapter for MoviePy's `FFMPEG_VideoReader`.

MoviePy launches ffmpeg as a subprocess, and can be used with various types of inputs. Generally,
the input should support seeking, but does not necessarily have to be a video. For example,
image sequences or AviSynth scripts are supported as inputs.
"""

import math
import os
import time
import typing as ty
import warnings
from fractions import Fraction
from logging import getLogger

import cv2
import numpy as np
from moviepy.video.io.ffmpeg_reader import FFMPEG_VideoReader

from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.common import (
    FrameRate,
    FrameTimecode,
    Timecode,
    TimecodeLike,
    framerate_to_fraction,
    parse_frame_or_time
)
from scenedetect.platform import StrPath, get_file_name
from scenedetect.video_stream import FrameNumbering, SeekError, VideoOpenFailure, VideoStream

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

    def __init__(
        self,
        path: StrPath,
        frame_rate: FrameRate | None = None,
        print_infos: bool = False,
        framerate: float | None = None,
        *,
        frame_numbering: FrameNumbering = FrameNumbering.RELATIVE,
    ):
        """Open a video or device.

        Arguments:
            path: Path to video,.
            frame_rate: If set, overrides the detected frame rate. Takes precedence over
                `framerate`.
            print_infos: If True, prints information about the opened video to stdout.
            framerate: [DEPRECATED] Use `frame_rate` instead. Retained as a deprecated
                alias for backwards compatibility; ignored when `frame_rate` is provided.
            frame_numbering: RELATIVE (default) restarts ordinals at 0 after seeking.
                SOURCE counts frames from the source beginning.

        Raises:
            OSError: file could not be found, access was denied, or the video is corrupt
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
        # TODO: Investigate how MoviePy handles ffmpeg not being on PATH.
        if frame_rate is not None and frame_rate <= 0:
            raise ValueError(f"Specified frame rate ({float(frame_rate):f}) is invalid!")
        # The override - if set - takes precedence over the rate reported by the reader.
        # MoviePy assumes CFR, so changing the rate is equivalent to reinterpreting frame
        # timestamps at a different cadence; the source's wall-clock duration is unaffected.
        self._frame_rate_override: Fraction | None = (
            framerate_to_fraction(frame_rate) if frame_rate is not None else None
        )

        self._path: str = os.fspath(path)
        # TODO: Need to map errors based on the strings, since several failure
        # cases return IOErrors (e.g. could not read duration/video resolution). These
        # should be mapped to specific errors, e.g. write a function to map MoviePy
        # exceptions to a new set of equivalents.
        self._reader = _retry_on_oserror(
            "open", lambda: FFMPEG_VideoReader(self._path, print_infos=print_infos)
        )
        # TODO: Support native VFR timestamps. FFMPEG_VideoReader exposes no per-frame
        # PTS, so this backend currently derives timestamps from the frame rate.
        # Timestamp of the cached image that the next read will return.
        self._next_timecode = Timecode(pts=0, time_base=1 / self.frame_rate)
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
        """Framerate in frames/sec as a rational Fraction. Returns the override passed at
        construction if one was provided; otherwise the rate reported by MoviePy's reader."""
        if self._frame_rate_override is not None:
            return self._frame_rate_override
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

    def seek(self, target: TimecodeLike):
        """Position the next read at a source frame ordinal or a time on the FPS-derived clock.

        Integer targets use sequential reading in both numbering modes. For example, `seek(4)`
        followed by `read()` reads the fifth frame. Its ordinal is 0 in RELATIVE mode or 4 in
        SOURCE mode.

        Time targets select the first frame at or after the requested time on the clock derived
        from `frame_rate`. Native per-frame presentation timestamps are not available. RELATIVE
        mode uses native MoviePy seeking; SOURCE mode counts the preceding frames sequentially.
        A successful seek restarts RELATIVE numbering at 0 without resetting frame timestamps.

        Not supported if the VideoStream is a device/camera. Untested with web streams.

        Arguments:
            target: A zero-based source ordinal (int or digit-only string), or a time
                (float seconds, timecode string, or Timecode).
        Raises:
            SeekError: The target cannot be reached, or seeking is not supported.
            OSError: MoviePy fails while seeking.
            TypeError: The target type is unsupported.
            ValueError: The target is negative, non-finite, or malformed, or has an invalid
                time base.
        """

        if not self.is_seekable:
            raise SeekError("Seeking is not supported for this video stream!")
        
        parsed = parse_frame_or_time(target)
        if parsed < 0:
            raise ValueError(f"Target frame/timecode ({target}) is negative!")

        if isinstance(parsed, Fraction):
            target_frame = math.ceil(parsed * self.frame_rate)
            if self.frame_numbering is FrameNumbering.SOURCE:
                self.seek(target_frame)
                if self._eof:
                    raise SeekError("Could not seek to the requested frame")
                return

            reader_time = target_frame / self._reader.fps
            success = False
            duration = self._reader.infos["duration"]
            try:
                # MoviePy 1.x does not update pos during direct read_frame() calls.
                self._reader.pos = self._next_timecode.pts + 1
                _retry_on_oserror(
                    "seek", lambda: self._reader.get_frame(reader_time)
                )
                if hasattr(self._reader, "last_read") and reader_time >= duration:
                    raise SeekError("MoviePy > 2.0 does not have proper EOF semantics (#461).")
                self._next_timecode = Timecode(
                    pts=target_frame, 
                    time_base=1 / self.frame_rate
                )
                self._position = None
                self._eof = False
                success = True
            except OSError as ex:
                # TODO(https://scenedetect.com/issues/380): Other backends do not currently throw an
                # exception if attempting to seek past EOF.
                #
                # We need to ensure consistency for seeking past end of video with respect to errors and
                # behaviour, and should probably gracefully stop at the last frame instead of throwing.
                if reader_time >= duration:
                    raise SeekError("Target frame is beyond end of video!") from ex
                raise
            finally:
                # Leave the object in a valid state on any errors.
                if not success:
                    self.reset()
            
        else:
            if (self.frame_numbering is FrameNumbering.RELATIVE
                or parsed <= self.frame_number):
                self.reset()

            for _ in range(self.frame_number+1, parsed):
                item = self._read_next_frame()
                if item is None:
                    raise SeekError("Could not seek to the requested frame")
                if self._frame_numbering is FrameNumbering.SOURCE:
                    _, timecode = item
                    self._record_frame(timecode)
            return

    def reset(self, print_infos=False):
        """Close and re-open the VideoStream (should be equivalent to calling `seek(0)`)."""
        self._reader.close()
        self._position = None
        self._eof = False
        self._reader = _retry_on_oserror(
            "reset", lambda: FFMPEG_VideoReader(self._path, print_infos=print_infos)
        )
        self._next_timecode = Timecode(pts=0, time_base=1 / self.frame_rate)

    def read(self, decode: bool = True) -> np.ndarray | bool:
        item = self._read_next_frame()
        if item is None:
            return False

        frame, timecode = item
        result = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if decode else True
        self._record_frame(timecode)
        return result

    def _read_next_frame(self) -> tuple[np.ndarray, Timecode] | None:
        """Return the cached image and timestamp without recording a position.

        Prefetch the next image. If it reaches EOF, the current image is still returned;
        the following call returns None.
        """
        if self._eof:
            return None
        if hasattr(self._reader, "last_read"):
            frame = self._reader.last_read
        elif hasattr(self._reader, "lastread"):
            frame = self._reader.lastread
        else:
            return None

        timecode = self._next_timecode
        if self._reader.read_frame() is frame:
            self._eof = True
        else:
            self._next_timecode = Timecode(
                pts=timecode.pts + 1, time_base=timecode.time_base
            )

        return frame, timecode
