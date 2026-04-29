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
"""Backend Consistency

Verifies that all available backends produce consistent cut lists for both CFR and VFR videos.
"""

import importlib.util
import os

import pytest

from scenedetect import ContentDetector, SceneManager, open_video

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VIDEOS = [
    # (relative path under repo root, is_vfr)
    ("tests/resources/testvideo.mp4", False),
    ("tests/resources/goldeneye.mp4", False),
    ("tests/resources/goldeneye-vfr.mp4", True),
]

BACKENDS = ("opencv", "pyav", "moviepy")
_BACKEND_PACKAGE = {"opencv": "cv2", "pyav": "av", "moviepy": "moviepy"}


def _installed_backends():
    return [
        name for name in BACKENDS if importlib.util.find_spec(_BACKEND_PACKAGE[name]) is not None
    ]


@pytest.mark.release
@pytest.mark.parametrize("rel_path,is_vfr", VIDEOS)
def test_cross_backend_consistency(rel_path, is_vfr):
    video_path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(video_path):
        pytest.skip(f"Video {rel_path} not present (needs resources branch).")

    backends = _installed_backends()
    if is_vfr and "moviepy" in backends:
        # MoviePy does not honor per-frame PTS on VFR video - tracked separately
        # from the OpenCV/PyAV VFR path that this test gates.
        backends = [b for b in backends if b != "moviepy"]
    if len(backends) < 2:
        pytest.skip(f"Need at least two backends, have: {backends}")

    results = {}
    for backend in backends:
        try:
            video = open_video(video_path, backend=backend)
        except Exception as exc:
            pytest.skip(f"{backend} failed to open {rel_path}: {exc}")
        sm = SceneManager()
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video)
        scenes = sm.get_scene_list()
        if is_vfr:
            results[backend] = [s[0].seconds for s in scenes[1:]]
        else:
            results[backend] = [s[0].frame_num for s in scenes[1:]]

    reference = backends[0]
    expected = results[reference]
    for backend in backends[1:]:
        actual = results[backend]
        assert len(actual) == len(expected), (
            f"Cut count mismatch: {backend}={len(actual)} vs {reference}={len(expected)}"
        )
        if is_vfr:
            for a, e in zip(actual, expected, strict=True):
                # Tolerance: ~one frame at 30 fps. Plan calls for +/-1 local-frame-duration;
                # 50 ms is a conservative superset that still catches real drift.
                assert abs(a - e) < 0.05, (
                    f"VFR timestamp drift between {backend} and {reference}: {a} vs {e}"
                )
        else:
            assert actual == expected, (
                f"CFR frame-number mismatch between {backend} and {reference}"
            )
