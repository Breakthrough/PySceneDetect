#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""``scenedetect.backends.concat`` Module

:class:`VideoStreamConcat` presents multiple videos as a single, contiguous
:class:`VideoStream <scenedetect.video_stream.VideoStream>` with a global PTS-based
timeline. Frames are decoded through any available backend, so the concatenation logic is
backend-agnostic. The easiest way to construct one is by passing a list of paths to
:func:`scenedetect.open_video`:

.. code:: python

    from scenedetect import open_video
    video = open_video(["part1.mp4", "part2.mp4"])

The resulting stream can be used anywhere a single-video stream can, e.g. with a
:class:`SceneManager <scenedetect.scene_manager.SceneManager>`. All videos must have the same
resolution. Framerates may differ. Frame ordinals follow the decoded sequence across input
boundaries; `position` contains each frame's timestamp on the global timeline.

:meth:`VideoStreamConcat.map_span` maps a span of the global timeline back to per-source local
times (e.g. for use as ffmpeg `-ss`/`-t` arguments).
"""

import bisect
import logging
import typing as ty
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np

from scenedetect.common import FrameRate, FrameTimecode, Timecode, TimecodeLike, parse_frame_or_time
from scenedetect.platform import StrPath
from scenedetect.video_stream import SeekError, VideoOpenFailure, VideoStream, FrameNumbering

logger = logging.getLogger("pyscenedetect")

_GLOBAL_TIME_BASE = Fraction(1, 1000000)
"""Time base used for the legacy combined-duration value."""

FRAMERATE_DELTA_TOLERANCE: float = 0.1
"""Tolerance in frames/sec above which a framerate mismatch between inputs is warned about."""


@dataclass(frozen=True)
class _SourceMetadata:
    """Declared metadata for one input video, probed via the child backend without decoding."""

    path: Path
    frame_size: tuple[int, int]
    frame_rate: Fraction
    duration: Fraction
    """Declared duration of the video in seconds (exact rational value). May be inaccurate;
    later source offsets may be extended when decoding reaches this source's end."""
    aspect_ratio: float


@dataclass(frozen=True)
class SourceSpan:
    """Portion of a single input video covered by a time span on the global timeline of a
    :class:`VideoStreamConcat`. The interval [local_start, local_end) is relative to that video's
    start. Use local_start as a seek target or ffmpeg `-ss` value; the elapsed time between the
    endpoints gives the `-t` value."""

    source_index: int
    path: Path
    local_start: Timecode
    local_end: Timecode


def _exact_seconds(timecode: FrameTimecode) -> Fraction:
    """Time represented by `timecode` as an exact rational number of seconds."""
    return Fraction(timecode.pts) * timecode.time_base


class VideoStreamConcat(VideoStream):
    """Concatenates multiple videos into a single, contiguous video stream with a
    PTS-based global timeline.

    The concatenation logic is backend-agnostic: frames are read through any PySceneDetect
    `VideoStream` backend, selected by name (default `opencv`). For the most accurate seam
    timing, use `backend="pyav"` if available.

    Raises:
        VideoOpenFailure: Failed to open a video, or video parameters don't match.
    """

    BACKEND_NAME = "concat"

    def __init__(
        self,
        paths: ty.Sequence[StrPath],
        frame_rate: FrameRate | None = None,
        backend: str = "opencv",
        frame_numbering: FrameNumbering = FrameNumbering.RELATIVE,
        **kwargs,
    ):
        """Open a list of videos as one continuous stream.

        Arguments:
            paths: List of paths of the videos to concatenate, in playback order.
            frame_rate: If set, overrides the detected frame rate of every input.
            backend: Name of the backend to decode each input with (see
                :data:`scenedetect.backends.AVAILABLE_BACKENDS`). Falls back to OpenCV if
                unavailable.
            frame_numbering: RELATIVE (default) restarts ordinals at 0 after seeking.
                SOURCE counts frames from the beginning of the concatenated stream.
            kwargs: Optional named arguments to pass to every child backend constructor.

        Raises:
            OSError: A file could not be found or access was denied.
            VideoOpenFailure: A video could not be opened, or resolutions don't match.
        """
        assert paths
        super().__init__(frame_numbering=frame_numbering)
        # Import here to avoid a circular import (scenedetect.backends imports this module).
        from scenedetect.backends import AVAILABLE_BACKENDS

        backend = backend.lower()
        if backend not in AVAILABLE_BACKENDS:
            logger.warning("Backend %s not available, falling back to opencv.", backend)
            backend = "opencv"
        self._backend_type: type = AVAILABLE_BACKENDS[backend]
        self._paths: list[Path] = [Path(path) for path in paths]
        self._frame_rate_override = frame_rate
        self._backend_kwargs = kwargs

        # Probe all inputs up front for validation and metadata, then only keep one source
        # open at a time for decoding. The handle probed for the first source is kept as the
        # initial decode source to avoid re-opening it.
        self._sources: list[_SourceMetadata] = []
        first_cap: VideoStream | None = None
        for index in range(len(self._paths)):
            cap = self._open_source(index)
            duration = cap.duration
            declared_seconds = _exact_seconds(duration) if duration is not None else Fraction(0)
            self._sources.append(
                _SourceMetadata(
                    path=self._paths[index],
                    frame_size=cap.frame_size,
                    frame_rate=cap.frame_rate,
                    duration=declared_seconds,
                    aspect_ratio=cap.aspect_ratio,
                )
            )
            if index == 0:
                first_cap = cap
        self._validate_sources()

        # Global start time of each source in exact rational seconds. Has one extra entry at
        # the end holding the total (declared) duration. Values after the current source are
        # estimates from declared durations, and may be extended using an estimated end time
        # when each source reaches EOF.
        self._offsets: list[Fraction] = [Fraction(0)]
        for source in self._sources:
            self._offsets.append(self._offsets[-1] + source.duration)

        self._index: int = 0
        self._decode_failures_prior: int = 0
        self._pending_frame: np.ndarray | None = None
        assert first_cap is not None
        self._cap: VideoStream = first_cap

    #
    # Concatenation Logic
    #

    def _validate_sources(self):
        first = self._sources[0]
        for source in self._sources[1:]:
            logger.debug(
                "Appending video %s (%d x %d at %2.3f FPS).",
                source.path.name,
                source.frame_size[0],
                source.frame_size[1],
                float(source.frame_rate),
            )
            if source.frame_size != first.frame_size:
                raise VideoOpenFailure(
                    f"Video resolutions must match to be concatenated: {source.path.name} is "
                    f"{source.frame_size[0]} x {source.frame_size[1]}, expected "
                    f"{first.frame_size[0]} x {first.frame_size[1]}."
                )
            if abs(float(source.frame_rate) - float(first.frame_rate)) > FRAMERATE_DELTA_TOLERANCE:
                logger.warning(
                    "Framerate of %s does not match the first input. The reported frame rate "
                    "is taken from the first input; timestamps use each input backend's timing.",
                    source.path.name,
                )

    def _open_source(self, index: int) -> VideoStream:
        return self._backend_type(
            str(self._paths[index]), self._frame_rate_override, **self._backend_kwargs
        )

    def _child_position_seconds(self) -> Fraction:
        """Position of the current source as exact rational seconds (local timeline)."""
        position = self._cap.position
        assert position is not None
        timecode = position.timecode
        return timecode.seconds

    def _finish_current_source(self):
        """Extend later source offsets when the estimated end exceeds the declared duration.

        Estimate the end from the last observed timestamp plus one frame at the child's rate.
        """
        self._decode_failures_prior += self._cap.decode_failures
        if self._cap.position is None:
            return
        actual_end = (
            self._offsets[self._index]
            + self._child_position_seconds()
            + Fraction(1) / self._cap.frame_rate
        )
        declared_end = self._offsets[self._index + 1]
        if actual_end > declared_end:
            delta = actual_end - declared_end
            for i in range(self._index + 1, len(self._offsets)):
                self._offsets[i] += delta

    def _current_timecode(self) -> Timecode:
        """Current position on the global timeline as a Timecode."""
        seconds = self._offsets[self._index] + self._child_position_seconds()
        return Timecode(pts=seconds.numerator, time_base=Fraction(1, seconds.denominator))


    def _read_next_frame(self, decode: bool = True) -> np.ndarray | bool:
        """Read/decode the next frame. Returns False when all inputs have been processed.

        Consume a pending seek image before reading from a child. Does not record a global
        frame position.
        """
        if self._pending_frame is not None:
            frame = self._pending_frame
            self._pending_frame = None
            return frame if decode else True
        while True:
            result = self._cap.read(decode=decode)
            if result is not False:
                return result
            if (self._index + 1) >= len(self._paths):
                logger.debug("No more input to process.")
                return False
            self._finish_current_source()
            self._index += 1
            logger.debug("Processing complete, opening next video: %s", self._paths[self._index])
            self._cap = self._open_source(self._index)

    def read(self, decode: bool = True) -> np.ndarray | bool:
        result = self._read_next_frame(decode=decode)
        if result is False:
            return False
        self._record_frame(self._current_timecode())
        return result

    def seek(self, target: TimecodeLike):
        """Seek to `target` on the global timeline. Supports seeking across sources in
        either direction.

        Integer targets are zero-based source ordinals reached by sequential reading. For
        example, `seek(4)` followed by `read()` reads the fifth frame, with ordinal 0 in
        RELATIVE mode or 4 in SOURCE mode.

        SOURCE time seeks count preceding frames sequentially. RELATIVE time seeks use native
        child seeking and the currently known source offsets, which may depend on declared
        durations. If the child raises SeekError and another source exists, replay the selected
        child and continue across source boundaries. Preroll retains the first image encountered
        at or after the requested time for the next read. Timestamp and seek accuracy depend on
        the child backend.
        A successful seek restarts RELATIVE numbering at 0 without resetting frame timestamps.

        Arguments:
            target: A zero-based source ordinal (int or digit-only string), or a time
                (float seconds, timecode string, or Timecode).

        Raises:
            SeekError: Seeking is unsupported or the requested position cannot be reached.
            OSError: A child backend fails to open, seek, or read an input.
            TypeError: The target type is unsupported.
            ValueError: The target is negative, non-finite, or malformed, or has an invalid
                time base.
        """
        if not self.is_seekable:
            raise SeekError("Seeking is not supported for this video stream.")

        parsed = parse_frame_or_time(target)
        if parsed < 0:
            raise ValueError("Target seek position cannot be negative!")

        if isinstance(parsed, Fraction):
            if self._frame_numbering is FrameNumbering.SOURCE:
                position = self.position
                if (
                    position is not None
                    and position.timecode.seconds >= parsed
                ):
                    self.reset()
            else:
                self._pending_frame = None
                target_seconds = parsed
                # Find the last source which starts at or before the target.
                index = bisect.bisect_right(self._offsets, target_seconds) - 1
                index = max(0, min(index, len(self._paths) - 1))
                if index != self._index:
                    self._decode_failures_prior += self._cap.decode_failures
                    self._index = index
                    self._cap = self._open_source(index)
                local_seconds = target_seconds - self._offsets[index]
                try:
                    self._cap.seek(
                        Timecode(
                            pts=local_seconds.numerator,
                            time_base=Fraction(1, local_seconds.denominator),
                        )
                    )
                except SeekError:
                    if self._index + 1 >= len(self._paths):
                        raise
                    self._cap.reset()
                else:
                    self._position = None
                    return

            while True:
                result = self._read_next_frame()
                if result is False:
                    raise SeekError("Could not reach the requested time.")

                timecode = self._current_timecode()
                if timecode.seconds >= parsed:
                    assert isinstance(result, np.ndarray)
                    self._pending_frame = result
                    if self.frame_numbering is FrameNumbering.RELATIVE:
                        self._position = None
                    return
                if self.frame_numbering is FrameNumbering.SOURCE:
                    self._record_frame(timecode)
        else:
            if (
                self._frame_numbering is FrameNumbering.RELATIVE
                or parsed <= self.frame_number
            ):
                self.reset()

            for _ in range(self.frame_number+1, parsed):
                if self._read_next_frame(decode=False) is False:
                    raise SeekError("Could not reach the requested frame.")
                if self.frame_numbering is FrameNumbering.SOURCE:
                    self._record_frame(self._current_timecode())
            return

    def reset(self):
        """Close and re-open the stream (equivalent to seeking back to the beginning)."""
        self._index = 0
        self._position = None
        self._pending_frame = None
        self._decode_failures_prior = 0
        self._cap = self._open_source(0)

    #
    # VideoStream Properties
    #

    @property
    def path(self) -> str:
        """Path of the first input video."""
        return str(self._paths[0])

    @property
    def name(self) -> str:
        """Name of the first input video, without extension."""
        return self._paths[0].stem

    @property
    def is_seekable(self) -> bool:
        return self._cap.is_seekable

    @property
    def frame_rate(self) -> Fraction:
        """Average framerate of the first input video. Individual sources may vary; use
        `position` for accurate timing."""
        return self._sources[0].frame_rate

    @property
    def duration(self) -> FrameTimecode:
        """Total duration of all input videos combined. May be inaccurate."""
        return FrameTimecode(
            timecode=Timecode(
                pts=round(self._offsets[-1] / _GLOBAL_TIME_BASE), time_base=_GLOBAL_TIME_BASE
            ),
            fps=self.frame_rate,
        )

    @property
    def frame_size(self) -> tuple[int, int]:
        """Video resolution (width x height) in pixels."""
        return self._sources[0].frame_size

    @property
    def aspect_ratio(self) -> float:
        return self._sources[0].aspect_ratio

    @property
    def decode_failures(self) -> int:
        """Number of frames which failed to decode across all sources."""
        return self._decode_failures_prior + self._cap.decode_failures

    #
    # Concatenation-Specific Properties/Methods
    #

    @property
    def paths(self) -> list[Path]:
        """All paths this object was created with."""
        return self._paths

    @property
    def child_backend(self) -> str:
        """Name of the backend used to decode each input video."""
        return self._cap.BACKEND_NAME

    def map_span(self, start: Timecode, end: Timecode) -> list[SourceSpan]:
        """Map a time span on the global timeline to the input video(s) covering it.
        A span which straddles one or more file boundaries yields multiple entries.

        Treat [start, end) as a half-open interval and clip it to the currently known source
        boundaries. Empty intervals return no spans. Raises ValueError if end precedes start.
        """
        start_seconds = start.seconds
        end_seconds = end.seconds
        if end_seconds < start_seconds:
            raise ValueError("Span end must not precede its start.")
        if end_seconds == start_seconds:
            return []
        spans: list[SourceSpan] = []
        for index, source in enumerate(self._sources):
            source_start, source_end = self._offsets[index], self._offsets[index + 1]
            if end_seconds <= source_start:
                break
            if start_seconds >= source_end:
                continue
            local_start = max(Fraction(0), start_seconds - source_start)
            local_end = min(source_end - source_start, end_seconds - source_start)
            if local_end <= local_start:
                continue
            spans.append(
                SourceSpan(
                    source_index=index,
                    path=source.path,
                    local_start=Timecode(
                        pts=local_start.numerator,
                        time_base=Fraction(1, local_start.denominator)
                    ),
                    local_end=Timecode(
                        pts=local_end.numerator,
                        time_base=Fraction(1, local_end.denominator)
                    ),
                )
            )
        return spans
