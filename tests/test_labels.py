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
from scenedetect.output.labels import MIN_PEGASUS_SCENE_SECONDS

FPS = Fraction(30)
# Two scenes, each well over the pegasus1.5 4s minimum (5s then 10s).
SCENE_LIST = [
    (FrameTimecode(0, FPS), FrameTimecode(150, FPS)),
    (FrameTimecode(150, FPS), FrameTimecode(450, FPS)),
]


class _FakeAnalyzeResponse:
    def __init__(self, data):
        self.data = data


class _FakeClient:
    """Records each analyze() call so wiring can be asserted without hitting the network."""

    def __init__(self, error_on_call=None, error=None):
        self.calls = []
        # If set, analyze() raises on the matching (0-based) call index. `error` is a zero-arg
        # factory for the exception to raise; defaults to a BadRequestError.
        self._error_on_call = error_on_call
        self._error = error

    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        if self._error_on_call is not None and len(self.calls) - 1 == self._error_on_call:
            if self._error is not None:
                raise self._error()
            from twelvelabs.errors.bad_request_error import BadRequestError

            raise BadRequestError(body={"code": "parameter_invalid", "message": "boom"})
        return _FakeAnalyzeResponse(f"  scene at {kwargs['start_time']}s  ")


def test_label_scenes_wires_per_scene_timecodes():
    client = _FakeClient()
    labels = label_scenes(SCENE_LIST, video_url="https://example.com/v.mp4", client=client)

    assert [type(label) for label in labels] == [SceneLabel, SceneLabel]
    # One Pegasus call per scene, with that scene's start/end in seconds.
    assert [(c["start_time"], c["end_time"]) for c in client.calls] == [(0.0, 5.0), (5.0, 15.0)]
    # The source is forwarded as a VideoContext, not a raw video_id (unsupported on pegasus1.5).
    assert all("video_id" not in c for c in client.calls)
    assert all(c["video"].url == "https://example.com/v.mp4" for c in client.calls)
    # Response text is stripped and indices run parallel to the input scene list.
    assert labels[0].index == 0 and labels[0].label == "scene at 0.0s"
    assert labels[1].start_time == 5.0 and labels[1].end_time == 15.0


def test_label_scenes_accepts_asset_id():
    client = _FakeClient()
    label_scenes(SCENE_LIST, asset_id="asset-1", client=client)
    # An asset_id is sent as a VideoContext_AssetId, which pegasus1.5 supports.
    assert all(c["video"].asset_id == "asset-1" for c in client.calls)


def test_label_scenes_requires_exactly_one_source():
    client = _FakeClient()
    with pytest.raises(ValueError):
        label_scenes(SCENE_LIST, client=client)
    with pytest.raises(ValueError):
        label_scenes(SCENE_LIST, asset_id="a", video_url="http://x", client=client)


def test_label_scenes_rejects_video_id():
    # video_id is unsupported by pegasus1.5; we fail fast with a clear error instead of a raw 400.
    client = _FakeClient()
    with pytest.raises(ValueError, match="video_id"):
        label_scenes(SCENE_LIST, video_id="vid123", client=client)


def test_label_scenes_skips_short_scene_without_aborting():
    # A sub-4s scene sits between two valid ones; it must be skipped, not fatal.
    assert MIN_PEGASUS_SCENE_SECONDS == 4.0
    scene_list = [
        (FrameTimecode(0, FPS), FrameTimecode(150, FPS)),  # 5s, kept
        (FrameTimecode(150, FPS), FrameTimecode(269, FPS)),  # 119 frames ≈ 3.97s, skipped
        (FrameTimecode(450, FPS), FrameTimecode(600, FPS)),  # 5s, kept
    ]
    client = _FakeClient()
    labels = label_scenes(scene_list, video_url="https://example.com/v.mp4", client=client)

    # The short scene never reached analyze(), and the run continued past it.
    assert len(client.calls) == 2
    assert [label.index for label in labels] == [0, 2]


def test_label_scenes_skips_per_scene_api_error():
    # A BadRequestError on the first scene is logged and skipped; the batch keeps going.
    client = _FakeClient(error_on_call=0)
    labels = label_scenes(SCENE_LIST, video_url="https://example.com/v.mp4", client=client)

    assert len(client.calls) == 2  # both attempted
    assert [label.index for label in labels] == [1]  # only the second succeeded


def test_label_scenes_stops_gracefully_on_rate_limit():
    # A 429 on the second scene must stop the pass (no further calls) and return the labels
    # already gathered, without raising — long free-tier videos can hit the quota mid-pass.
    from twelvelabs.errors.too_many_requests_error import TooManyRequestsError

    def _rate_limited():
        return TooManyRequestsError(
            body={"code": "too_many_requests"}, headers={"Retry-After": "86400"}
        )

    client = _FakeClient(error_on_call=1, error=_rate_limited)
    labels = label_scenes(SCENE_LIST, video_url="https://example.com/v.mp4", client=client)

    # The first scene succeeded; the second 429'd and stopped the run before any third call.
    assert len(client.calls) == 2
    assert [label.index for label in labels] == [0]
    assert labels[0].label == "scene at 0.0s"


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
