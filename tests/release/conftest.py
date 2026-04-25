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
"""Fixtures for the release test suite."""

import os

import pytest

from .synthetic import (
    generate_synthetic_matrix_video,
    generate_vfr_bframes,
    generate_vfr_pts_gap,
    generate_vfr_swing,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def no_logs_gte_error():
    # Override the strict autouse guard from tests/conftest.py: release tests
    # exercise known-pathological inputs that legitimately emit ERROR logs.
    yield


@pytest.fixture
def vfr_swing_video(tmp_path) -> str:
    path = str(tmp_path / "vfr_swing.mp4")
    generate_vfr_swing(path)
    return path


@pytest.fixture
def vfr_pts_gap_video(tmp_path) -> str:
    path = str(tmp_path / "vfr_pts_gap.mp4")
    generate_vfr_pts_gap(path)
    return path


@pytest.fixture
def vfr_bframes_video(tmp_path) -> str:
    path = str(tmp_path / "vfr_bframes.mp4")
    generate_vfr_bframes(path)
    return path


@pytest.fixture
def long_video() -> str:
    """Long synthetic video for memory/FD leak stress testing.

    Checked in under tests/resources/ on the resources branch; encode locally
    with ffmpeg if missing (see scripts/encode_stress_video.sh or the plan).
    """
    path = os.path.join(REPO_ROOT, "tests", "resources", "stress_15min.mp4")
    if not os.path.exists(path):
        pytest.skip(
            "tests/resources/stress_15min.mp4 not present. Generate with: "
            'ffmpeg -f lavfi -i "testsrc2=duration=900:size=640x480:rate=30" '
            "-c:v libx264 -crf 30 -preset slow -pix_fmt yuv420p "
            "tests/resources/stress_15min.mp4"
        )
    return path


@pytest.fixture
def synthetic_matrix_generator(tmp_path):
    def _generate(codec: str, container: str, extra_args: list | None = None) -> str:
        path = str(tmp_path / f"synthetic_{codec}_{container}.{container}")
        generate_synthetic_matrix_video(path, codec, container, extra_args)
        return path

    return _generate
