# -*- coding: utf-8 -*-
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
""" PySceneDetect Scene Detection Tests

These tests ensure that the detection algorithms deliver consistent
results by using known ground truths of scene cut locations in the
test case material.
"""

from dataclasses import dataclass
import os
import typing as ty

import pytest

from scenedetect import detect, SceneManager, FrameTimecode, StatsManager, SceneDetector
from scenedetect.detectors import AdaptiveDetector, ContentDetector, ThresholdDetector, HashDetector
from scenedetect.backends.opencv import VideoStreamCv2


# TODO: Reduce code duplication here and in `conftest.py`
def get_absolute_path(relative_path: str) -> str:
    """ Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    abs_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError("""
Test video file (%s) must be present to run test case. This file can be obtained by running the following commands from the root of the repository:

git fetch --depth=1 https://github.com/Breakthrough/PySceneDetect.git refs/heads/resources:refs/remotes/origin/resources
git checkout refs/remotes/origin/resources -- tests/resources/
git reset
""" % relative_path)
    return abs_path


@dataclass
class TestCase:
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
            end_time=self.end_time)


def get_fast_cut_test_cases():
    """Fixture for parameterized test cases that detect fast cuts."""
    return [
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=ContentDetector(),
                start_time=1199,
                end_time=1450,
                scene_boundaries=[1199, 1226, 1260, 1281, 1334, 1365]),
            id="content_default"),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=AdaptiveDetector(),
                start_time=1199,
                end_time=1450,
                scene_boundaries=[1199, 1226, 1260, 1281, 1334, 1365]),
            id="adaptive_default"),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=HashDetector(),
                start_time=1199,
                end_time=1450,
                scene_boundaries=[1199, 1226, 1260, 1281, 1334, 1365]),
            id="hash_default"),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=ContentDetector(min_scene_len=30),
                start_time=1199,
                end_time=1450,
                scene_boundaries=[1199, 1260, 1334, 1365]),
            id="content_min_scene_len"),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=AdaptiveDetector(min_scene_len=30),
                start_time=1199,
                end_time=1450,
                scene_boundaries=[1199, 1260, 1334, 1365]),
            id="adaptive_min_scene_len"),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/goldeneye.mp4"),
                detector=HashDetector(min_scene_len=30),
                start_time=1199,
                end_time=1450,
                scene_boundaries=[1199, 1260, 1334, 1365]),
            id="hash_min_scene_len"),
    ]


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
                scene_boundaries=[0, 15, 198, 376]),
            id="threshold_testvideo_default"),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/fades.mp4"),
                detector=ThresholdDetector(),
                start_time=0,
                end_time=250,
                scene_boundaries=[0, 84, 167]),
            id="threshold_fades_default"),
        pytest.param(
            TestCase(
                path=get_absolute_path("resources/fades.mp4"),
                detector=ThresholdDetector(
                    threshold=12.0,
                    method=ThresholdDetector.Method.FLOOR,
                    add_final_scene=True,
                ),
                start_time=0,
                end_time=250,
                scene_boundaries=[0, 84, 167, 245]),
            id="threshold_fades_floor"),
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
                scene_boundaries=[0, 42, 125, 209]),
            id="threshold_fades_ceil"),
    ]

@pytest.mark.parametrize("test_case", get_fast_cut_test_cases())
def test_detect_fast_cuts(test_case: TestCase):
    scene_list = test_case.detect()
    start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert test_case.scene_boundaries == start_frames
    assert scene_list[0][0] == test_case.start_time
    assert scene_list[-1][1] == test_case.end_time


@pytest.mark.parametrize("test_case", get_fade_in_out_test_cases())
def test_detect_fades(test_case: TestCase):
    scene_list = test_case.detect()
    start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert test_case.scene_boundaries == start_frames
    assert scene_list[0][0] == test_case.start_time
    assert scene_list[-1][1] == test_case.end_time


def test_detectors_with_stats(test_video_file):
    """ Test all detectors functionality with a StatsManager. """
    # TODO(v1.0): Parameterize this test case (move fixture from cli to test config).
    for detector in [ContentDetector, ThresholdDetector, AdaptiveDetector, HashDetector]:
        video = VideoStreamCv2(test_video_file)
        stats = StatsManager()
        scene_manager = SceneManager(stats_manager=stats)
        scene_manager.add_detector(detector())
        scene_manager.auto_downscale = True
        end_time = FrameTimecode('00:00:08', video.frame_rate)
        scene_manager.detect_scenes(video=video, end_time=end_time)
        initial_scene_len = len(scene_manager.get_scene_list())
        assert initial_scene_len > 0 # test case must have at least one scene!
                                     # Re-analyze using existing stats manager.
        scene_manager = SceneManager(stats_manager=stats)
        scene_manager.add_detector(detector())

        video.reset()
        scene_manager.auto_downscale = True

        scene_manager.detect_scenes(video=video, end_time=end_time)
        scene_list = scene_manager.get_scene_list()
        assert len(scene_list) == initial_scene_len
