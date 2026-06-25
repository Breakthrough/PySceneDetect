#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Tests for scenedetect.output.labels (optional TwelveLabs scene labelling)."""

import os
from fractions import Fraction

import pytest

from scenedetect import FrameTimecode
from scenedetect.output import SceneLabel, label_scenes

FPS = Fraction(30)
SCENE_LIST = [
    (FrameTimecode(0, FPS), FrameTimecode(30, FPS)),
    (FrameTimecode(30, FPS), FrameTimecode(90, FPS)),
]


class _FakeAnalyzeResponse:
    def __init__(self, data):
        self.data = data


class _FakeClient:
    """Records each analyze() call so wiring can be asserted without hitting the network."""

    def __init__(self):
        self.calls = []

    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeAnalyzeResponse(f"  scene at {kwargs['start_time']}s  ")


def test_label_scenes_wires_per_scene_timecodes():
    client = _FakeClient()
    labels = label_scenes(SCENE_LIST, video_id="vid123", client=client)

    assert [type(label) for label in labels] == [SceneLabel, SceneLabel]
    # One Pegasus call per scene, with that scene's start/end in seconds.
    assert [(c["start_time"], c["end_time"]) for c in client.calls] == [(0.0, 1.0), (1.0, 3.0)]
    assert all(c["video_id"] == "vid123" for c in client.calls)
    # Response text is stripped and indices run parallel to the input scene list.
    assert labels[0].index == 0 and labels[0].label == "scene at 0.0s"
    assert labels[1].start_time == 1.0 and labels[1].end_time == 3.0


def test_label_scenes_requires_exactly_one_source():
    client = _FakeClient()
    with pytest.raises(ValueError):
        label_scenes(SCENE_LIST, client=client)
    with pytest.raises(ValueError):
        label_scenes(SCENE_LIST, video_id="a", video_url="http://x", client=client)


@pytest.mark.skipif(
    not os.environ.get("TWELVELABS_API_KEY"),
    reason="requires TWELVELABS_API_KEY and a reachable video",
)
def test_label_scenes_integration():
    # Opt-in: needs a real key and a public video URL via TWELVELABS_TEST_VIDEO_URL.
    video_url = os.environ.get("TWELVELABS_TEST_VIDEO_URL")
    if not video_url:
        pytest.skip("set TWELVELABS_TEST_VIDEO_URL to a public video to run this test")
    labels = label_scenes(SCENE_LIST[:1], video_url=video_url)
    assert len(labels) == 1
    assert isinstance(labels[0].label, str) and labels[0].label
