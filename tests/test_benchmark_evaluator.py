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
"""Unit tests for the benchmark evaluator. Exercises matching, tolerance, and aggregation logic with
synthetic predictions versus ground-truth lists. Covers TRECVID-SBD style scoring as documented in
``benchmark/README.md``.
"""

from __future__ import annotations

import math
from pathlib import Path

from benchmark.evaluator import (
    EventInterval,
    EventMetrics,
    GroundTruth,
    Prediction,
    _score_fade_transitions,
    _score_hard_cuts,
    evaluate,
    score_video,
)

# --------------------------------------------------------------------- #
# Hard-cut matching (the core of every detector's score)
# --------------------------------------------------------------------- #


def test_hard_exact_match_tolerance_zero():
    m, offsets = _score_hard_cuts(
        predicted_cuts=[10, 20, 30], ground_truth_cuts=[10, 20, 30], tolerance=0
    )
    assert (m.matched, m.false_positives, m.missed) == (3, 0, 0)
    assert offsets == [0, 0, 0]
    assert m.precision == 1.0
    assert m.recall == 1.0
    assert m.f1 == 1.0


def test_hard_tolerance_one_admits_one_frame_offset():
    m, offsets = _score_hard_cuts(predicted_cuts=[11, 19], ground_truth_cuts=[10, 20], tolerance=1)
    assert (m.matched, m.false_positives, m.missed) == (2, 0, 0)
    assert sorted(offsets) == [1, 1]


def test_hard_tolerance_one_rejects_two_frame_offset():
    m, _ = _score_hard_cuts(predicted_cuts=[12], ground_truth_cuts=[10], tolerance=1)
    assert (m.matched, m.false_positives, m.missed) == (0, 1, 1)


def test_hard_greedy_picks_closer_match():
    # Two ground-truth cuts at 10 and 14. Single prediction at 13 is closer
    # to 14. The greedy matcher must claim 14 first; 10 then becomes a miss.
    m, offsets = _score_hard_cuts(predicted_cuts=[13], ground_truth_cuts=[10, 14], tolerance=5)
    assert (m.matched, m.false_positives, m.missed) == (1, 0, 1)
    assert offsets == [1]


def test_hard_equidistant_tie_resolves_deterministically():
    # Prediction at 12 is exactly 2 frames from both ground-truth cuts at 10
    # and 14. Tie-break is by stable sort order (i, j) which prefers the
    # lower ground-truth index.
    m, offsets = _score_hard_cuts(predicted_cuts=[12], ground_truth_cuts=[10, 14], tolerance=5)
    assert (m.matched, m.false_positives, m.missed) == (1, 0, 1)
    assert offsets == [2]


def test_hard_one_to_one_no_double_assignment():
    # Two predictions both within tolerance of a single ground-truth cut.
    # Only one can match; the other is a false positive.
    m, _ = _score_hard_cuts(predicted_cuts=[10, 11], ground_truth_cuts=[10], tolerance=1)
    assert (m.matched, m.false_positives, m.missed) == (1, 1, 0)


def test_hard_empty_inputs():
    m, _ = _score_hard_cuts(predicted_cuts=[], ground_truth_cuts=[], tolerance=0)
    assert (m.matched, m.false_positives, m.missed) == (0, 0, 0)
    # Division-by-zero defenses.
    assert m.precision == 0.0
    assert m.recall == 0.0
    assert m.f1 == 0.0


def test_hard_empty_preds_with_nonempty_gt():
    # No predictions: every ground-truth cut is a miss.
    m, offsets = _score_hard_cuts(predicted_cuts=[], ground_truth_cuts=[10, 20], tolerance=1)
    assert (m.matched, m.false_positives, m.missed) == (0, 0, 2)
    assert offsets == []
    assert m.recall == 0.0


def test_hard_empty_gt_with_nonempty_preds():
    # No ground truth: every prediction is a false positive.
    m, offsets = _score_hard_cuts(predicted_cuts=[10], ground_truth_cuts=[], tolerance=1)
    assert (m.matched, m.false_positives, m.missed) == (0, 1, 0)
    assert offsets == []
    assert m.precision == 0.0


# --------------------------------------------------------------------- #
# Fade transition matching (ClipShots-style typed ground truth)
# --------------------------------------------------------------------- #


def test_fade_pred_inside_interval_is_match():
    m, consumed = _score_fade_transitions(predicted_cuts=[15], intervals=[EventInterval(10, 20)])
    assert (m.matched, m.false_positives, m.missed) == (1, 0, 0)
    assert consumed == {0}


def test_fade_pred_outside_interval_not_consumed():
    m, consumed = _score_fade_transitions(predicted_cuts=[25], intervals=[EventInterval(10, 20)])
    assert (m.matched, m.false_positives, m.missed) == (0, 0, 1)
    assert consumed == set()  # passed through to hard scorer


def test_fade_multiple_preds_in_same_interval():
    # First prediction inside the interval is the match; the second is a
    # false positive. Both are consumed (do not leak to hard matching).
    m, consumed = _score_fade_transitions(
        predicted_cuts=[12, 18], intervals=[EventInterval(10, 20)]
    )
    assert (m.matched, m.false_positives, m.missed) == (1, 1, 0)
    assert consumed == {0, 1}


def test_fade_interval_endpoints_inclusive():
    m, _ = _score_fade_transitions(predicted_cuts=[10, 20], intervals=[EventInterval(10, 20)])
    # Both endpoints hit the same interval, so 1 match + 1 false positive.
    assert (m.matched, m.false_positives, m.missed) == (1, 1, 0)


# --------------------------------------------------------------------- #
# score_video: fade transitions take priority over hard cuts
# --------------------------------------------------------------------- #


def test_score_video_fade_consumes_pred_before_hard():
    # Prediction at 15 falls inside the fade interval [10, 20]. Even
    # though the hard ground-truth cut at 16 is within tolerance, the
    # fade scorer claims the prediction first and the hard scorer
    # never sees it.
    ground_truth = GroundTruth(hard_cuts=[16], fades=[EventInterval(10, 20)])
    v = score_video([15], ground_truth, tolerance=1, elapsed=0.0)
    assert v.fades.matched == 1
    assert v.hard_cuts.matched == 0  # hard match was preempted by the fade
    assert v.hard_cuts.missed == 1  # hard ground-truth cut at 16 is now a miss


def test_score_video_pred_outside_fade_falls_to_hard():
    ground_truth = GroundTruth(hard_cuts=[30], fades=[EventInterval(10, 20)])
    v = score_video([30], ground_truth, tolerance=0, elapsed=0.0)
    assert v.fades.matched == 0
    assert v.fades.missed == 1  # fade still missed
    assert v.hard_cuts.matched == 1


# --------------------------------------------------------------------- #
# Mean absolute offset (localization error on hard-cut matches only)
# --------------------------------------------------------------------- #


def test_mean_abs_offset_only_hard_matches_tolerance_zero():
    ground_truth = GroundTruth(
        hard_cuts=[100, 200, 300],
        fades=[EventInterval(50, 60)],
    )
    # Predictions: fade hit at 55 (excluded from offset), hard match at 100
    # (offset 0). 201 and 302 are outside tolerance 0.
    v = score_video([55, 100, 201, 302], ground_truth, 0, 0.0)
    assert v.hard_cuts.matched == 1
    assert v.mean_abs_offset == 0.0


def test_mean_abs_offset_only_hard_matches_tolerance_one():
    ground_truth = GroundTruth(
        hard_cuts=[100, 200, 300],
        fades=[EventInterval(50, 60)],
    )
    # Same setup at tolerance 1: 100 (offset 0) and 201 (offset 1) match;
    # 302 is out of tolerance. Mean offset is (0 + 1) / 2 = 0.5.
    v = score_video([55, 100, 201, 302], ground_truth, 1, 0.0)
    assert v.hard_cuts.matched == 2
    assert v.mean_abs_offset == 0.5


def test_mean_abs_offset_nan_when_no_matches():
    ground_truth = GroundTruth(hard_cuts=[1000])
    v = score_video([5], ground_truth, 0, 0.0)
    assert math.isnan(v.mean_abs_offset)


def test_benchmark_result_mean_abs_offset_nan_when_no_matches_across_videos():
    # Two videos, both producing zero hard-cut matches. The aggregate offset
    # has zero sum and zero count, so nan must propagate at the
    # BenchmarkResult level, not just per-video.
    predictions = {
        Path("a.mp4"): Prediction(
            predicted_cuts=[5],
            ground_truth=GroundTruth(hard_cuts=[1000]),
            elapsed=1.0,
        ),
        Path("b.mp4"): Prediction(
            predicted_cuts=[7],
            ground_truth=GroundTruth(hard_cuts=[2000]),
            elapsed=1.0,
        ),
    }
    result = evaluate(predictions, tolerance=0)
    assert math.isnan(result.mean_abs_offset_hard_cuts)


# --------------------------------------------------------------------- #
# Aggregate result: sum-of-counts across videos
# --------------------------------------------------------------------- #


def test_benchmark_result_aggregate_matches_sum_of_counts():
    predictions = {
        Path("vid_a.mp4"): Prediction(
            predicted_cuts=[10, 20],
            ground_truth=GroundTruth(hard_cuts=[10, 21]),
            elapsed=1.0,
        ),
        Path("vid_b.mp4"): Prediction(
            predicted_cuts=[50, 99],
            ground_truth=GroundTruth(hard_cuts=[50, 100]),
            elapsed=3.0,
        ),
    }
    # Tolerance 0: only 10 (vid_a) and 50 (vid_b) match exactly.
    # Aggregate: 2 matched, 2 false positives, 2 missed.
    result_t0 = evaluate(predictions, tolerance=0)
    assert result_t0.hard_cuts.matched == 2
    assert result_t0.hard_cuts.false_positives == 2
    assert result_t0.hard_cuts.missed == 2
    # Tolerance 1: both predictions in each video match -> 4 matched, 0 fp, 0 missed.
    result_t1 = evaluate(predictions, tolerance=1)
    assert result_t1.hard_cuts.matched == 4
    assert result_t1.hard_cuts.false_positives == 0
    assert result_t1.hard_cuts.missed == 0
    # Elapsed: total and mean (independent of tolerance).
    assert result_t0.elapsed_total == 4.0
    assert result_t0.elapsed_mean == 2.0


def test_benchmark_result_by_category_buckets_videos():
    predictions = {
        Path("a.mp4"): Prediction(
            predicted_cuts=[10],
            ground_truth=GroundTruth(hard_cuts=[10], category="news"),
            elapsed=1.0,
        ),
        Path("b.mp4"): Prediction(
            predicted_cuts=[20],
            ground_truth=GroundTruth(hard_cuts=[20], category="sports"),
            elapsed=1.0,
        ),
        Path("c.mp4"): Prediction(
            predicted_cuts=[30],
            ground_truth=GroundTruth(hard_cuts=[30], category="news"),
            elapsed=1.0,
        ),
    }
    result = evaluate(predictions, tolerance=0)
    by_category = result.by_category()
    assert set(by_category) == {"news", "sports"}
    assert len(by_category["news"].per_video) == 2
    assert len(by_category["sports"].per_video) == 1


def test_benchmark_result_by_category_buckets_untagged_videos_as_unknown():
    # Datasets without category tags (BBC, AutoShot) leave category=None on every
    # video. by_category must bucket those under the literal key "unknown".
    predictions = {
        Path("a.mp4"): Prediction(
            predicted_cuts=[10],
            ground_truth=GroundTruth(hard_cuts=[10]),  # category defaults to None
            elapsed=1.0,
        ),
        Path("b.mp4"): Prediction(
            predicted_cuts=[20],
            ground_truth=GroundTruth(hard_cuts=[20]),
            elapsed=1.0,
        ),
    }
    result = evaluate(predictions, tolerance=0)
    by_category = result.by_category()
    assert set(by_category) == {"unknown"}
    assert len(by_category["unknown"].per_video) == 2


# --------------------------------------------------------------------- #
# EventMetrics arithmetic
# --------------------------------------------------------------------- #


def test_event_metrics_addition():
    a = EventMetrics(matched=3, false_positives=1, missed=2)
    b = EventMetrics(matched=5, false_positives=2, missed=1)
    c = a + b
    assert (c.matched, c.false_positives, c.missed) == (8, 3, 3)


def test_event_metrics_to_dict_round_trip():
    m = EventMetrics(matched=3, false_positives=1, missed=1)
    d = m.to_dict()
    assert d["matched"] == 3
    assert d["false_positives"] == 1
    assert d["missed"] == 1
    assert d["precision"] == 75.0  # 3 / 4
    assert d["recall"] == 75.0  # 3 / 4
    assert d["f1"] == 75.0
