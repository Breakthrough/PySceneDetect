#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect Scene Detection Tests

These tests ensure that the detection algorithms deliver consistent
results by using known ground truths of scene cut locations in the
test case material.
"""

import os
import typing as ty
from dataclasses import dataclass

import pytest

from scenedetect import FrameTimecode, SceneDetector, SceneManager, StatsManager, detect
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.detectors import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
)

FAST_CUT_DETECTORS: ty.Tuple[ty.Type[SceneDetector]] = (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
)

ALL_DETECTORS: ty.Tuple[ty.Type[SceneDetector]] = (*FAST_CUT_DETECTORS, ThresholdDetector)

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
            """
Test video file (%s) must be present to run test case. This file can be obtained by running the following commands from the root of the repository:

git fetch --depth=1 https://github.com/Breakthrough/PySceneDetect.git refs/heads/resources:refs/remotes/origin/resources
git checkout refs/remotes/origin/resources -- tests/resources/
git reset
"""
            % relative_path
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
    scene_boundaries: ty.List[int]
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
    # goldeneye.mp4 with min_scene_len = 15 (default)
    test_cases += [
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=detector_type(min_scene_len=15),
                start_time=1199,
                end_time=1450,
                scene_boundaries=[1199, 1226, 1260, 1281, 1334, 1365],
            ),
            id="%s/default" % detector_type.__name__,
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
                scene_boundaries=[1199, 1260, 1334, 1365],
            ),
            id="%s/m=30" % detector_type.__name__,
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
                scene_boundaries=[0, 15, 198, 376],
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
                scene_boundaries=[0, 42, 125, 209],
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


# TODO(v0.8): Remove this test during the removal of `scenedetect.scene_detector`.
def test_deprecated_detector_module_emits_warning_on_import():
    SCENE_DETECTOR_WARNING = (
        "The `scene_detector` submodule is deprecated, import from the base package instead."
    )
    with pytest.warns(DeprecationWarning, match=SCENE_DETECTOR_WARNING):
        from scenedetect.scene_detector import SceneDetector as _
