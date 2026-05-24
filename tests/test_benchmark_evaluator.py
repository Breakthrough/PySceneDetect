"""Unit tests for the benchmark evaluator.

These tests exercise the matching, tolerance, and aggregation logic with
synthetic prediction / ground-truth lists - no video decoding required.
They cover the TRECVID-SBD-style scoring contract documented in
``benchmark/README.md``.
"""

from __future__ import annotations

import math

import pytest

from benchmark.evaluator import (
    Evaluator,
    EventInterval,
    EventMetrics,
    GroundTruth,
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
    v = score_video([15], ground_truth, tolerances=(0, 1), video_file="x.mp4", elapsed=0.0)
    assert v.fades.matched == 1
    assert v.hard_cuts[1].matched == 0  # hard match was preempted by the fade
    assert v.hard_cuts[1].missed == 1  # hard ground-truth cut at 16 is now a miss


def test_score_video_pred_outside_fade_falls_to_hard():
    ground_truth = GroundTruth(hard_cuts=[30], fades=[EventInterval(10, 20)])
    v = score_video([30], ground_truth, tolerances=(0,), video_file="x.mp4", elapsed=0.0)
    assert v.fades.matched == 0
    assert v.fades.missed == 1  # fade still missed
    assert v.hard_cuts[0].matched == 1


# --------------------------------------------------------------------- #
# Mean absolute offset (localization error on hard-cut matches only)
# --------------------------------------------------------------------- #


def test_mean_abs_offset_only_hard_matches():
    ground_truth = GroundTruth(
        hard_cuts=[100, 200, 300],
        fades=[EventInterval(50, 60)],
    )
    # Predictions: fade hit at 55 (excluded from offset), hard matches
    # at 100 (offset 0), 201 (offset 1), 302 (offset 2 - outside tolerance 1).
    v = score_video([55, 100, 201, 302], ground_truth, (0, 1), "x.mp4", 0.0)
    # tolerance 0: only the perfect 100 match counts.
    assert v.hard_cuts[0].matched == 1
    assert v.mean_abs_offset(0) == 0.0
    # tolerance 1: 100 (0) and 201 (1) match; 302 is out of tolerance.
    assert v.hard_cuts[1].matched == 2
    assert v.mean_abs_offset(1) == 0.5


def test_mean_abs_offset_nan_when_no_matches():
    ground_truth = GroundTruth(hard_cuts=[1000])
    v = score_video([5], ground_truth, (0,), "x.mp4", 0.0)
    assert math.isnan(v.mean_abs_offset(0))


def test_benchmark_result_mean_abs_offset_nan_when_no_matches_across_videos():
    # Two videos, both producing zero hard-cut matches. The aggregate offset
    # has zero sum and zero count, so nan must propagate at the
    # BenchmarkResult level, not just per-video.
    pred_scenes = {
        "a.txt": {
            "video_file": "a.mp4",
            "elapsed": 1.0,
            "pred_scenes": [5],
            "ground_truth": GroundTruth(hard_cuts=[1000]),
        },
        "b.txt": {
            "video_file": "b.mp4",
            "elapsed": 1.0,
            "pred_scenes": [7],
            "ground_truth": GroundTruth(hard_cuts=[2000]),
        },
    }
    result = evaluate(pred_scenes, tolerances=(0,))
    assert math.isnan(result.mean_abs_offset_hard_cuts[0])


# --------------------------------------------------------------------- #
# Aggregate result: sum-of-counts across videos
# --------------------------------------------------------------------- #


def test_benchmark_result_aggregate_matches_sum_of_counts():
    pred_scenes = {
        "vid_a.txt": {
            "video_file": "vid_a.mp4",
            "elapsed": 1.0,
            "pred_scenes": [10, 20],
            "ground_truth": GroundTruth(hard_cuts=[10, 21]),
        },
        "vid_b.txt": {
            "video_file": "vid_b.mp4",
            "elapsed": 3.0,
            "pred_scenes": [50, 99],
            "ground_truth": GroundTruth(hard_cuts=[50, 100]),
        },
    }
    result = evaluate(pred_scenes, tolerances=(0, 1))
    # vid_a tolerance 0: only 10 matches -> 1 matched, 1 fp, 1 missed
    # vid_b tolerance 0: only 50 matches -> 1 matched, 1 fp, 1 missed
    # Aggregate: 2 matched, 2 false positives, 2 missed
    assert result.hard_cuts[0].matched == 2
    assert result.hard_cuts[0].false_positives == 2
    assert result.hard_cuts[0].missed == 2
    # Tolerance 1: both predictions in each video match -> 4 matched, 0 fp, 0 missed
    assert result.hard_cuts[1].matched == 4
    assert result.hard_cuts[1].false_positives == 0
    assert result.hard_cuts[1].missed == 0
    # Elapsed: total and mean
    assert result.elapsed_total == 4.0
    assert result.elapsed_mean == 2.0


def test_benchmark_result_by_category_buckets_videos():
    pred_scenes = {
        "a.txt": {
            "video_file": "a.mp4",
            "elapsed": 1.0,
            "pred_scenes": [10],
            "ground_truth": GroundTruth(hard_cuts=[10], category="news"),
        },
        "b.txt": {
            "video_file": "b.mp4",
            "elapsed": 1.0,
            "pred_scenes": [20],
            "ground_truth": GroundTruth(hard_cuts=[20], category="sports"),
        },
        "c.txt": {
            "video_file": "c.mp4",
            "elapsed": 1.0,
            "pred_scenes": [30],
            "ground_truth": GroundTruth(hard_cuts=[30], category="news"),
        },
    }
    result = evaluate(pred_scenes, tolerances=(0,))
    by_category = result.by_category()
    assert set(by_category) == {"news", "sports"}
    assert len(by_category["news"].per_video) == 2
    assert len(by_category["sports"].per_video) == 1


def test_benchmark_result_by_category_buckets_untagged_videos_as_unknown():
    # Datasets without category tags (BBC, AutoShot) leave category=None on every
    # video. by_category must bucket those under the literal key "unknown".
    pred_scenes = {
        "a.txt": {
            "video_file": "a.mp4",
            "elapsed": 1.0,
            "pred_scenes": [10],
            "ground_truth": GroundTruth(hard_cuts=[10]),  # category defaults to None
        },
        "b.txt": {
            "video_file": "b.mp4",
            "elapsed": 1.0,
            "pred_scenes": [20],
            "ground_truth": GroundTruth(hard_cuts=[20]),
        },
    }
    result = evaluate(pred_scenes, tolerances=(0,))
    by_category = result.by_category()
    assert set(by_category) == {"unknown"}
    assert len(by_category["unknown"].per_video) == 2


# --------------------------------------------------------------------- #
# Backward-compatible shim
# --------------------------------------------------------------------- #


def test_evaluate_performance_matches_legacy_set_intersection_semantics(tmp_path):
    """At tolerance 0, the legacy shim must report the same recall, precision
    and F1 numbers the original ``set(pred) & set(gt)`` implementation gave."""
    # Write a tiny BBC/AutoShot-style scene file: tab-separated, second column
    # is the 0-based frame index, second column +1 -> 1-based scene frame.
    scene_file = tmp_path / "01-scenes.txt"
    scene_file.write_text("0\t9\n1\t19\n2\t29\n")  # 1-based ground truth: [10, 20, 30]
    # Predictions: hit two of three; one off by 2 (false positive).
    pred_scenes = {
        str(scene_file): {
            "video_file": "v.mp4",
            "elapsed": 0.5,
            "pred_scenes": [10, 20, 32],
        }
    }
    out = Evaluator().evaluate_performance(pred_scenes)
    # 2 of 3 ground-truth cuts recovered -> recall = 2/3
    assert out["recall"] == pytest.approx(200.0 / 3)
    # 2 of 3 predictions correct -> precision = 2/3
    assert out["precision"] == pytest.approx(200.0 / 3)
    # F1 of two equal values is that value
    assert out["f1"] == pytest.approx(200.0 / 3)
    assert out["elapsed"] == 0.5


def test_evaluate_performance_uses_provided_ground_truth_over_scene_file():
    # When the payload already has a typed GroundTruth, the shim must
    # honor it and not try to re-read a non-existent text file.
    pred_scenes = {
        "synthetic-key": {
            "video_file": "v.mp4",
            "elapsed": 0.1,
            "pred_scenes": [100, 200],
            "ground_truth": GroundTruth(hard_cuts=[100, 200]),
        }
    }
    out = Evaluator().evaluate_performance(pred_scenes)
    assert out["recall"] == 100.0
    assert out["precision"] == 100.0
    assert out["f1"] == 100.0


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
