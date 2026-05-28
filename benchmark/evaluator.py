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
"""Scoring for shot-boundary-detection benchmarks.

Implements the TRECVID-SBD evaluation convention. Each predicted boundary is one integer frame
number. Hard cuts are matched against ground-truth frames, with a configurable frame-tolerance.
Matches are scored via greedy 1-to-1 nearest-neighbor assignment. Fades and other gradual
transitions are matched by point-in-interval membership, where the prediction inside an interval
is considered a match. Other predictions in the same interval are considered false positives.

References:
- Smeaton, Over & Doherty (2010), "Video shot boundary detection: Seven years of TRECVid activity",
  *Computer Vision and Image Understanding*.
  https://ora.ox.ac.uk/objects/uuid:868aebdf-298a-4567-b47f-c8f9e3a6ac7a
- Hassanien et al. (2017), "Large-scale, Fast and Accurate Shot Boundary Detection through
  Spatio-temporal Convolutional Neural Networks", arXiv:1705.03281.
  https://arxiv.org/abs/1705.03281
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import TypeAlias

# 1-based frame number, matching the convention used by the BBC/AutoShot text annotations and by
# PySceneDetect's :class:`FrameTimecode`. Used for cut positions and for tolerance windows.
#
# Ironically, all the work we did in v0.7 to support VFR is meaningless for most existing benchmarks
# since they are all CFR. In the future we should consider extending the API to support temporal
# units of time or PTS, and also see if other datasets might take this into account.
Frames: TypeAlias = int


@dataclass(frozen=True)
class EventInterval:
    """Inclusive ``[start, end]`` frame range for a gradual transition (dissolve/fade)."""

    start: Frames
    end: Frames

    def contains(self, frame: Frames) -> bool:
        return self.start <= frame <= self.end


@dataclass
class GroundTruth:
    """Ground truth for one video, consisting of hard cut frames and fade intervals."""

    hard_cuts: list[Frames]
    fades: list[EventInterval] = field(default_factory=list)
    category: str | None = None


@dataclass
class Prediction:
    """One detector run on one video, ready for scoring against typed ground truth."""

    predicted_cuts: list[Frames]
    """Flat list of predicted hard cut frame numbers, 1-based."""
    ground_truth: GroundTruth
    """Ground truth for the video being scored."""
    elapsed: float
    """How long it took to run the prediction, in seconds. Used for performance not accuracy."""


@dataclass
class EventMetrics:
    """Per-event-type scoring counts used to calculate precision, recall, and F1 score.

    Each instance should be used to score *one* event type (either hard cuts *or* fade transitions)
    against ground truth.
    """

    # Detector fired on a real event in the ground truth.
    matched: int = 0
    # Detector fired but there was no real event at that frame.
    false_positives: int = 0
    # Real event in the ground truth that the detector failed to fire on.
    missed: int = 0

    @property
    def precision(self) -> float:
        denom = self.matched + self.false_positives
        return self.matched / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.matched + self.missed
        return self.matched / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def __add__(self, other: EventMetrics) -> EventMetrics:
        return EventMetrics(
            matched=self.matched + other.matched,
            false_positives=self.false_positives + other.false_positives,
            missed=self.missed + other.missed,
        )

    def to_dict(self) -> dict:
        return {
            "matched": self.matched,
            "false_positives": self.false_positives,
            "missed": self.missed,
            "precision": round(self.precision * 100, 4),
            "recall": round(self.recall * 100, 4),
            "f1": round(self.f1 * 100, 4),
        }


@dataclass
class VideoMetrics:
    """Per-video result at one tolerance. The video's path lives in the enclosing
    :class:`BenchmarkResult.per_video` dict key, not on this object."""

    elapsed: float
    category: str | None
    hard_cuts: EventMetrics
    fades: EventMetrics
    # (sum of |prediction - ground_truth|, match count) over hard-cut matches.
    # Stored as raw sums so aggregation across videos is `sum / total_matched`,
    # not a mean-of-means.
    hard_offset: tuple[float, int]

    @property
    def mean_abs_offset(self) -> float:
        s, n = self.hard_offset
        return s / n if n else math.nan

    def to_dict(self) -> dict:
        return {
            "elapsed": self.elapsed,
            "category": self.category,
            "hard_cuts": self.hard_cuts.to_dict(),
            "fades": self.fades.to_dict(),
            "mean_abs_offset_hard_cuts": self.mean_abs_offset,
        }


@dataclass
class BenchmarkResult:
    """Aggregate result of running one detector configuration on a dataset at one tolerance.

    ``per_video`` is keyed by source video path so per-video lookups are explicit; aggregate
    properties sum counts across all videos (same convention used by TRECVID).
    """

    per_video: dict[Path, VideoMetrics]
    tolerance: Frames

    @property
    def hard_cuts(self) -> EventMetrics:
        total = EventMetrics()
        for v in self.per_video.values():
            total = total + v.hard_cuts
        return total

    @property
    def fades(self) -> EventMetrics:
        total = EventMetrics()
        for v in self.per_video.values():
            total = total + v.fades
        return total

    @property
    def mean_abs_offset_hard_cuts(self) -> float:
        num = sum(v.hard_offset[0] for v in self.per_video.values())
        den = sum(v.hard_offset[1] for v in self.per_video.values())
        return num / den if den else math.nan

    @property
    def elapsed_total(self) -> float:
        return sum(v.elapsed for v in self.per_video.values())

    @property
    def elapsed_mean(self) -> float:
        return mean(v.elapsed for v in self.per_video.values()) if self.per_video else 0.0

    def by_category(self) -> dict[str, BenchmarkResult]:
        buckets: dict[str, dict[Path, VideoMetrics]] = {}
        for path, v in self.per_video.items():
            buckets.setdefault(v.category or "unknown", {})[path] = v
        return {
            g: BenchmarkResult(per_video=vids, tolerance=self.tolerance)
            for g, vids in buckets.items()
        }

    def to_dict(self, root: Path | None = None) -> dict:
        def _fmt_path(p: Path) -> str:
            if root is not None:
                try:
                    return p.relative_to(root).as_posix()
                except ValueError:
                    pass
            return p.as_posix()

        return {
            "tolerance": self.tolerance,
            "aggregate": {
                "hard_cuts": self.hard_cuts.to_dict(),
                "mean_abs_offset_hard_cuts": self.mean_abs_offset_hard_cuts,
                "fades": self.fades.to_dict(),
                "elapsed_total": self.elapsed_total,
                "elapsed_mean": self.elapsed_mean,
                "video_count": len(self.per_video),
            },
            "per_video": {_fmt_path(path): v.to_dict() for path, v in self.per_video.items()},
        }


def _score_hard_cuts(
    predicted_cuts: Iterable[Frames],
    ground_truth_cuts: Iterable[Frames],
    tolerance: Frames,
) -> tuple[EventMetrics, list[Frames]]:
    """Greedy 1-to-1 nearest-neighbor matching within ``tolerance`` frames.

    Builds the set of all (prediction, ground-truth) candidate pairs whose absolute frame distance
    is within tolerance, sorts by distance, and walks the sorted list claiming the first unused
    pair each time. Ties on distance are broken by stable iteration order, which is deterministic
    but otherwise unspecified - fine since we report aggregate metrics, not per-event assignments.

    Returns the event metrics and the per-match absolute offsets (for later averaging).
    """
    predicted_cuts = list(predicted_cuts)
    ground_truth_cuts = list(ground_truth_cuts)
    candidates: list[tuple[int, int, int]] = []
    for i, p in enumerate(predicted_cuts):
        for j, g in enumerate(ground_truth_cuts):
            d = abs(p - g)
            if d <= tolerance:
                candidates.append((d, i, j))
    candidates.sort()
    prediction_used = [False] * len(predicted_cuts)
    ground_truth_used = [False] * len(ground_truth_cuts)
    offsets: list[int] = []
    for d, i, j in candidates:
        if not prediction_used[i] and not ground_truth_used[j]:
            prediction_used[i] = True
            ground_truth_used[j] = True
            offsets.append(d)
    matched = len(offsets)
    return (
        EventMetrics(
            matched=matched,
            false_positives=len(predicted_cuts) - matched,
            missed=len(ground_truth_cuts) - matched,
        ),
        offsets,
    )


def _score_fade_transitions(
    predicted_cuts: Iterable[Frames],
    intervals: Iterable[EventInterval],
) -> tuple[EventMetrics, set[int]]:
    """Point-in-interval matching for gradual fade transitions.

    Each prediction that falls inside any ground-truth interval is consumed by that interval
    (first-match wins). The first prediction to land in an interval is the match; any further
    predictions in the same interval are false positives. Predictions outside every interval are
    not touched here - they go back to the hard-cut scorer.

    Returns the fade transition metrics and the set of *positional indices* (into
    ``predicted_cuts``, not frame values) that were consumed by a fade interval, so the caller
    can skip them when running hard matching.
    """
    predicted_cuts = list(predicted_cuts)
    intervals = list(intervals)
    consumed: set[int] = set()
    intervals_matched: set[EventInterval] = set()
    matched = 0
    false_positives = 0
    for k, p in enumerate(predicted_cuts):
        for interval in intervals:
            if interval.contains(p):
                consumed.add(k)
                if interval in intervals_matched:
                    false_positives += 1
                else:
                    intervals_matched.add(interval)
                    matched += 1
                break
    missed = len(intervals) - matched
    return (
        EventMetrics(matched=matched, false_positives=false_positives, missed=missed),
        consumed,
    )


def score_video(
    predicted_cuts: Iterable[Frames],
    ground_truth: GroundTruth,
    tolerance: Frames,
    elapsed: float,
) -> VideoMetrics:
    """Score one video against typed ground truth at one tolerance.

    Fade transition matching runs first; predictions that land inside any fade interval are
    consumed there and excluded from hard-cut matching. The remaining predictions are matched
    against ground-truth hard cuts at ``tolerance`` frames.
    """
    predicted_cuts = list(predicted_cuts)

    fade_metrics, consumed = _score_fade_transitions(predicted_cuts, ground_truth.fades)
    remaining_cuts = [p for k, p in enumerate(predicted_cuts) if k not in consumed]
    hard_metrics, offsets = _score_hard_cuts(remaining_cuts, ground_truth.hard_cuts, tolerance)

    return VideoMetrics(
        elapsed=elapsed,
        category=ground_truth.category,
        hard_cuts=hard_metrics,
        fades=fade_metrics,
        hard_offset=(float(sum(offsets)), len(offsets)),
    )


def evaluate(predictions: dict[Path, Prediction], tolerance: Frames) -> BenchmarkResult:
    """Score predictions at a single tolerance and return aggregate + per-video results."""
    assert predictions, "predictions must not be empty"
    videos = {
        path: score_video(
            predicted_cuts=p.predicted_cuts,
            ground_truth=p.ground_truth,
            tolerance=tolerance,
            elapsed=p.elapsed,
        )
        for path, p in predictions.items()
    }
    return BenchmarkResult(per_video=videos, tolerance=tolerance)
