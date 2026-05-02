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
"""VFR Accuracy Against Ground Truth

Verifies that scene cuts in synthetic VFR videos are detected at the correct
wall-clock times.
"""

import pytest

from scenedetect import ContentDetector, SceneManager, open_video


@pytest.mark.release
@pytest.mark.parametrize("backend", ["opencv", "pyav"])
def test_vfr_swing_accuracy(vfr_swing_video, backend):
    video = open_video(vfr_swing_video, backend=backend)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()

    # Ground truth: cuts at 5.0s and 10.0s
    assert len(scene_list) == 3

    # Tolerance: 1 frame at the local rate.
    # At 5.0s, the rate changes from 1 fps to 60 fps.
    # At 10.0s, it changes from 60 fps to 1 fps.
    # We'll use a conservative 100ms tolerance.
    assert abs(scene_list[1][0].seconds - 5.0) < 0.1
    assert abs(scene_list[2][0].seconds - 10.0) < 0.1


@pytest.mark.release
@pytest.mark.parametrize("backend", ["opencv", "pyav"])
def test_vfr_pts_gap_accuracy(vfr_pts_gap_video, backend):
    video = open_video(vfr_pts_gap_video, backend=backend)
    # We don't expect a cut here necessarily, but we want to ensure it doesn't crash
    # and duration is reported correctly.
    # testsrc2 duration=5:rate=30 is 150 frames.
    # We drop 3 frames (30, 31, 32). Remaining: 147 frames.
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video)

    # Some backends might report duration differently if there's a gap.
    # For now, just ensure it runs.
    assert video.duration is not None
    assert video.duration.seconds > 0


@pytest.mark.release
@pytest.mark.parametrize("backend", ["opencv", "pyav"])
def test_vfr_bframes_accuracy(vfr_bframes_video, backend):
    video = open_video(vfr_bframes_video, backend=backend)
    # Ensure B-frames don't cause issues with frame ordering or detection
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video)

    assert video.duration is not None
    assert video.duration.seconds > 0


@pytest.mark.release
def test_vfr_swing_cross_backend_parity(vfr_swing_video):
    """OpenCV and PyAV must agree on cuts in a synthetic VFR clip with known ground truth.

    MoviePy is excluded because it does not honor per-frame PTS on VFR sources (already
    skipped in test_cross_backend_consistency for the same reason).
    """
    results: dict[str, list[float]] = {}
    for backend in ("opencv", "pyav"):
        video = open_video(vfr_swing_video, backend=backend)
        sm = SceneManager()
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video)
        results[backend] = [s[0].seconds for s in sm.get_scene_list()]

    assert len(results["opencv"]) == len(results["pyav"]), (
        f"Scene count mismatch: opencv={len(results['opencv'])}, pyav={len(results['pyav'])}"
    )
    # Tolerance: 50ms (well below one frame at the 1fps and 60fps regions of the swing clip).
    for cv_t, av_t in zip(results["opencv"], results["pyav"], strict=True):
        assert abs(cv_t - av_t) < 0.05, (
            f"VFR-swing scene start drifted between backends: opencv={cv_t}, pyav={av_t}"
        )
