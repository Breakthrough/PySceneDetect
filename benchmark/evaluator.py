"""Scoring for shot-boundary-detection benchmarks.

Implements the TRECVID-SBD evaluation convention. Each predicted boundary is one integer frame
number. Hard cuts are matched against ground-truth frames with a configurable frame-tolerance window
via greedy 1-to-1 nearest-neighbor assignment. Fades and other gradual transitions are matched by
point-in-interval membership, where the prediction inside an interval matches. Additional
predictions in the same interval are considered false positives.

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
from statistics import mean


@dataclass(frozen=True)
class EventInterval:
    """Interval that captures the start/end of a gradual transition (dissolve/fade) in ground truth.

    ``start`` and ``end`` are inclusive 1-based frame indices, matching the convention used by the
    BBC/AutoShot text annotations and by PySceneDetect's :class:`FrameTimecode`.
    """

    start: int
    end: int

    def contains(self, frame: int) -> bool:
        return self.start <= frame <= self.end


@dataclass
class GroundTruth:
    """Ground truth for one video, consisting of hard cut frames and fade intervals."""

    hard_cuts: list[int]
    fades: list[EventInterval] = field(default_factory=list)
    category: str | None = None


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
    """Per-video result. One entry per (video, detector) pair."""

    video_file: str
    elapsed: float
    category: str | None
    hard_cuts: dict[int, EventMetrics]
    fades: EventMetrics
    # Per-tolerance (sum of |prediction - ground_truth|, match count) over
    # hard-cut matches. Stored as raw sums so aggregation across videos is
    # `sum / total_matched`, not a mean-of-means.
    hard_offset: dict[int, tuple[float, int]]

    def mean_abs_offset(self, tolerance: int) -> float:
        s, n = self.hard_offset[tolerance]
        return s / n if n else math.nan

    def to_dict(self) -> dict:
        return {
            "video_file": self.video_file,
            "elapsed": self.elapsed,
            "category": self.category,
            "hard_cuts": {str(t): m.to_dict() for t, m in self.hard_cuts.items()},
            "fades": self.fades.to_dict(),
            "mean_abs_offset_hard_cuts": {str(t): self.mean_abs_offset(t) for t in self.hard_cuts},
        }


@dataclass
class BenchmarkResult:
    """Aggregate result of running one detector configuration on a dataset.

    Holds per-video metrics and exposes aggregate properties computed by summing counts across
    videos (same convention used by TRECVID).
    """

    per_video: list[VideoMetrics]
    tolerances: tuple[int, ...]

    @property
    def hard_cuts(self) -> dict[int, EventMetrics]:
        out = {t: EventMetrics() for t in self.tolerances}
        for v in self.per_video:
            for t in self.tolerances:
                out[t] = out[t] + v.hard_cuts[t]
        return out

    @property
    def fades(self) -> EventMetrics:
        total = EventMetrics()
        for v in self.per_video:
            total = total + v.fades
        return total

    @property
    def mean_abs_offset_hard_cuts(self) -> dict[int, float]:
        out: dict[int, float] = {}
        for tolerance in self.tolerances:
            num = sum(v.hard_offset[tolerance][0] for v in self.per_video)
            den = sum(v.hard_offset[tolerance][1] for v in self.per_video)
            out[tolerance] = num / den if den else math.nan
        return out

    @property
    def elapsed_total(self) -> float:
        return sum(v.elapsed for v in self.per_video)

    @property
    def elapsed_mean(self) -> float:
        return mean(v.elapsed for v in self.per_video) if self.per_video else 0.0

    def by_category(self) -> dict[str, BenchmarkResult]:
        buckets: dict[str, list[VideoMetrics]] = {}
        for v in self.per_video:
            buckets.setdefault(v.category or "unknown", []).append(v)
        return {
            g: BenchmarkResult(per_video=vids, tolerances=self.tolerances)
            for g, vids in buckets.items()
        }

    def to_dict(self) -> dict:
        return {
            "tolerances": list(self.tolerances),
            "aggregate": {
                "hard_cuts": {str(t): m.to_dict() for t, m in self.hard_cuts.items()},
                "mean_abs_offset_hard_cuts": {
                    str(t): v for t, v in self.mean_abs_offset_hard_cuts.items()
                },
                "fades": self.fades.to_dict(),
                "elapsed_total": self.elapsed_total,
                "elapsed_mean": self.elapsed_mean,
                "video_count": len(self.per_video),
            },
            "per_video": [v.to_dict() for v in self.per_video],
        }


def _score_hard_cuts(
    predicted_cuts: Iterable[int],
    ground_truth_cuts: Iterable[int],
    tolerance: int,
) -> tuple[EventMetrics, list[int]]:
    """Greedy 1-to-1 nearest-neighbor matching within ``tolerance`` frames.

    Builds the set of all (prediction, ground-truth) candidate pairs whose
    absolute frame distance is within tolerance, sorts by distance, and
    walks the sorted list claiming the first unused pair each time. Ties
    on distance are broken by stable iteration order, which is
    deterministic but otherwise unspecified - fine since we report
    aggregate metrics, not per-event assignments.

    Returns the event metrics and the per-match absolute offsets (for later
    averaging).
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
    predicted_cuts: Iterable[int],
    intervals: Iterable[EventInterval],
) -> tuple[EventMetrics, set[int]]:
    """Point-in-interval matching for gradual fade transitions.

    Each prediction that falls inside any ground-truth interval is
    consumed by that interval (first-match wins). The first prediction to
    land in an interval is the match; any further predictions in the same
    interval are false positives. Predictions outside every interval are
    not touched here - they go back to the hard-cut scorer.

    Returns the fade transition metrics and the indices of predictions that were
    consumed (so the caller can skip them when running hard matching).
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
    predicted_cuts: Iterable[int],
    ground_truth: GroundTruth,
    tolerances: Iterable[int],
    video_file: str,
    elapsed: float,
) -> VideoMetrics:
    """Score one video against typed ground truth.

    Fade transition matching runs first; predictions that land inside any fade
    interval are consumed there and excluded from hard-cut matching. The
    remaining predictions are matched against ground-truth hard cuts once
    per tolerance value in ``tolerances``.
    """
    predicted_cuts = list(predicted_cuts)
    tolerances = tuple(tolerances)

    fade_metrics, consumed = _score_fade_transitions(predicted_cuts, ground_truth.fades)
    remaining_cuts = [p for k, p in enumerate(predicted_cuts) if k not in consumed]

    hard_cuts: dict[int, EventMetrics] = {}
    hard_cut_offsets: dict[int, tuple[float, int]] = {}
    for t in tolerances:
        m, offsets = _score_hard_cuts(remaining_cuts, ground_truth.hard_cuts, t)
        hard_cuts[t] = m
        hard_cut_offsets[t] = (float(sum(offsets)), len(offsets))

    return VideoMetrics(
        video_file=video_file,
        elapsed=elapsed,
        category=ground_truth.category,
        hard_cuts=hard_cuts,
        fades=fade_metrics,
        hard_offset=hard_cut_offsets,
    )


def _load_scenes_text(scene_filename: str) -> list[int]:
    """Read a BBC/AutoShot annotation file and return 1-based frame indices.

    Expects tab-separated rows where the second column is the 0-based frame index of the cut.
    """
    with open(scene_filename) as f:
        return [int(x.strip().split("\t")[1]) + 1 for x in f.readlines()]


def _build_video_metrics(pred_scenes: dict, tolerances: tuple[int, ...]) -> list[VideoMetrics]:
    """Score every (scene_file, payload) entry in ``pred_scenes``."""
    if not pred_scenes:
        raise ValueError("pred_scenes must not be empty")
    videos: list[VideoMetrics] = []
    for scene_file, payload in pred_scenes.items():
        gt = payload.get("ground_truth")
        if gt is None:
            gt = GroundTruth(hard_cuts=_load_scenes_text(scene_file))
        videos.append(
            score_video(
                predicted_cuts=payload["pred_scenes"],
                ground_truth=gt,
                tolerances=tolerances,
                video_file=payload["video_file"],
                elapsed=payload["elapsed"],
            )
        )
    return videos


class Evaluator:
    """Wrapper exposing ``evaluate_performance(dict) -> dict`` for the printed result table."""

    def evaluate_performance(self, pred_scenes: dict) -> dict:
        """Score a set of predictions.

        ``pred_scenes`` is a dict mapping ``scene_file`` to a dict containing:

        - ``video_file``: source video filename
        - ``elapsed``: per-video wall-clock seconds
        - ``pred_scenes``: list of predicted cut frames (1-based)
        - ``ground_truth`` (optional): a :class:`GroundTruth`. If absent the scene file is
          parsed as a BBC/AutoShot-style tab-separated text file with hard cuts only.

        Returns the flat dict ``{recall, precision, f1, elapsed}`` at tolerance 0 over
        hard-cut events. Use :func:`evaluate` for per-video, per-tolerance, fade-aware results.
        """
        result = BenchmarkResult(
            per_video=_build_video_metrics(pred_scenes, (0,)),
            tolerances=(0,),
        )
        hard_zero = result.hard_cuts[0]
        return {
            "recall": hard_zero.recall * 100,
            "precision": hard_zero.precision * 100,
            "f1": hard_zero.f1 * 100,
            "elapsed": result.elapsed_mean,
        }


def evaluate(pred_scenes: dict, tolerances: Iterable[int] = (0, 1)) -> BenchmarkResult:
    """Score predictions and return per-video and per-tolerance results."""
    tolerances = tuple(tolerances)
    return BenchmarkResult(
        per_video=_build_video_metrics(pred_scenes, tolerances),
        tolerances=tolerances,
    )
