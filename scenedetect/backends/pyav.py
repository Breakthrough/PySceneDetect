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
""":class:`VideoStreamAv` provides an adapter for the PyAV av.InputContainer object."""

import os
import typing as ty
import warnings
from fractions import Fraction
from logging import getLogger

import av
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
VALID_THREAD_MODES = ["NONE", "SLICE", "FRAME", "AUTO"]

MAX_CONSECUTIVE_DECODE_FAILURES = 8
"""Number of consecutive frame decode failures after which `VideoStreamAv.read()` gives up.
Isolated corrupt frames are skipped; this bound ensures a truncated file still terminates."""


class VideoStreamAv(VideoStream):
    """PyAV `av.InputContainer` backend."""

    # TODO: Investigate adding an accurate_duration option to backends to calculate the duration
    # with higher precision. Sometimes it doesn't exactly match what the codec or VLC reports,
    # but we can try to seek to the end of the video first to determine it. Investigate how VLC
    # calculates the end time.
    def __init__(
        self,
        path_or_io: StrPath | ty.BinaryIO,
        frame_rate: FrameRate | None = None,
        name: str | None = None,
        threading_mode: str | None = None,
        suppress_output: bool = False,
        framerate: FrameRate | None = None,
        *,
        frame_numbering: FrameNumbering = FrameNumbering.RELATIVE,
    ):
        """Open a video by path or from a binary file-like object.

        .. warning::

            Using `threading_mode` with `suppress_output = True` can cause lockups in your
            application. See the PyAV documentation for details:
            https://pyav.org/docs/stable/overview/caveats.html#sub-interpeters

        Arguments:
            path_or_io: Path to the video, or a file-like object.
            frame_rate: If set, overrides the detected frame rate. Takes precedence over
                `framerate`.
            name: Overrides the `name` property derived from the video path. Should be set if
                `path_or_io` is a file-like object.
            threading_mode: The PyAV video stream `thread_type`. See av.codec.context.ThreadType
                for valid threading modes ('AUTO', 'FRAME', 'NONE', and 'SLICE'). For seekable
                sources in 'AUTO' or 'FRAME' mode, an EOF error triggers at most one recovery
                attempt with codec threading disabled. Consumed frames are replayed before reading
                resumes.
            suppress_output: If False, ffmpeg output will be sent to stdout/stderr by calling
                `av.logging.restore_default_callback()` before any other library calls. If True
                the application may deadlock if threading_mode is set. See the PyAV documentation
                for details: https://pyav.org/docs/stable/overview/caveats.html#sub-interpeters
            framerate: [DEPRECATED] Use `frame_rate` instead. Retained as a deprecated
                alias for backwards compatibility; ignored when `frame_rate` is provided.
            frame_numbering: Origin for decoded frame ordinals. RELATIVE (default) numbers the
                first frame read after each successful seek as 0. SOURCE counts decoded frames
                from the source beginning, including seek preroll. Neither mode resets timestamps.

        Raises:
            OSError: file could not be found or access was denied
            VideoOpenFailure: video could not be opened (may be corrupted)
            ValueError: specified frame rate is invalid
        """
        # NOTE(https://scenedetect.com/issues/258): `read()` skips over corrupt packets and
        # continues decoding. `self._container.discard_corrupt = True` may be a future
        # refinement for frames FFmpeg flags as corrupt but still decodes.
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
        # Ensure specified frame rate is valid if set.
        if frame_rate is not None and frame_rate < MAX_FPS_DELTA:
            raise ValueError(f"Specified frame rate ({float(frame_rate):f}) is invalid!")

        self._name = "" if name is None else name
        self._path = ""
        self._frame: av.VideoFrame | None = None
        self._pending_frame: av.VideoFrame | None = None
        self._seek_origin: TimecodeLike = 0
        self._decoder: ty.Generator | None = None
        self._reopened = True
        self._decode_failures = 0
        self._warning_displayed = False

        if threading_mode:
            try:
                threading_mode = av.codec.context.ThreadType[threading_mode.upper()]  # type: ignore[attr-defined]
            except KeyError as _:
                raise ValueError(
                    f"Invalid threading mode! Must be one of: {VALID_THREAD_MODES}"
                ) from None

        if not suppress_output:
            logger.debug("Restoring default ffmpeg log callbacks.")
            av.logging.restore_default_callback()  # type: ignore[attr-defined]

        try:
            if isinstance(path_or_io, (str, os.PathLike)):
                self._path: str = os.fspath(path_or_io)
                # File handle is intentionally long-lived and tied to the VideoStream.
                self._io = open(self._path, "rb")  # noqa: SIM115
                if not self._name:
                    self._name = get_file_name(self._path, include_extension=False)
            else:
                self._io = path_or_io

            self._container: av.container.InputContainer = av.open(self._io)  # type: ignore[attr-defined]
            if threading_mode is not None:
                self._video_stream.thread_type = threading_mode
                self._reopened = False
                logger.debug("Threading mode set: %s", threading_mode)
        except OSError:
            raise
        except Exception as ex:
            raise VideoOpenFailure(str(ex)) from ex

        if frame_rate is None:
            # Calculate frame rate from video container. `guessed_rate` below appears in PyAV 9.
            detected_rate = (
                self._video_stream.guessed_rate
                if hasattr(self._video_stream, "guessed_rate")
                else self._codec_context.framerate
            )
            if detected_rate is None or detected_rate == 0:
                raise FrameRateUnavailable()
            if detected_rate < MAX_FPS_DELTA:
                raise FrameRateUnavailable()
            self._frame_rate: Fraction = framerate_to_fraction(detected_rate)
        else:
            assert frame_rate >= MAX_FPS_DELTA
            self._frame_rate: Fraction = framerate_to_fraction(frame_rate)

        # Calculate duration after we have set the framerate.
        self._duration_frames = self._get_duration()

    def __del__(self):
        # Finalizers must never raise - an exception here becomes an unraisable error. During
        # interpreter shutdown the underlying handles are reclaimed by the OS anyway.
        try:
            # Close the decode generator first to break its cycle with the container.
            decoder = getattr(self, "_decoder", None)
            if decoder is not None:
                decoder.close()
            # `_container` is unset if `__init__` raised before `av.open()` succeeded.
            container = getattr(self, "_container", None)
            if container is not None:
                container.close()
        except Exception:
            pass

    #
    # VideoStream Methods/Properties
    #

    BACKEND_NAME = "pyav"
    """Unique name used to identify this backend."""

    @property
    def path(self) -> str:
        """Video path."""
        return self._path

    @property
    def name(self) -> str:
        """Name of the video, without extension."""
        return self._name

    @property
    def is_seekable(self) -> bool:
        """True if seek() is allowed, False otherwise."""
        return self._io.seekable()

    @property
    def frame_size(self) -> tuple[int, int]:
        """Size of each video frame in pixels as a tuple of (width, height)."""
        return (self._codec_context.width, self._codec_context.height)

    @property
    def duration(self) -> FrameTimecode:
        """Duration of the video as a FrameTimecode."""
        return self.base_timecode + self._duration_frames

    @property
    def frame_rate(self) -> Fraction:
        """Frame rate in frames/sec as a rational Fraction."""
        return self._frame_rate

    @property
    def rate(self) -> Fraction:
        return self._video_stream.guessed_rate

    @property
    def time_base(self) -> Fraction | None:
        if self._frame:
            return self._frame.time_base
        return None

    @property
    def aspect_ratio(self) -> float:
        """Pixel aspect ratio as a float (1.0 represents square pixels)."""
        if (
            not hasattr(self._codec_context, "display_aspect_ratio")
            or self._codec_context.display_aspect_ratio is None
        ):
            return 1.0
        ar_denom = self._codec_context.display_aspect_ratio.denominator
        if ar_denom <= 0:
            return 1.0
        display_aspect_ratio = self._codec_context.display_aspect_ratio.numerator / ar_denom
        assert self.frame_size[0] > 0 and self.frame_size[1] > 0
        frame_aspect_ratio = self.frame_size[0] / self.frame_size[1]
        return display_aspect_ratio / frame_aspect_ratio

    def seek(self, target: TimecodeLike) -> None:
        """Position the next read at a source frame ordinal or presentation time.

        Integer targets are zero-based source ordinals in both numbering modes and are reached
        by sequential decoding. For example, `seek(4)` followed by `read()` reads the fifth source
        frame. Its ordinal is 4 in SOURCE mode and 0 in RELATIVE mode.

        Time targets select the first frame at or after the target encountered during preroll.
        RELATIVE mode uses a native timestamp seek; SOURCE mode counts frames while decoding from
        the beginning or continuing forward. A successful seek restarts RELATIVE numbering at 0
        without changing the source-relative presentation timestamps.

        Arguments:
            target: A source frame ordinal (int or digit-only string), or a presentation time
                (float seconds, timecode string, or Timecode).

        Raises:
            SeekError: Seeking is unsupported or the target cannot be reached.
            TypeError: The target type is unsupported.
            ValueError: The target is negative, non-finite, or malformed, or has an invalid
            time base.
        """

        if not self.is_seekable:
            raise SeekError("This source does not support seeking.")
        parsed = parse_frame_or_time(target)
        if parsed < 0:
            raise ValueError("Target cannot be negative!")

        if isinstance(parsed, Fraction):
            stream = self._video_stream
            time_base = stream.time_base
            if time_base is None or time_base <= 0:
                raise SeekError("The stream has no usable time base.")
            raw_timestamp = parsed + (stream.start_time or 0) * stream.time_base
            target_pts = raw_timestamp // stream.time_base

            if self._frame_numbering is FrameNumbering.RELATIVE:
                if self._decoder is not None:
                    self._decoder.close()
                self._decoder = None
                self._pending_frame = None
                try:
                    self._container.seek(target_pts, stream=stream)
                except (OSError, OverflowError, av.error.FFmpegError) as ex:  # type: ignore[attr-defined]
                    raise SeekError("Could not seek to the requested time.") from ex
            else:
                if self.position and self.position.timecode.seconds >= parsed:
                    self.reset()

            while True:
                try:
                    next_frame = self._decode_next_frame()
                except av.error.EOFError as ex:  # type: ignore[attr-defined]
                    raise SeekError("Could not reach the requested time.") from ex

                if next_frame is None:
                    raise SeekError("Could not reach the requested time.")

                if next_frame.pts is None or next_frame.time_base is None:
                    raise ValueError("Decoded frame has no usable presentation timestamp.")

                if next_frame.pts * next_frame.time_base >= raw_timestamp:
                    self._pending_frame = next_frame
                    if self._frame_numbering is FrameNumbering.RELATIVE:
                        self._frame = None
                        self._position = None
                    self._seek_origin = target
                    return
                if self._frame_numbering is FrameNumbering.SOURCE:
                    self._record_decoded_frame(next_frame)

        else:
            if self._frame_numbering is FrameNumbering.RELATIVE or parsed <= self.frame_number:
                self.reset()
            for _ in range(self.frame_number + 1, parsed):
                try:
                    frame = self._decode_next_frame()
                except av.error.EOFError as ex:  # type: ignore[attr-defined]
                    raise SeekError("Could not reach the requested frame.") from ex

                if frame is None:
                    raise SeekError("Could not reach the requested frame.")

                if self._frame_numbering is FrameNumbering.SOURCE:
                    self._record_decoded_frame(frame)

            self._seek_origin = target

    def reset(self):
        """Reopen at the source beginning and clear the frame position and seek origin.

        Preserve the current codec threading mode and the one-shot EOF recovery guard.
        """
        thread_type = self._video_stream.thread_type
        if self._decoder is not None:
            self._decoder.close()
        self._container.close()
        self._frame = None
        self._decoder = None
        self._pending_frame = None
        self._position = None
        self._seek_origin = 0
        try:
            self._io.seek(0)
            self._container = av.open(self._io)
            self._video_stream.thread_type = thread_type
        except Exception as ex:
            raise VideoOpenFailure() from ex

    def read(self, decode: bool = True) -> np.ndarray | bool:
        while True:
            try:
                frame = self._decode_next_frame()
            except av.error.EOFError:  # type: ignore[attr-defined]
                if self._handle_eof():
                    continue
                return False

            if frame is None:
                return False

            result = frame.to_ndarray(format="bgr24") if decode else True
            self._record_decoded_frame(frame)
            return result

    #
    # Private Methods/Properties
    #

    @property
    def _video_stream(self):
        """PyAV `av.video.stream.VideoStream` being used."""
        return self._container.streams.video[0]

    @property
    def _codec_context(self):
        """PyAV `av.codec.context.CodecContext` being used."""
        return self._video_stream.codec_context

    def _normalized_pts(self) -> int:
        """PTS of the current frame relative to the start of the stream. Some files have a
        nonzero stream start_time (e.g. from edit lists); other backends report the first
        frame's presentation time as 0, so we must do the same."""
        assert self._frame is not None and self._frame.pts is not None
        start_time = self._video_stream.start_time or 0
        if start_time and self._video_stream.time_base != self._frame.time_base:
            start_time = int(start_time * self._video_stream.time_base / self._frame.time_base)
        return self._frame.pts - start_time

    def _get_duration(self) -> int:
        """Get video duration as number of frames based on the video and set framerate."""
        # See https://pyav.org/docs/develop/api/time.html for details on how ffmpeg/PyAV
        # handle time calculations internally and which time base to use.
        assert self.frame_rate is not None, "Frame rate must be set before calling _get_duration!"
        # See if we can obtain the number of frames directly from the stream itself.
        if self._video_stream.frames > 0:
            return self._video_stream.frames
        # Calculate based on the reported container duration.
        duration_sec = None
        container = self._video_stream.container
        if container.duration is not None and container.duration > 0:
            # Containers use AV_TIME_BASE as the time base.
            duration_sec = float(self._video_stream.container.duration / av.time_base)
        # Lastly, if that calculation fails, try to calculate it based on the stream duration.
        if duration_sec is None or duration_sec < MAX_FPS_DELTA:
            if self._video_stream.duration is None:
                logger.warning("Video duration unavailable.")
                return 0
            # Streams use stream `time_base` as the time base.
            time_base = self._video_stream.time_base
            if time_base.denominator == 0:
                logger.warning(
                    "Unable to calculate video duration: time_base (%s) has zero denominator!",
                    str(time_base),
                )
                return 0
            duration_sec = float(self._video_stream.duration / time_base)
        return round(duration_sec * self.frame_rate)

    def _handle_eof(self):
        """Attempt one recovery from an EOF error in AUTO/FRAME decoding.

        For seekable sources, reopen with codec threading disabled and replay the consumed
        prefix to restore frame ordinals. Leave the next frame unread. Replay assumes that
        reopening reproduces the consumed frame sequence.
        """
        # Don't re-open the video if we already did.
        if self._reopened:
            return False
        # Don't re-open the video if we can't seek or aren't in AUTO/FRAME thread_type mode.
        if not self.is_seekable or self._video_stream.thread_type.name not in ("AUTO", "FRAME"):
            return False

        # Replay reads must not start another recovery attempt.
        self._reopened = True
        expected_position = self.position
        frames_read = self.frame_number + 1
        seek_origin = self._seek_origin
        self.reset()
        # reset() preserves the mode; use a non-threaded path for this compatibility retry.
        self._video_stream.thread_type = "NONE"

        if self.frame_numbering is FrameNumbering.SOURCE:
            self.seek(frames_read)
        else:
            self.seek(seek_origin)
            for _ in range(frames_read):
                if self.read(decode=False) is False:
                    raise SeekError("Could not replay the consumed frames during EOF recovery.")

        if self.position != expected_position:
            raise SeekError("Could not restore the expected position during EOF recovery.")
        # Internal recovery seeks must not replace the original public seek target.
        self._seek_origin = seek_origin
        return True

    def _decode_next_frame(self) -> av.VideoFrame | None:
        """Decode one frame without publishing a position."""
        if self._pending_frame is not None:
            frame = self._pending_frame
            self._pending_frame = None
            return frame
        consecutive_failures = 0
        while True:
            # Reuse a persistent decoder generator so the codec's internal frame buffer (used for
            # B-frame reordering) is never flushed prematurely. Creating a new generator each call
            # caused the last buffered frame to be lost at EOF.
            if self._decoder is None:
                self._decoder = self._container.decode(video=0)
            try:
                assert self._decoder is not None
                return next(self._decoder)
            # NOTE: EOFError subclasses FFmpegError, so this clause must come first.
            except av.error.EOFError:  # type: ignore[attr-defined]
                raise
            except StopIteration:
                return None
            except av.error.FFmpegError as ex:  # type: ignore[attr-defined]
                # Failed decode attempts do not publish a frame or advance its ordinal.
                self._decode_failures += 1
                consecutive_failures += 1
                # The decoder generator is closed once an exception propagates through it;
                # recreating it (next loop iteration) resumes demuxing after the bad packet.
                self._decoder = None
                if consecutive_failures >= MAX_CONSECUTIVE_DECODE_FAILURES:
                    logger.error(
                        "Failed to decode %d consecutive frames, stopping: %s",
                        consecutive_failures,
                        ex,
                    )
                    return None
                logger.debug("Frame failed to decode: %s", ex)
                if not self._warning_displayed and self._decode_failures > 1:
                    self._warning_displayed = True
                    logger.warning("Failed to decode some frames, results may be inaccurate.")
                continue

    def _record_decoded_frame(self, frame: av.VideoFrame) -> None:
        if frame.pts is None or frame.time_base is None:
            raise ValueError("Decoded frame has no usable presentation timestamp.")
        self._frame = frame
        self._record_frame(
            Timecode(
                pts=self._normalized_pts(),
                time_base=frame.time_base,
            )
        )
