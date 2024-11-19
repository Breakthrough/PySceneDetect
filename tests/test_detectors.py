#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2021 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect Scene Detection Tests

These tests ensure that the detection algorithms deliver consistent
results by using known ground truths of scene cut locations in the
test case material.
"""

import os
from dataclasses import dataclass

import numpy as np
import pytest

from scenedetect import FrameTimecode, SceneDetector, SceneManager, StatsManager, detect
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.detectors import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    KoalaDetector,
    ThresholdDetector,
)

# Untyped so each entry retains its concrete `type[...]` for parameterized construction
# (calls below pass detector-specific kwargs like `min_scene_len`).
FAST_CUT_DETECTORS = (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    KoalaDetector,
)

ALL_DETECTORS = (*FAST_CUT_DETECTORS, ThresholdDetector)

# TODO(https://scenedetect.com/issues/53): Add a test that verifies algorithms output relatively
# consistent frame scores regardless of resolution. This will ensure that threshold values will hold
# true for different input sources. Most detectors already provide this guarantee, so this is more
# to prevent any regressions in the future.


# TODO: Reduce code duplication here and in `conftest.py`
def get_absolute_path(relative_path: str) -> str:
    """Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    abs_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(
            f"""
Test video file ({relative_path}) must be present to run test case. This file can be obtained by running the following commands from the root of the repository:

git fetch --depth=1 https://github.com/Breakthrough/PySceneDetect.git refs/heads/resources:refs/remotes/origin/resources
git checkout refs/remotes/origin/resources -- tests/resources/
git reset
"""
        )
    return abs_path


@dataclass
class TestCase:
    __test__ = False
    """Properties for detector test cases."""
    path: str
    """Path to video for test case."""
    detector: SceneDetector
    """Detector instance to use."""
    start_time: int
    """Start time as frames."""
    end_time: int
    """End time as frames."""
    scene_boundaries: list[int]
    """Scene boundaries."""

    def detect(self):
        """Run scene detection for test case. Should only be called once."""
        return detect(
            video_path=self.path,
            detector=self.detector,
            start_time=self.start_time,
            end_time=self.end_time,
        )


def get_fast_cut_test_cases():
    """Fixture for parameterized test cases that detect fast cuts."""
    test_cases = []
    # goldeneye.mp4 with min_scene_len = 15 (default). HistogramDetector's recalibrated defaults
    # (threshold=0.20, bins=128) are less sensitive and do not trigger on the cut at frame 1260.
    test_cases += [
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=detector_type(min_scene_len=15),
                start_time=1199,
                end_time=1450,
                scene_boundaries=(
                    [1199, 1226, 1281, 1334, 1365]
                    if detector_type is HistogramDetector
                    else [1199, 1226, 1260, 1281, 1334, 1365]
                ),
            ),
            id=f"{detector_type.__name__}/default",
        )
        for detector_type in FAST_CUT_DETECTORS
    ]
    # goldeneye.mp4 with min_scene_len = 30
    test_cases += [
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=detector_type(min_scene_len=30),
                start_time=1199,
                end_time=1450,
                scene_boundaries=(
                    [1199, 1281, 1334, 1365]
                    if detector_type is HistogramDetector
                    else [1199, 1260, 1334, 1365]
                ),
            ),
            id=f"{detector_type.__name__}/m=30",
        )
        for detector_type in FAST_CUT_DETECTORS
    ]
    return test_cases


def get_fade_in_out_test_cases():
    """Fixture for parameterized test cases that detect fades."""
    # TODO: min_scene_len doesn't seem to be working as intended for ThresholdDetector.
    # Possibly related to #278: https://github.com/Breakthrough/PySceneDetect/issues/278
    return [
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/testvideo.mp4"),
                detector=ThresholdDetector(),
                start_time=0,
                end_time=500,
                scene_boundaries=[0, 15, 198, 377],
            ),
            id="threshold_testvideo_default",
        ),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/fades.mp4"),
                detector=ThresholdDetector(),
                start_time=0,
                end_time=250,
                scene_boundaries=[0, 84, 167],
            ),
            id="threshold_fades_default",
        ),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/fades.mp4"),
                detector=ThresholdDetector(
                    threshold=11.0,
                    method=ThresholdDetector.Method.FLOOR,
                    add_final_scene=True,
                ),
                start_time=0,
                end_time=250,
                scene_boundaries=[0, 84, 167, 245],
            ),
            id="threshold_fades_floor",
        ),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/fades.mp4"),
                detector=ThresholdDetector(
                    threshold=243.0,
                    method=ThresholdDetector.Method.CEILING,
                    add_final_scene=True,
                ),
                start_time=0,
                end_time=250,
                scene_boundaries=[0, 42, 126, 209],
            ),
            id="threshold_fades_ceil",
        ),
    ]


@pytest.mark.parametrize("test_case", get_fast_cut_test_cases())
def test_detect_fast_cuts(test_case: TestCase):
    scene_list = test_case.detect()
    start_frames = [timecode.frame_num for timecode, _ in scene_list]

    assert start_frames == test_case.scene_boundaries
    assert scene_list[0][0] == test_case.start_time
    assert scene_list[-1][1] == test_case.end_time


@pytest.mark.parametrize("test_case", get_fade_in_out_test_cases())
def test_detect_fades(test_case: TestCase):
    scene_list = test_case.detect()
    start_frames = [timecode.frame_num for timecode, _ in scene_list]
    assert start_frames == test_case.scene_boundaries
    assert scene_list[0][0] == test_case.start_time
    assert scene_list[-1][1] == test_case.end_time


def test_detectors_with_stats(test_video_file):
    """Test all detectors functionality with a StatsManager."""
    # TODO(v1.0): Parameterize this test case (move fixture from cli to test config).
    for detector in ALL_DETECTORS:
        video = VideoStreamCv2(test_video_file)
        stats = StatsManager()
        scene_manager = SceneManager(stats_manager=stats)
        scene_manager.add_detector(detector())
        scene_manager.auto_downscale = True
        end_time = FrameTimecode("00:00:05", video.frame_rate)
        scene_manager.detect_scenes(video=video, end_time=end_time)
        initial_scene_len = len(scene_manager.get_scene_list())
        assert initial_scene_len > 0, "Test case must have at least one scene."
        # Re-analyze using existing stats manager.
        scene_manager = SceneManager(stats_manager=stats)
        scene_manager.add_detector(detector())
        video.reset()
        scene_manager.auto_downscale = True
        scene_manager.detect_scenes(video=video, end_time=end_time)
        scene_list = scene_manager.get_scene_list()
        assert len(scene_list) == initial_scene_len


@pytest.mark.parametrize("detector_type", FAST_CUT_DETECTORS)
@pytest.mark.parametrize(
    "min_scene_len",
    # 30 frames at goldeneye.mp4's 24000/1001 (~23.976) fps is ~1.2513s. All four forms should
    # produce identical cut lists, demonstrating that detectors accept temporal as well as
    # frame-count values.
    [30, 1.25, "1.25s", "00:00:01.250"],
)
def test_min_scene_len_accepts_time_values(detector_type, min_scene_len):
    """Detectors accept min_scene_len as int (frames), float (seconds), or str (timecode)."""
    test_case = TestCase(
        path=get_absolute_path("resources/goldeneye.mp4"),
        detector=detector_type(min_scene_len=min_scene_len),
        start_time=1199,
        end_time=1450,
        # HistogramDetector's recalibrated defaults do not trigger on the cut at frame 1260
        # (see `get_fast_cut_test_cases`).
        scene_boundaries=(
            [1199, 1281, 1334, 1365]
            if detector_type is HistogramDetector
            else [1199, 1260, 1334, 1365]
        ),
    )
    scene_list = test_case.detect()
    start_frames = [timecode.frame_num for timecode, _ in scene_list]
    assert start_frames == test_case.scene_boundaries


def test_adaptive_detector_min_scene_len_uses_target_frame():
    """AdaptiveDetector applies min_scene_len to the emitted cut, not the current frame.

    AdaptiveDetector scores a target frame `window_width` behind the frame currently
    being processed. Comparing min_scene_len against the current frame lets a second
    peak emit a cut only `window_width` frames after the previous one (issue #408).
    """
    window_width = 20
    min_scene_len = 24
    detector = AdaptiveDetector(
        adaptive_threshold=2.0,
        window_width=window_width,
        min_scene_len=min_scene_len,
        min_content_val=15.0,
        luma_only=True,
    )
    fps = 30.0
    n_frames = 180
    cuts: list[FrameTimecode] = []
    for frame_num in range(n_frames):
        # Hard cuts at 100 and 104 (4 frames apart) plus a later valid cut at 140.
        # The 4-frame pair matches the report: min_scene_len - window_width.
        value = 255 if 100 <= frame_num <= 103 or 140 <= frame_num <= 143 else 0
        frame = np.full((16, 16, 3), value, dtype=np.uint8)
        cuts.extend(detector.process_frame(FrameTimecode(frame_num, fps), frame))

    cut_frames = [cut.frame_num for cut in cuts]
    assert cut_frames == [100, 140]


@pytest.mark.parametrize("start_time", [1217, 1224])
def test_koala_detector_keeps_cut_near_start(start_time: int):
    """KoalaDetector emits cuts that fall within its look-ahead buffer of the first frame.

    The cut at frame 1226 is 9 (or 2) frames after `start_time`; `min_scene_len` is 0 so the
    minimum-length rule cannot suppress it.
    """
    scene_list = detect(
        video_path=get_absolute_path("resources/goldeneye.mp4"),
        detector=KoalaDetector(min_scene_len=0),
        start_time=start_time,
        end_time=1373,
    )
    start_frames = [timecode.frame_num for timecode, _ in scene_list]
    assert start_frames == [start_time, 1226, 1260, 1281, 1334, 1365]
    assert scene_list[-1][1].frame_num == 1373


def test_koala_detector_callback_fires_per_cut():
    """KoalaDetector returns cuts from `process_frame`, so the SceneManager callback sees each."""
    video = VideoStreamCv2(get_absolute_path("resources/goldeneye.mp4"))
    video.seek(1199)
    scene_manager = SceneManager()
    scene_manager.add_detector(KoalaDetector())
    callback_frames: list[int] = []
    scene_manager.detect_scenes(
        video=video,
        end_time=FrameTimecode(1450, video.frame_rate),
        callback=lambda _image, timecode: callback_frames.append(timecode.frame_num),
    )
    assert callback_frames == [1226, 1260, 1281, 1334, 1365]
    scene_starts = [start.frame_num for start, _ in scene_manager.get_scene_list()]
    assert scene_starts == [1199, *callback_frames]


def _koala_cuts_from_scores(scores: list[float], **kwargs) -> list[int]:
    """Drive KoalaDetector's cut logic with precomputed frame scores, bypassing image processing.

    Returns the indices into `scores` at which cuts were emitted (`min_scene_len` is 0).
    """
    detector = KoalaDetector(min_scene_len=0, **kwargs)
    detector._last_cut = FrameTimecode(0, 24.0)
    cuts: list[FrameTimecode] = []
    for index, score in enumerate(scores):
        cuts += detector._score_frame(FrameTimecode(index + 1, 24.0), score)
    cuts += detector.post_process(FrameTimecode(len(scores) + 1, 24.0))
    return [cut.frame_num - 1 for cut in cuts]


def _reference_koala_cuts(scores: list[float], threshold: float = 0.0) -> list[int]:
    """Reference for KoalaDetector's placement rule with the adaptive rule off: one cut at the
    first frame of each run of consecutive scores below `threshold`."""
    cuts: list[int] = []
    in_run = False
    for index, score in enumerate(scores):
        flagged = score < threshold
        if flagged and not in_run:
            cuts.append(index)
        in_run = flagged
    return cuts


def test_koala_detector_cut_placement_matches_reference():
    """Random score sequences yield the same cuts as the reference placement rule."""
    rng = np.random.default_rng(1)
    for scores in rng.uniform(-1.0, 2.5, size=(200, 40)).tolist():
        assert _koala_cuts_from_scores(scores) == _reference_koala_cuts(scores)
    # A multi-frame transition yields one cut at its first frame, for both modes.
    scores = [2.0] * 5 + [-1.0, -1.0, -1.0] + [2.0] * 3
    assert _koala_cuts_from_scores(scores) == [5]
    assert _koala_cuts_from_scores(scores, adaptive=True) == [5]


def test_koala_detector_adaptive_rule_flags_smoothed_drop():
    """A dip that never crosses `threshold` is only found by the adaptive rule."""
    # Smoothed score at index 11 is 0.3, far below the trimmed mean (2.0) of the window.
    scores = [2.0] * 10 + [0.3, 0.3, 0.3] + [2.0] * 4
    assert _koala_cuts_from_scores(scores) == []
    assert _koala_cuts_from_scores(scores, adaptive=True) == [11]


def test_koala_detector_adaptive_smear_does_not_move_cut():
    """The moving average smears a large drop onto the preceding frame, which the adaptive rule
    flags; the cut must stay on the frame whose raw score crossed the threshold."""
    scores = [2.0] * 10 + [-3.0] + [2.0] * 5
    assert _koala_cuts_from_scores(scores) == [10]
    assert _koala_cuts_from_scores(scores, adaptive=True) == [10]


@pytest.mark.parametrize("adaptive", [False, True])
def test_koala_detector_cut_on_final_frame(adaptive: bool):
    """A transition on the very last frame is still emitted (from `post_process` when the
    smoothing look-ahead holds it back)."""
    detector = KoalaDetector(min_scene_len=0, adaptive=adaptive)
    black = np.zeros((64, 64, 3), dtype=np.uint8)
    white = np.full((64, 64, 3), 255, dtype=np.uint8)
    cuts: list[FrameTimecode] = []
    for frame_num, frame in enumerate([black] * 10 + [white]):
        cuts += detector.process_frame(FrameTimecode(frame_num, 24.0), frame)
    cuts += detector.post_process(FrameTimecode(11, 24.0))
    assert [cut.frame_num for cut in cuts] == [10]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"filter_size": 2},
        {"filter_size": 0},
        {"window_size": 4},
        {"window_size": 8, "filter_size": 9},
    ],
)
def test_koala_detector_rejects_invalid_window(kwargs: dict):
    with pytest.raises(ValueError):
        KoalaDetector(**kwargs)
    # The smallest valid window is also the largest valid filter for it.
    KoalaDetector(window_size=5, filter_size=5)


@pytest.mark.parametrize(
    "frame",
    [
        np.zeros((64, 64, 3), dtype=np.float32),
        np.zeros((64, 64), dtype=np.uint8),
        np.zeros((64, 64, 1), dtype=np.uint8),
    ],
)
def test_koala_detector_rejects_invalid_frames(frame: np.ndarray):
    with pytest.raises(ValueError):
        KoalaDetector().process_frame(FrameTimecode(0, 24.0), frame)
