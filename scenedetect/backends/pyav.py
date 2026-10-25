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
"""Number of frames `VideoStreamAv.seek()` decodes looking for a timestamp before concluding the
stream has none and cannot be seeked (e.g. raw Annex-B H.264)."""

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
        # Presentation time of `_frame` relative to the start of the stream. None until the first
        # `read()` (and after `close()`/`reset()`).
        self._timecode: Timecode | None = None
        # Position of the most recent frame that had a valid timestamp. Used to track monotonicity.
        self._last_timestamp: Timecode | None = None
        # Timestamp (and timebase) subtracted from every frame timestamp such that that frame 1 is
        # at time 0. Decided based on the the first decoded frame with a valid timestamp. Only set
        # once, even after `reset()` or `seek()`.
        self._offset: int | None = None
        self._offset_time_base: Fraction | None = None
        # Ensures we only log a warning once per stream if timestamps go backwards.
        self._warned_non_monotonic = False
        # 1-based count of frames decoded in the current stream pass, used to estimate the position
        # of frames without timestamps and for diagnostic logging.
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
        self._timecode = None

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
        cannot be seeked, and may raise `SeekError`, after which the stream position is undefined
        until `reset()` is called.

        Arguments:
            target: Target position in video stream to seek to.
                If float, interpreted as time in seconds.
                If int, interpreted as frame number.
        Raises:
            SeekError: Stream does not support seeking, or target cannot be seeked to.
            ValueError: `target` is not a valid value (i.e. it is negative), or the stream is
                closed.
        """
        self._check_open()
        if not isinstance(target, FrameTimecode):
            target = FrameTimecode(target, self.frame_rate)
        if target < 0:
            raise ValueError("Target cannot be negative!")
        if not self.is_seekable:
            raise SeekError("Stream is not seekable.")
        beginning = target == 0

        target = self.base_timecode + target
        if target >= 1:
            target = target - 1
        # The timestamp offset is anchored at the start of the stream (see `_update_timecode()`),
        # so it must only ever be decided from frames decoded in order from the start: a seek can
        # land on a later keyframe. While it is unknown, seeking to the start re-opens the stream,
        # and seeking elsewhere first decodes frames until one carries a timestamp. Streams without
        # any timestamps (e.g. raw H.264) cannot be seeked, so give up after
        # `MAX_SEEK_PROBE_FRAMES` frames. As with any failed seek, the stream position is then
        # undefined until `reset()` is called.
        if beginning and self._offset is None:
            self.reset()
            return
        stream_time_base = self._video_stream.time_base
        if not stream_time_base:
            raise SeekError("Unable to seek in stream: stream time_base is unset.")
        if self._offset is None:
            while self._offset is None and self._frames_decoded < MAX_SEEK_PROBE_FRAMES:
                if self.read(decode=False) is False:
                    break
            if self._offset is None:
                raise SeekError("Unable to seek in stream without timestamps.")
        # Positions are relative to `_offset`, so the seek target must be too. For streams whose
        # first frame has a PTS, this is the stream's `start_time`.
        stream_time_base = _to_fraction(stream_time_base)
        assert self._offset is not None and self._offset_time_base is not None
        offset = self._offset
        if offset and self._offset_time_base != stream_time_base:
            offset = int(offset * self._offset_time_base / stream_time_base)
        target_pts = offset + int((self.base_timecode + target).seconds / stream_time_base)
        # TODO(https://scenedetect.com/issues/590): For some containers (e.g. MPEG-TS), we can end
        # up *after* the `target_pts`. For example, seeking to frame 100 may have us end up on 151.
        # This means the loop below never gets to walk forward to the exact frame. We need to seek
        # to an earlier keyframe and then read forward to fix this.
        try:
            self._container.seek(target_pts, stream=self._video_stream)
        except av.error.FFmpegError as ex:  # type: ignore[attr-defined]
            raise SeekError(f"Unable to seek in stream: {ex}") from ex
        self._frame = None
        self._decoder = None
        self._timecode = None
        self._last_timestamp = None
        # Seed `_frames_decoded` with the target frame before walking forward from the keyframe so
        # `_estimated_timecode()` has a fallback if no post-seek frame carries a timestamp, then
        # sync it to `self.frame_number` once the walk completes.
        self._frames_decoded = 0 if beginning else max(target.frame_num, 0)
        if not beginning:
            # The keyframe landed on may itself lack a timestamp, in which case its position is
            # unknown (it is estimated at the target). Keep reading until a frame carries one
            # before comparing against the target, otherwise the walk would stop early and the
            # next `read()` could land before the requested frame.
            probe_limit = self._frames_decoded + MAX_SEEK_PROBE_FRAMES
            while self.read(decode=False) is not False:
                if self._last_timestamp is not None or self._frames_decoded >= probe_limit:
                    break
        while self.position < target:
            if self.read(decode=False) is False:
                break
        self._frames_decoded = self.frame_number

    def reset(self):
        """Close and re-open the VideoStream (should be equivalent to calling `seek(0)`)."""
        self._check_open()
        self._container.close()
        self._frame = None
        self._decoder = None
        self._timecode = None
        self._last_timestamp = None
        self._frames_decoded = 0
        self._warned_non_monotonic = False
        try:
            self._container = self._open_container(rewind=True)
            if self._threading_mode is not None:
                self._video_stream.thread_type = self._threading_mode
                self._reopened = False
        except Exception as ex:
            raise VideoOpenFailure() from ex

    def read(self, decode: bool = True) -> np.ndarray | bool:
        self._check_open()
        consecutive_failures = 0
        while True:
            # Reuse the same decode generator for the lifetime of the container. Creating a new
            # generator on each call would flush the codec's internal buffer at EOF and drop the
            # last buffered frame.
            if self._decoder is None:
                self._decoder = self._container.decode(video=0)
            try:
                last_frame = self._frame
                assert self._decoder is not None
                self._frame = next(self._decoder)
            # EOFError subclasses FFmpegError, so this clause must come first.
            except av.error.EOFError:  # type: ignore[attr-defined]
                self._frame = last_frame
                if self._handle_eof():
                    return self.read(decode)
                return False
            except StopIteration:
                return False
            except av.error.FFmpegError as ex:  # type: ignore[attr-defined]
                # `next()` raised before assignment, so `self._frame` and `self._timecode` still
                # reflect the last valid frame.
                self._decode_failures += 1
                consecutive_failures += 1
                # A generator cannot be resumed once an exception propagates out of it; recreating
                # it on the next iteration continues demuxing after the corrupt packet.
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
        """Open `_io` as a PyAV container with `_CONTAINER_OPTIONS`.

        All container opens (initial open, `reset()`, and `_handle_eof()`) must go through this
        helper so container flags like `-genpts` stay applied after re-opening.

        Arguments:
            rewind: Seek `_io` back to byte 0 before opening (used when re-opening a stream).
        """
        if rewind and self._io.seekable():
            self._io.seek(0)
        return av.open(self._io, container_options=_CONTAINER_OPTIONS)  # type: ignore[attr-defined]

    def _update_timecode(self):
        """Update `_timecode` with the presentation time of `_frame` relative to the first frame.

        Each frame is placed at its PTS, falling back to its DTS when the PTS is missing (the
        same rule as OpenCV's FFmpeg backend, and what FFmpeg's `best_effort_timestamp` reduces
        to once `genpts` is disabled). A frame with neither is placed one nominal frame period
        after the previous frame (see `_estimated_timecode()`).

        `_offset` is decided once, from the first frame that carries a timestamp. When that is
        frame 1 and it has a PTS, the stream `start_time` is used so files with edit lists start
        at time 0 like the other backends. Otherwise the offset anchors frame 1 at time 0 assuming
        the frames before it were spaced at the nominal frame rate. This covers DTS-only streams
        (e.g. AVI), whose first DTS is already past the stream start by the decoder's B-frame
        reordering delay, and streams whose first frames carry no timestamps at all.
        """
        frame = self._frame
        assert frame is not None
        timestamp = frame.pts if frame.pts is not None else frame.dts
        if timestamp is None or not frame.time_base:
            self._timecode = self._estimated_timecode()
            return
        time_base = self._frame_time_base
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
        previous = self._last_timestamp
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
        self._timecode = self._last_timestamp = timecode

    def _estimated_timecode(self) -> Timecode:
        """The position we think the next frame should be at. Use only if we get a frame without a
        timestamp. Calculated as one (nominal) frame period from the previous frame's timestamp, or
        estimated as the frame count times the (nominal) frame rate if no frame was consumed yet."""
        previous = self._timecode
        previous = self._timecode
        if previous is None:
            return Timecode(pts=max(self._frames_decoded - 1, 0), time_base=1 / self.frame_rate)
        return Timecode(
            pts=previous.pts + self._frame_period(previous.time_base), time_base=previous.time_base
        )

    def _frame_period(self, time_base: Fraction) -> int:
        """Duration of one frame at the nominal frame rate in `time_base` ticks (at least 1)."""
        return max(round(1 / (self.frame_rate * time_base)), 1)

    def _get_duration(self) -> int:
        """Get video duration as number of frames based on the video and set framerate.

        See https://pyav.org/docs/develop/api/time.html for details on how ffmpeg/PyAV
        handle time calculations internally and which time base to use.
        """
        assert self.frame_rate is not None, "Frame rate must be set before calling _get_duration!"
        # See if we can obtain the number of frames directly from the stream itself.
        # TODO(https://scenedetect.com/issues/590): Some AVI files remuxed by ffmpeg set the stream
        # rate to a high tick rate (e.g. 600/1), causing `stream.frames` to report tick count
        # rather than actual frame count (e.g. 12012 instead of 480). OpenCV reports the same value
        # via CAP_PROP_FRAME_COUNT, but `duration_sec * frame_rate` would be more accurate when
        # `stream.frames` disagrees with the stream duration and codec frame rate.
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
        thread_type = getattr(
            self._video_stream.thread_type, "name", self._video_stream.thread_type
        )
        if not self.is_seekable or self._offset is None or thread_type not in ("AUTO", "FRAME"):
            return False
        last_pos = self.position if self._timecode is not None else None
        orig_pos = self._io.tell()
        try:
            container = self._open_container(rewind=True)
        except:
            self._io.seek(orig_pos)
            raise
        self._container.close()
        self._container = container
        self._decoder = None
        if last_pos is not None:
            try:
                # `seek(target)` positions the stream one frame before `target` so the next `read()`
                # returns `target`. Pass `last_pos + 1` so the reopened stream lands on `last_pos`
                # and the caller's subsequent `read()` advances to the next frame.
                self.seek(last_pos + 1)
            except SeekError:
                return False
        return True
