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
"""Golden Result Tests

Verifies that detectors produce the exact same timecodes as stored in the golden JSONs.
"""

import json
import os
import sys

import pytest

from scenedetect import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    SceneManager,
    ThresholdDetector,
    open_video,
)

DETECTOR_MAP = {
    "ContentDetector": ContentDetector,
    "AdaptiveDetector": AdaptiveDetector,
    "ThresholdDetector": ThresholdDetector,
    "HistogramDetector": HistogramDetector,
    "HashDetector": HashDetector,
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN_DIR = os.path.join(REPO_ROOT, "tests", "resources", "goldens")


def get_golden_files():
    if not os.path.exists(GOLDEN_DIR):
        return []
    return sorted(f for f in os.listdir(GOLDEN_DIR) if f.endswith(".json"))


@pytest.mark.release
@pytest.mark.parametrize("golden_file", get_golden_files())
def test_golden_regression(golden_file):
    with open(os.path.join(GOLDEN_DIR, golden_file)) as f:
        expected_cuts = json.load(f)["cuts"]

    # Parse filename: video.mp4.DetectorName.suffix.json
    parts = golden_file.split(".")
    video_name = parts[0] + "." + parts[1]
    detector_name = parts[2]
    suffix = parts[3]

    video_path = os.path.join(REPO_ROOT, "tests", "resources", video_name)
    if not os.path.exists(video_path):
        pytest.skip(f"Video {video_path} not found.")

    # TODO: HistogramDetector and AdaptiveDetector diverge on macOS; the decoder pipeline seems to
    # produce different YUV bytes and/or there is a math error somewhere.
    if sys.platform == "darwin" and detector_name in ("HistogramDetector", "AdaptiveDetector"):
        pytest.skip(f"{detector_name} goldens diverge on macOS (decoder/SIMD pipeline)")

    detector_class = DETECTOR_MAP[detector_name]
    params = {}
    if detector_name == "ContentDetector" and suffix == "t30":
        params = {"threshold": 30.0}
    elif detector_name == "AdaptiveDetector" and suffix == "t5":
        params = {"adaptive_threshold": 5.0}

    video = open_video(video_path, backend="pyav")
    scene_manager = SceneManager()
    scene_manager.add_detector(detector_class(**params))
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    actual_cuts = [scene[0].frame_num for scene in scene_list[1:]]

    assert actual_cuts == expected_cuts, f"Cut list mismatch for {golden_file}"
