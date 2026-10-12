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
:class:`VideoStream <scenedetect.video_stream.VideoStream>` with a monotonic PTS-based
timeline. Frames are decoded through any available backend, so the concatenation logic is
backend-agnostic. The easiest way to construct one is by passing a list of paths to
:func:`scenedetect.open_video`:

.. code:: python

    from scenedetect import open_video
    video = open_video(["part1.mp4", "part2.mp4"])

The resulting stream can be used anywhere a single-video stream can, e.g. with a
:class:`SceneManager <scenedetect.scene_manager.SceneManager>`. All videos must have the same
resolution. Framerates may differ, in which case reported frame numbers may be inaccurate -
use `position` for accurate PTS-based timing.

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

from scenedetect.common import FrameRate, FrameTimecode, Timecode, TimecodeLike
from scenedetect.platform import StrPath
from scenedetect.video_stream import VideoOpenFailure, VideoStream

logger = logging.getLogger("pyscenedetect")

_GLOBAL_TIME_BASE = Fraction(1, 1000000)
"""Time base used for the global (concatenated) timeline."""

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
    the global timeline is corrected once the actual end of the source is reached."""
    frames: int
    """Declared number of frames in the video. May be inaccurate."""
    aspect_ratio: float


@dataclass(frozen=True)
class SourceSpan:
    """Portion of a single input video covered by a time span on the global timeline of a
    :class:`VideoStreamConcat`. Local times are relative to the start of that video, directly
    usable as seek targets or ffmpeg `-ss`/`-t` values."""

    source_index: int
    path: Path
    local_start: FrameTimecode
    local_end: FrameTimecode


def _exact_seconds(timecode: FrameTimecode) -> Fraction:
    """Time represented by `timecode` as an exact rational number of seconds."""
    return Fraction(timecode.pts) * timecode.time_base


class VideoStreamConcat(VideoStream):
    """Concatenates multiple videos into a single, contiguous video stream with a
    monotonic PTS-based global timeline.

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
        **kwargs,
    ):
        """Open a list of videos as one continuous stream.

        Arguments:
            paths: List of paths of the videos to concatenate, in playback order.
            frame_rate: If set, overrides the detected frame rate of every input.
            backend: Name of the backend to decode each input with (see
                :data:`scenedetect.backends.AVAILABLE_BACKENDS`). Falls back to OpenCV if
                unavailable.
            kwargs: Optional named arguments to pass to every child backend constructor.

        Raises:
            OSError: A file could not be found or access was denied.
            VideoOpenFailure: A video could not be opened, or resolutions don't match.
        """
        assert paths
        super().__init__()
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
                    frames=duration.frame_num if duration is not None else 0,
                    aspect_ratio=cap.aspect_ratio,
                )
            )
            if index == 0:
                first_cap = cap
        self._validate_sources()

        # Global start time of each source in exact rational seconds. Has one extra entry at
        # the end holding the total (declared) duration. Values after the current source are
        # estimates from declared durations, and are corrected once the actual end of each
        # source is reached during decode.
        self._offsets: list[Fraction] = [Fraction(0)]
        for source in self._sources:
            self._offsets.append(self._offsets[-1] + source.duration)

        self._index: int = 0
        self._frames_prior: int = 0
        self._decode_failures_prior: int = 0
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
                    "Framerate of %s does not match the first input. Timing is based on "
                    "presentation timestamps, but reported frame numbers may be inaccurate.",
                    source.path.name,
                )

    def _open_source(self, index: int) -> VideoStream:
        return self._backend_type(
            str(self._paths[index]), self._frame_rate_override, **self._backend_kwargs
        )

    def _child_position_seconds(self) -> Fraction:
        """Position of the current source as exact rational seconds (local timeline)."""
        return _exact_seconds(self._cap.position)

    def _finish_current_source(self):
        """Correct the declared offset of the next source now that the actual end of the
        current source is known, guaranteeing strictly monotonic PTS across the seam even
        when the declared duration is inaccurate."""
        self._decode_failures_prior += self._cap.decode_failures
        self._frames_prior += self._cap.frame_number
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

    def read(self, decode: bool = True) -> np.ndarray | bool:
        """Read/decode the next frame. Returns False when all inputs have been processed."""
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

    def seek(self, target: TimecodeLike):
        """Seek to `target` on the global timeline. Supports seeking across sources in
        either direction."""
        if not isinstance(target, FrameTimecode):
            target = FrameTimecode(target, self.frame_rate)
        if target < 0:
            raise ValueError("Target seek position cannot be negative!")
        target_seconds = _exact_seconds(target)
        # Find the last source which starts at or before the target.
        index = bisect.bisect_right(self._offsets, target_seconds) - 1
        index = max(0, min(index, len(self._paths) - 1))
        if index != self._index:
            self._decode_failures_prior += self._cap.decode_failures
            self._frames_prior = sum(source.frames for source in self._sources[:index])
            self._index = index
            self._cap = self._open_source(index)
        local_seconds = target_seconds - self._offsets[index]
        self._cap.seek(float(local_seconds))

    def reset(self):
        """Close and re-open the stream (equivalent to seeking back to the beginning)."""
        self._index = 0
        self._frames_prior = 0
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
        if self._frame_rate_override is not None:
            return Fraction(self._frame_rate_override)
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
    def position(self) -> FrameTimecode:
        """Presentation time of the last-read frame on the global timeline (the first frame
        of the first video has a presentation time of 0)."""
        global_seconds = self._offsets[self._index] + self._child_position_seconds()
        return FrameTimecode(
            timecode=Timecode(
                pts=round(global_seconds / _GLOBAL_TIME_BASE), time_base=_GLOBAL_TIME_BASE
            ),
            fps=self.frame_rate,
        )

    @property
    def position_ms(self) -> float:
        """Presentation time of the last-read frame in milliseconds on the global timeline."""
        return float((self._offsets[self._index] + self._child_position_seconds()) * 1000)

    @property
    def frame_number(self) -> int:
        """Number of frames read so far across all sources."""
        return self._frames_prior + self._cap.frame_number

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

    def map_span(self, start: FrameTimecode, end: FrameTimecode) -> list[SourceSpan]:
        """Map a time span on the global timeline to the input video(s) covering it.
        A span which straddles one or more file boundaries yields multiple entries."""
        start_seconds = _exact_seconds(start)
        end_seconds = _exact_seconds(end)
        spans: list[SourceSpan] = []
        for index, source in enumerate(self._sources):
            source_start, source_end = self._offsets[index], self._offsets[index + 1]
            if end_seconds <= source_start:
                break
            if start_seconds >= source_end:
                continue
            local_start = max(Fraction(0), start_seconds - source_start)
            local_end = min(source_end - source_start, end_seconds - source_start)
            spans.append(
                SourceSpan(
                    source_index=index,
                    path=source.path,
                    local_start=FrameTimecode(
                        timecode=Timecode(
                            pts=round(local_start / _GLOBAL_TIME_BASE),
                            time_base=_GLOBAL_TIME_BASE,
                        ),
                        fps=source.frame_rate,
                    ),
                    local_end=FrameTimecode(
                        timecode=Timecode(
                            pts=round(local_end / _GLOBAL_TIME_BASE),
                            time_base=_GLOBAL_TIME_BASE,
                        ),
                        fps=source.frame_rate,
                    ),
                )
            )
        return spans
