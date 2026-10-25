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
from enum import Enum, auto
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
)
from scenedetect.platform import StrPath, get_file_name
from scenedetect.video_stream import (
    FrameRateUnavailable,
    SeekError,
    VideoOpenFailure,
    VideoStream,
)

logger = getLogger("pyscenedetect")
VALID_THREAD_MODES = ["NONE", "SLICE", "FRAME", "AUTO"]

# FFmpeg options used when opening the container. PyAV sets AVFMT_FLAG_GENPTS on every input
# (documented in `av.open()` as of PyAV 19.1). On containers that only store decode timestamps
# (e.g. AVI) the generated PTS comes out permuted once B-frames are reordered, and even FFmpeg's
# `best_effort_timestamp` is wrong for the first frames before it falls back to DTS. Disabling
# the flag is required on every PyAV version; see https://scenedetect.com/issues/590 and
# https://github.com/PyAV-Org/PyAV/pull/2478.
_CONTAINER_OPTIONS = {"fflags": "-genpts"}

# `Frame.best_effort_timestamp` was added in PyAV 19.1, which requires Python 3.12+. Older PyAV
# versions remain supported on Python 3.10/3.11, so its absence must be handled.
_HAS_BEST_EFFORT_TIMESTAMP = hasattr(av.VideoFrame, "best_effort_timestamp")


class _TimeSource(Enum):
    """The origin of the stream's frame position properties.

    This should be calculated once per stream from the first decoded frame. This source must then
    be used for all subsequent frames."""

    PTS = auto()
    """Frames carry presentation timestamps."""
    DTS = auto()
    """Frames only carry decode timestamps (e.g. AVI, some MPEG-TS)."""
    FRAMES = auto()
    """Frames carry no timestamps at all (e.g. raw Annex-B H.264); count decoded frames."""


MAX_CONSECUTIVE_DECODE_FAILURES = 8
"""Number of consecutive frame decode failures after which `VideoStreamAv.read()` gives up.
Isolated corrupt frames are skipped; this bound ensures a truncated file still terminates."""


def _to_fraction(value) -> Fraction:
    """PyAV >= 19.0 returns `av.AVRational` for time bases and frame rates. The backend must
    convert to `Fraction` so downstream arithmetic works correctly."""
    return Fraction(value.numerator, value.denominator)


def _frame_timestamp(frame) -> int | None:
    """Timestamp of `frame` in units of `frame.time_base`, or None if it has none.

    Uses FFmpeg's estimate (`best_effort_timestamp`, PyAV >= 19.1) when available: the PTS, unless
    PTS values have been missing or out of order more often than DTS values, in which case the
    DTS. Otherwise the PTS, falling back to the DTS. With GENPTS disabled (`_CONTAINER_OPTIONS`)
    both give the same result for inputs that only store DTS; the estimate only differs for
    inputs whose PTS is present but partly broken, where it may switch to DTS mid-stream like
    ffmpeg/ffplay do."""
    if _HAS_BEST_EFFORT_TIMESTAMP:
        return frame.best_effort_timestamp
    return frame.pts if frame.pts is not None else frame.dts


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
    ):
        """Open a video by path.

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
                for valid threading modes ('AUTO', 'FRAME', 'NONE', and 'SLICE'). If this mode is
                'AUTO' or 'FRAME' and not all frames have been decoded, the video will be reopened
                if seekable, and the remaining frames decoded in single-threaded mode.
            suppress_output: If False, ffmpeg output will be sent to stdout/stderr by calling
                `av.logging.restore_default_callback()` before any other library calls. If True
                the application may deadlock if threading_mode is set. See the PyAV documentation
                for details: https://pyav.org/docs/stable/overview/caveats.html#sub-interpeters
            framerate: [DEPRECATED] Use `frame_rate` instead. Retained as a deprecated
                alias for backwards compatibility; ignored when `frame_rate` is provided.

        Raises:
            OSError: file could not be found or access was denied
            VideoOpenFailure: video could not be opened (may be corrupted)
            ValueError: specified frame rate is invalid
        """
        # NOTE(https://scenedetect.com/issues/258): `read()` skips over corrupt packets and
        # continues decoding. `self._container.discard_corrupt = True` may be a future
        # refinement for frames FFmpeg flags as corrupt but still decodes.
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
        # Ensure specified frame rate is valid if set.
        if frame_rate is not None and frame_rate < MAX_FPS_DELTA:
            raise ValueError(f"Specified frame rate ({float(frame_rate):f}) is invalid!")

        self._name = "" if name is None else name
        self._path = ""
        self._frame: av.VideoFrame | None = None
        self._decoder: ty.Generator | None = None
        self._reopened = True
        self._decode_failures = 0
        self._warning_displayed = False
        # Presentation time of `_frame` (see `_update_timecode`), None until a frame is read.
        self._timecode: Timecode | None = None
        # Decided from the first decoded frame, None until then. Kept across `reset()` since it is
        # a property of the input, not of the container instance.
        self._time_source: _TimeSource | None = None
        # In DTS mode, the DTS of the first frame decoded from the start of the stream. Frames are
        # emitted after the decoder's reordering delay, so this includes both the stream start
        # time and that delay. Stored with the time base it was observed in.
        self._dts_offset: int = 0
        self._dts_offset_time_base: Fraction | None = None
        # Set once a timestamp going backwards has been reported for this stream.
        self._warned_non_monotonic = False
        # Number of frames decoded since the last seek/reset (position source in frame-count mode).
        self._frames_decoded = 0
        # Last observed gap between consecutive frames in ticks of `_timecode.time_base`, used to
        # extrapolate a position for frames that carry no timestamp.
        self._last_delta = 0
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
            # PyAV behavior has changed in version 19:
            #   PyAV  < 19 - unknown rate is returned as None
            #   PyAV >= 19 - returns AVRational(0, 1) which is falsy
            if not detected_rate or detected_rate < MAX_FPS_DELTA:
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
    def duration(self) -> FrameTimecode:
        """Duration of the video as a FrameTimecode."""
        return self.base_timecode + self._duration_frames

    @property
    def frame_rate(self) -> Fraction:
        """Frame rate in frames/sec as a rational Fraction."""
        return self._frame_rate

    @property
    def position(self) -> FrameTimecode:
        """Current position within stream as FrameTimecode.

        This can be interpreted as presentation time stamp, thus frame 1 corresponds
        to the presentation time 0.  Returns 0 even if `frame_number` is 1."""
        if self._timecode is None:
            return self.base_timecode
        return FrameTimecode(timecode=self._timecode, fps=self.frame_rate)

    @property
    def position_ms(self) -> float:
        """Current position within stream as a float of the presentation time in
        milliseconds. The first frame has a PTS of 0."""
        if self._timecode is None:
            return 0.0
        return float(self._timecode.seconds) * 1000.0

    @property
    def frame_number(self) -> int:
        """Current position within stream as the frame number (CFR-equivalent).

        Will return 0 until the first frame is `read`. For VFR video this is an approximation
        derived from PTS * framerate; use `position` for accurate PTS-based timing."""
        if self._timecode is None:
            return 0
        return round(float(self._timecode.seconds) * float(self.frame_rate)) + 1

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
        """Seek to the given timecode. If given as a frame number, represents the current seek
        pointer (e.g. if seeking to 0, the next frame decoded will be the first frame of the video).

        For 1-based indices (first frame is frame #1), the target frame number needs to be converted
        to 0-based by subtracting one. For example, if we want to seek to the first frame, we call
        seek(0) followed by read(). If we want to seek to the 5th frame, we call seek(4) followed
        by read(), at which point frame_number will be 5.

        May not be supported on all input codecs (see `is_seekable`). Elementary streams usually
        cannot be seeked, and may raise `SeekError`.

        Arguments:
            target: Target position in video stream to seek to.
                If float, interpreted as time in seconds.
                If int, interpreted as frame number.
        Raises:
            ValueError: `target` is not a valid value (i.e. it is negative), or the stream is
                closed.
        """
        self._check_open()
        if not isinstance(target, FrameTimecode):
            target = FrameTimecode(target, self.frame_rate)
        if target < 0:
            raise ValueError("Target cannot be negative!")
        beginning = target == 0

        target = self.base_timecode + target
        if target >= 1:
            target = target - 1
        target_pts = (self._video_stream.start_time or 0) + int(
            (self.base_timecode + target).seconds / _to_fraction(self._video_stream.time_base)
        )
        # If no frame has been decoded yet, the container is still at the start of the stream.
        # Decode one frame from there first so the time source (and in DTS mode the reordering
        # delay, which is only observable on the first frame) is known before moving away.
        if self._time_source is None and not beginning:
            self.read(decode=False)
        self._frame = None
        self._decoder = None
        self._timecode = None
        # Without timestamps, frame numbering resumes from the seek target.
        self._frames_decoded = max(target.frame_num, 0)
        # TODO(https://scenedetect.com/issues/590): For some containers (e.g. MPEG-TS), we can end
        # up *after* the `target_pts`. For example, seeking to frame 100 may have us end up on 151.
        # This means the loop below never gets to walk forward to the exact frame. We need to seek
        # to an earlier keyframe and then readc forward to fix this.
        try:
            self._container.seek(target_pts, stream=self._video_stream)
        except av.error.FFmpegError as ex:  # type: ignore[attr-defined]
            raise SeekError(f"Unable to seek in stream: {ex}") from ex
        if not beginning:
            self.read(decode=False)
        while self.position < target:
            if self.read(decode=False) is False:
                break

    def reset(self):
        """Close and re-open the VideoStream (should be equivalent to calling `seek(0)`)."""
        self._check_open()
        self._container.close()
        self._frame = None
        self._decoder = None
        self._timecode = None
        self._frames_decoded = 0
        self._warned_non_monotonic = False
        try:
            self._container = self._open_container(rewind=True)
        except Exception as ex:
            raise VideoOpenFailure() from ex

    def read(self, decode: bool = True) -> np.ndarray | bool:
        self._check_open()
        consecutive_failures = 0
        while True:
            # *NOTE*: We *must* reuse the same decoder generator for the lifetime of the container.
            # Creating a new generator at each call would cause the last buffered frame to be lost
            # when we hit EOF due to the codec's internal buffer having been flushed.
            if self._decoder is None:
                self._decoder = self._container.decode(video=0)
            try:
                last_frame = self._frame
                assert self._decoder is not None
                self._frame = next(self._decoder)
            # *NOTE*: EOFError subclasses FFmpegError, so this clause must come first.
            except av.error.EOFError:  # type: ignore[attr-defined]
                self._frame = last_frame
                if self._handle_eof():
                    return self.read(decode)
                return False
            except StopIteration:
                return False
            except av.error.FFmpegError as ex:  # type: ignore[attr-defined]
                # `next()` was raised before assignment, so `self._frame` is still the last valid
                # frame. Positions and frame numbers should be unaffected by any skipped packets.
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
                    return False
                logger.debug("Frame failed to decode: %s", ex)
                if not self._warning_displayed and self._decode_failures > 1:
                    self._warning_displayed = True
                    logger.warning("Failed to decode some frames, results may be inaccurate.")
                continue
            assert self._frame is not None
            self._frames_decoded += 1
            self._update_timecode()
            return self._frame.to_ndarray(format="bgr24") if decode else True

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
        """Open `_io` as a PyAV container with the options this backend relies on. Every open
        must go through here so a re-open (`reset`, `_handle_eof`) keeps the same behaviour.

        Arguments:
            rewind: Seek `_io` back to the start before opening, for re-opens of a stream that
                has already been read from.
        """
        if rewind and self._io.seekable():
            self._io.seek(0)
        return av.open(self._io, container_options=_CONTAINER_OPTIONS)  # type: ignore[attr-defined]

    def _update_timecode(self):
        """Set `_timecode` to the presentation time of `_frame`, relative to the first frame of
        the stream. The VideoStream contract is to report the first frame as 0.

        The first decoded frame decides where timestamps come from for the whole stream: PTS when
        present, otherwise DTS, otherwise the number of decoded frames. The source determines the
        offset that is subtracted; the timestamp itself comes from `_frame_timestamp`. If a frame
        lacks a timestamp, it's extrapolated from the previous frame.
        """
        frame = self._frame
        assert frame is not None
        timestamp = _frame_timestamp(frame)
        if self._time_source is None:
            if frame.pts is not None:
                self._time_source = _TimeSource.PTS
            elif timestamp is not None:
                # Frames are emitted after the decoder's reordering delay, so the first frame's
                # DTS includes both the stream start time and that delay.
                self._time_source = _TimeSource.DTS
                self._dts_offset, self._dts_offset_time_base = timestamp, self._frame_time_base
                logger.debug(
                    "Stream has no PTS, using DTS with offset %d (time base %s).",
                    self._dts_offset,
                    self._dts_offset_time_base,
                )
            else:
                self._time_source = _TimeSource.FRAMES
                logger.debug("Stream has no timestamps, positions are derived from frame count.")

        if self._time_source == _TimeSource.FRAMES:
            self._timecode = Timecode(
                pts=max(self._frames_decoded - 1, 0), time_base=1 / self.frame_rate
            )
            return
        if self._time_source == _TimeSource.PTS:
            offset, offset_time_base = (
                self._video_stream.start_time or 0,
                _to_fraction(self._video_stream.time_base),
            )
        else:
            offset, offset_time_base = self._dts_offset, self._dts_offset_time_base
        if timestamp is None or not frame.time_base:
            # E.g. frames flushed from the decoder at end of stream carry no DTS. Extrapolate from
            # the previous frame rather than falling back to 0 or stalling, so positions stay
            # monotonic.
            self._timecode = self._extrapolated_timecode()
            return
        time_base = self._frame_time_base
        if offset and offset_time_base is not None and offset_time_base != time_base:
            offset = int(offset * offset_time_base / time_base)
        timecode = Timecode(pts=timestamp - offset, time_base=time_base)
        previous = self._timecode
        if previous is not None and previous.time_base == timecode.time_base:
            if timecode.pts > previous.pts:
                self._last_delta = timecode.pts - previous.pts
            elif timecode.pts < previous.pts and not self._warned_non_monotonic:
                # With GENPTS disabled this is no longer expected for DTS-only inputs, so it
                # points at a genuinely broken file (or a new PyAV/FFmpeg behaviour).
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

    def _extrapolated_timecode(self) -> Timecode | None:
        """Position one frame after the current one, using the last observed gap between frames
        (or the nominal frame duration if none has been observed yet)."""
        previous = self._timecode
        if previous is None:
            return None
        delta = self._last_delta
        if delta <= 0:
            delta = max(round(1 / (self.frame_rate * previous.time_base)), 1)
        return Timecode(pts=previous.pts + delta, time_base=previous.time_base)

    def _get_duration(self) -> int:
        """Get video duration as number of frames based on the video and set framerate."""
        # See https://pyav.org/docs/develop/api/time.html for details on how ffmpeg/PyAV
        # handle time calculations internally and which time base to use.
        assert self.frame_rate is not None, "Frame rate must be set before calling _get_duration!"
        # See if we can obtain the number of frames directly from the stream itself.
        # TODO(https://scenedetect.com/issues/590): AVI files remuxed by ffmpeg can declare a tick
        # rate (e.g. 600/1) as the stream rate, in which case `frames` counts ticks, not frames (a
        # 480 frame clip reports 12012). OpenCV reports the same value, so this matches ffmpeg, but
        # `duration * frame_rate` would be correct here. Pre-dates the GENPTS workaround.
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
            # Streams use stream `time_base` as the time base. Unset is None on PyAV < 19 and
            # a falsy AVRational(0, 1) on PyAV 19+.
            time_base = self._video_stream.time_base
            if not time_base:
                logger.warning("Unable to calculate video duration: stream time_base is unset.")
                return 0
            # `duration` is in units of `time_base`, so seconds = duration * time_base.
            duration_sec = float(self._video_stream.duration * _to_fraction(time_base))
        return round(duration_sec * self.frame_rate)

    def _handle_eof(self):
        """Fix for issue where if thread_type is 'AUTO' the whole video is not decoded.

        Re-open video if the threading mode is AUTO and we didn't decode all of the frames."""
        # Don't re-open the video if we already did, or if we already decoded all the frames.
        if self._reopened or self.frame_number >= self.duration:
            return False
        self._reopened = True
        # Don't re-open the video if we can't seek or aren't in AUTO/FRAME thread_type mode.
        if not self.is_seekable or self._video_stream.thread_type not in ("AUTO", "FRAME"):
            return False
        last_pos_secs = self.position.seconds
        orig_pos = self._io.tell()
        try:
            container = self._open_container(rewind=True)
        except:
            self._io.seek(orig_pos)
            raise
        self._container.close()
        self._container = container
        self._decoder = None
        self.seek(last_pos_secs)
        return True
