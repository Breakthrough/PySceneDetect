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

import contextlib
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

# FFmpeg options passed to `av.open()`. By default, PyAV enables `AVFMT_FLAG_GENPTS` (`+genpts`) on
# every input container. For containers that only store decode timestamps (e.g. AVI), `+genpts`
# synthesizes missing presentation timestamps (PTS) from packet decode timestamps (DTS), which are
# in decode order rather than presentation order. When the video contains B-frames, the decoder
# reorders frames into presentation order while keeping those decode-order PTS values attached,
# causing `frame.pts` (and `best_effort_timestamp` on the initial frames) to jump backwards and
# forwards. Disabling `genpts` leaves `frame.pts` as `None` on DTS-only streams so we can fall back
# to `frame.dts` cleanly. See https://scenedetect.com/issues/590 and
# https://github.com/PyAV-Org/PyAV/pull/2478.
_CONTAINER_OPTIONS = {"fflags": "-genpts"}


MAX_SEEK_PROBE_FRAMES = 32
"""Number of frames `VideoStreamAv.seek()` probes for a timestamp before or after a native
RELATIVE timestamp seek. Streams without timestamps (e.g. raw Annex-B H.264) cannot use this path.
This also caps how many leading frames without timestamps can be probed before the first native
seek: a file whose first timestamp is on frame 40 can be read sequentially, but not seeked this way
before reading. Integer seeks and SOURCE timestamp seeks are not subject to this probe limit.
"""

MAX_CONSECUTIVE_DECODE_FAILURES = 8
"""Number of consecutive frame decode failures after which `VideoStreamAv.read()` gives up.
Isolated corrupt frames are skipped; this bound ensures a truncated file still terminates."""


def _to_fraction(value) -> Fraction:
    """PyAV >= 19.0 returns `av.AVRational` for time bases and frame rates. The backend must
    convert to `Fraction` so downstream arithmetic works correctly."""
    return Fraction(value.numerator, value.denominator)


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
        # Timestamp of the latest decoded frame, including pending frames and seek preroll.
        # Public position is stored separately in `_position`.
        self._timecode: Timecode | None = None
        # Timestamp (and timebase) subtracted from every frame timestamp so the first frame is
        # at time 0. Decided based on the first decoded frame with a valid timestamp. Only set
        # once, even after `reset()` or `seek()`.
        self._offset: int | None = None
        self._offset_time_base: Fraction | None = None
        # Ensures we only log a warning once per pass (until `reset()`) if positions go backwards.
        self._warned_non_monotonic = False
        # 1-based count of frames decoded in the current native decoding pass, used to estimate
        # the time of frames without timestamps and for diagnostic logging.
        self._frames_decoded = 0
        # True if `_io` was opened by this object (from a path) and must be closed in `close()`.
        # Set before anything below can raise so a partially constructed object is safe to finalize.
        self._owns_io = False

        if threading_mode:
            try:
                threading_mode = av.codec.context.ThreadType[threading_mode.upper()]  # type: ignore[attr-defined]
            except KeyError as _:
                raise ValueError(
                    f"Invalid threading mode! Must be one of: {VALID_THREAD_MODES}"
                ) from None
        self._threading_mode = threading_mode

        if not suppress_output:
            logger.debug("Restoring default ffmpeg log callbacks.")
            av.logging.restore_default_callback()  # type: ignore[attr-defined]

        try:
            if isinstance(path_or_io, (str, os.PathLike)):
                self._path: str = os.fspath(path_or_io)
                # File handle is owned by this object and released in `close()` (or `__del__`).
                self._io = open(self._path, "rb")  # noqa: SIM115
                self._owns_io = True
                if not self._name:
                    self._name = get_file_name(self._path, include_extension=False)
            else:
                self._io = path_or_io

            self._container: av.container.InputContainer = self._open_container()  # type: ignore[attr-defined]
            if self._threading_mode is not None:
                self._video_stream.thread_type = self._threading_mode
                self._reopened = False
                logger.debug("Threading mode set: %s", self._threading_mode)
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
            # PyAV behavior has changed in version 19:
            #   PyAV  < 19 - unknown rate is returned as None
            #   PyAV >= 19 - returns AVRational(0, 1) which is falsy
            if not detected_rate or detected_rate < MAX_FPS_DELTA:
                raise FrameRateUnavailable()
            self._frame_rate: Fraction = framerate_to_fraction(detected_rate)
        else:
            assert frame_rate >= MAX_FPS_DELTA
            self._frame_rate: Fraction = framerate_to_fraction(frame_rate)

        # Cache source metadata so it remains available after closing.
        self._duration = self._get_duration()
        # TODO(https://scenedetect.com/issues/590): Some AVI files remuxed by ffmpeg set the stream
        # rate to a high tick rate (e.g. 600/1), causing `stream.frames` to report tick count
        # rather than actual frame count (e.g. 12012 instead of 480). OpenCV reports the same value
        # via CAP_PROP_FRAME_COUNT, but `duration_sec * frame_rate` would be more accurate when
        # `stream.frames` disagrees with the stream duration and codec frame rate.
        frame_count = self._video_stream.frames
        self._frame_count = frame_count if frame_count > 0 else None

    def __del__(self):
        # Finalizers must never raise - an exception here becomes an unraisable error. During
        # interpreter shutdown the underlying handles are reclaimed by the OS anyway.
        with contextlib.suppress(Exception):
            self.close()

    def close(self) -> None:
        """Close the video, releasing the decoder, the container, and the file handle opened if
        `path_or_io` is a path. File-like objects passed by the caller are left open. Has no
        effect if the stream is already closed. See
        :meth:`VideoStream.close() <scenedetect.video_stream.VideoStream.close>` for details."""
        if self._closed:
            return
        # Record the properties read from the container while it is open. They can't be read if
        # `__init__` raised (`__del__` also calls this method) or the video can't be decoded.
        with contextlib.suppress(Exception):
            self._closed_frame_size = self.frame_size
            self._closed_aspect_ratio = self.aspect_ratio
        # Close the decode generator first to break its cycle with the container.
        decoder = getattr(self, "_decoder", None)
        if decoder is not None:
            decoder.close()
            self._decoder = None
        # `_container` is unset if `__init__` raised before `av.open()` succeeded.
        container = getattr(self, "_container", None)
        if container is not None:
            container.close()
        # Closing the container does not close the file object backing it. Only close `_io`
        # if we opened it ourselves; file-like objects passed by the caller remain theirs.
        if getattr(self, "_owns_io", False):
            io = getattr(self, "_io", None)
            if io is not None:
                io.close()
        # Only mark the stream as closed once everything is released, so a failed `close()` can be
        # retried. The last decoded frame is dropped, since `position` is undefined once closed.
        self._closed = True
        self._frame = None
        self._timecode = None
        self._pending_frame = None
        self._position = None

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
        if self._closed:
            return self._closed_frame_size
        return (self._codec_context.width, self._codec_context.height)

    @property
    def duration(self) -> Fraction | None:
        """Duration of the video, or None if unavailable."""
        return self._duration

    @property
    def frame_count(self) -> int | None:
        """Reported total source frame count, or None if unavailable."""
        return self._frame_count

    @property
    def frame_rate(self) -> Fraction:
        """Frame rate in frames/sec as a rational Fraction."""
        return self._frame_rate

    @property
    def rate(self) -> Fraction | None:
        """Frame rate reported by the stream (PyAV `guessed_rate`), or None if unavailable."""
        guessed_rate = self._video_stream.guessed_rate
        return _to_fraction(guessed_rate) if guessed_rate else None

    @property
    def time_base(self) -> Fraction | None:
        if self._frame is not None and self._frame.time_base:
            return self._frame_time_base
        return None

    @property
    def aspect_ratio(self) -> float:
        """Pixel aspect ratio as a float (1.0 represents square pixels)."""
        if self._closed:
            return self._closed_aspect_ratio
        # Unset is None on PyAV < 19 and a falsy AVRational(0, 1) on PyAV 19+.
        dar = getattr(self._codec_context, "display_aspect_ratio", None)
        if not dar or dar.denominator <= 0:
            return 1.0
        display_aspect_ratio = dar.numerator / dar.denominator
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
            ValueError: The stream is closed, or the target is negative, non-finite, malformed,
                or has an invalid time base.
        """
        self._check_open()

        if not self.is_seekable:
            raise SeekError("This source does not support seeking.")
        parsed = parse_frame_or_time(target)
        if parsed < 0:
            raise ValueError("Target cannot be negative!")
        beginning = parsed == 0
        # Seeking to the start always re-opens the stream. The demuxer can only seek to keyframes
        # that carry a timestamp, so if the first one does not (as in some MPEG-TS files), seeking
        # the container to time 0 lands on a later keyframe instead.
        if beginning:
            self._reset_for_seek()
            return

        if isinstance(parsed, Fraction):
            if self._frame_numbering is FrameNumbering.RELATIVE:
                # Establish the timestamp offset before jumping away from the source prefix.
                while self._offset is None and self._frames_decoded < MAX_SEEK_PROBE_FRAMES:
                    if self._next_frame() is None:
                        break

                if self._offset is None:
                    raise SeekError("Unable to seek in stream without timestamps.")

                stream = self._video_stream
                time_base = stream.time_base
                if not time_base or time_base <= 0:
                    raise SeekError("The stream has no usable time base.")
                time_base = _to_fraction(time_base)

                assert self._offset_time_base is not None
                target_pts = (parsed + self._offset * self._offset_time_base) // time_base
                if self._decoder is not None:
                    self._decoder.close()
                self._decoder = None
                self._pending_frame = None
                try:
                    self._container.seek(target_pts, stream=stream)
                except (OSError, OverflowError, av.error.FFmpegError) as ex:  # type: ignore[attr-defined]
                    raise SeekError("Could not seek to the requested time.") from ex
                self._frame = None
                self._timecode = None
                self._frames_decoded = 0

                landed = None
                for _ in range(MAX_SEEK_PROBE_FRAMES):
                    try:
                        candidate = self._decode_next_frame()
                    except av.error.EOFError:  # type: ignore[attr-defined]
                        break

                    if candidate is None:
                        break

                    if self._frame_has_timestamp(candidate):
                        landed = self._timecode
                        self._pending_frame = candidate
                        break

                    # An estimate cannot establish where the container landed.
                    self._timecode = None

                if landed is None or landed.seconds > parsed:
                    self._reset_for_seek()
            else:
                if self.position and self.position.timecode.seconds >= parsed:
                    self._reset_for_seek()

            while True:
                try:
                    next_frame = self._decode_next_frame()
                except av.error.EOFError as ex:  # type: ignore[attr-defined]
                    raise SeekError("Could not reach the requested time.") from ex

                if next_frame is None:
                    raise SeekError("Could not reach the requested time.")

                assert self._timecode is not None

                if self._timecode.seconds >= parsed:
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
                self._reset_for_seek()
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
        self._check_open()
        thread_type = self._video_stream.thread_type
        if self._decoder is not None:
            self._decoder.close()
        self._container.close()
        self._frame = None
        self._decoder = None
        self._timecode = None
        self._frames_decoded = 0
        self._warned_non_monotonic = False
        self._pending_frame = None
        self._position = None
        self._seek_origin = 0
        try:
            self._container = self._open_container(rewind=True)
            self._video_stream.thread_type = thread_type
        except Exception as ex:
            raise VideoOpenFailure() from ex

    def read(self, decode: bool = True) -> np.ndarray | bool:
        self._check_open()
        frame = self._next_frame()
        if frame is None:
            return False

        result = frame.to_ndarray(format="bgr24") if decode else True
        self._record_decoded_frame(frame)
        return result

    def peek_timecode(self) -> Timecode | None:
        self._check_open()
        if self._pending_frame is None:
            self._pending_frame = self._next_frame()

        frame = self._pending_frame
        if frame is None:
            return None
        assert self._timecode is not None
        return self._timecode

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

    @property
    def _frame_time_base(self) -> Fraction:
        """Time base of the current frame as a `Fraction` (see `_to_fraction`)."""
        assert self._frame is not None and self._frame.time_base
        return _to_fraction(self._frame.time_base)

    def _open_container(self, rewind: bool = False) -> av.container.InputContainer:  # type: ignore[attr-defined]
        """Open `_io` as a PyAV container with `_CONTAINER_OPTIONS`.

        All container opens (initial open, `reset()`, and `_handle_eof()`) must go through this
        helper so container flags like `-genpts` stay applied after re-opening.

        Arguments:
            rewind: Seek `_io` back to byte 0 before opening (used when re-opening a stream).
        """
        if rewind and self._io.seekable():
            self._io.seek(0)
        return av.open(self._io, container_options=_CONTAINER_OPTIONS)  # type: ignore[attr-defined]

    def _reset_for_seek(self):
        """Call `reset()` on behalf of `seek()`, raising `SeekError` instead of `VideoOpenFailure`
        if the video cannot be re-opened, so `seek()` only raises the exceptions it documents."""
        try:
            self.reset()
        except VideoOpenFailure as ex:
            raise SeekError("Unable to seek in stream: failed to re-open video.") from ex

    def _frame_has_timestamp(self, frame: av.VideoFrame) -> bool:
        """True if `frame` carries a usable timestamp (a PTS or DTS, and a time base)."""
        return (
            frame is not None
            and bool(frame.time_base)
            and (frame.pts is not None or frame.dts is not None)
        )

    def _update_timecode(self, frame: av.VideoFrame):
        """Update `_timecode` with the presentation time of `frame` relative to the first frame.

        Each frame is placed at its PTS, falling back to its DTS when the PTS is missing. This is
        the same rule as OpenCV's FFmpeg backend. With `genpts` off, FFmpeg's
        `best_effort_timestamp` gives the same result on streams whose PTS are monotonic; it
        additionally switches to DTS once PTS has gone backwards more often than DTS. A frame with
        neither is placed one nominal frame period after the previous frame (see
        `_estimated_timecode()`). A warning is logged (once per pass) if a frame is placed before
        the previous frame's position, estimated or not.

        `_offset` is decided once, from the first frame that carries a timestamp. When that is
        the first frame and it has a PTS, the stream `start_time` is used so files with edit lists
        start at time 0 like the other backends. Otherwise the offset anchors the first frame at
        time 0 assuming the frames before it were spaced at the nominal frame rate. This covers
        DTS-only streams (e.g. AVI), whose first DTS is already past the stream start by the
        decoder's B-frame reordering delay, and streams whose first frames carry no
        timestamps at all.
        """
        assert frame is not None
        timestamp = frame.pts if frame.pts is not None else frame.dts
        if timestamp is None or not frame.time_base:
            self._timecode = self._estimated_timecode()
            return
        time_base = _to_fraction(frame.time_base)
        if self._offset is None:
            stream_time_base = self._video_stream.time_base
            if self._frames_decoded == 1 and frame.pts is not None and stream_time_base:
                self._offset = self._video_stream.start_time or 0
                self._offset_time_base = _to_fraction(stream_time_base)
            else:
                self._offset = timestamp - round(
                    (self._frames_decoded - 1) / (self.frame_rate * time_base)
                )
                self._offset_time_base = time_base
                logger.debug(
                    "First timestamp found on frame %d, using offset %d (time base %s).",
                    self._frames_decoded,
                    self._offset,
                    time_base,
                )
        offset = self._offset
        if offset and self._offset_time_base != time_base:
            assert self._offset_time_base is not None
            offset = int(offset * self._offset_time_base / time_base)
        timecode = Timecode(pts=timestamp - offset, time_base=time_base)
        # Compare with the previous decoded timestamp, including estimates.
        previous = self._timecode
        if (
            previous is not None
            and timecode.seconds < previous.seconds
            and not self._warned_non_monotonic
        ):
            # With `-genpts` set on the container, non-monotonic timestamps indicate either a
            # genuinely malformed input or unexpected demuxer/decoder behavior.
            self._warned_non_monotonic = True
            logger.warning(
                "Timestamps went backwards at frame %d (%.3fs -> %.3fs, PyAV %s); results "
                "may be inaccurate. See https://scenedetect.com/issues/590",
                self._frames_decoded,
                float(previous.seconds),
                float(timecode.seconds),
                av.__version__,
            )
        self._timecode = timecode

    def _estimated_timecode(self) -> Timecode:
        """The position we think the next frame should be at. Use only if we get a frame without a
        timestamp. Calculated as one (nominal) frame period from the previous frame's position, or
        as the frame count in nominal frame periods if there is no previous position."""
        previous = self._timecode
        if previous is None:
            return Timecode(pts=max(self._frames_decoded - 1, 0), time_base=1 / self.frame_rate)
        return Timecode(
            pts=previous.pts + self._frame_period(previous.time_base), time_base=previous.time_base
        )

    def _frame_period(self, time_base: Fraction) -> int:
        """Duration of one frame at the nominal frame rate in `time_base` ticks (at least 1)."""
        return max(round(1 / (self.frame_rate * time_base)), 1)

    def _next_frame(self) -> av.VideoFrame | None:
        """Return the next frame, attempting EOF recovery when needed."""
        while True:
            try:
                return self._decode_next_frame()
            except av.error.EOFError:  # type: ignore[attr-defined]
                if self._handle_eof():
                    continue
                return None

    def _get_duration(self) -> Fraction | None:
        """Get reported video duration in seconds, or None if unavailable.

        See https://pyav.org/docs/develop/api/time.html for details on how ffmpeg/PyAV
        handle time calculations internally and which time base to use.
        """
        stream = self._video_stream
        if (
            stream.duration is not None
            and stream.duration >= 0
            and stream.time_base is not None
            and stream.time_base > 0
        ):
            return stream.duration * _to_fraction(stream.time_base)
        logger.debug("Video-stream duration unavailable; trying container duration.")
        # Fall back to container duration, which may include other tracks.
        container = stream.container
        if container.duration is not None and container.duration >= 0:
            # Containers use AV_TIME_BASE as the time base.
            return Fraction(container.duration, av.time_base)

        logger.warning("Video duration unavailable.")
        return None

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
        thread_type = self._video_stream.thread_type
        thread_type = getattr(thread_type, "name", thread_type)
        if not self.is_seekable or thread_type not in ("AUTO", "FRAME"):
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
                frame = next(self._decoder)
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
            self._frames_decoded += 1
            self._update_timecode(frame)
            return frame

    def _record_decoded_frame(self, frame: av.VideoFrame) -> None:
        assert self._timecode is not None
        self._frame = frame
        self._record_frame(self._timecode)
