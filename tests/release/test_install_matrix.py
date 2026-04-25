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
"""Category 8: Install Matrix Tests

Verifies behavior of PySceneDetect when different extras are installed.
These tests are intended to be run in fresh virtual environments by the
release-test workflow's install-matrix job; they fail loudly in any other
env (which is correct — they only validate a specific env layout).
"""

import importlib.util

import pytest

from scenedetect import open_video


@pytest.mark.release
def test_install_bare():
    """Should be run in an environment with no backends installed.

    Reaching this point asserts the package imports cleanly without any
    backend extra. The workflow's bare-venv shell step is the actual gate.
    """
    import scenedetect

    assert scenedetect.__version__


@pytest.mark.release
def test_opencv_only(test_video_file):
    """Should be run in an environment with ONLY opencv-python installed."""
    if importlib.util.find_spec("cv2") is None:
        pytest.skip("OpenCV not installed.")
    if importlib.util.find_spec("av") is not None:
        pytest.fail("PyAV should not be installed in this environment.")

    video = open_video(test_video_file, backend="opencv")
    assert video is not None


@pytest.mark.release
def test_pyav_only(test_video_file):
    """Should be run in an environment with ONLY av installed."""
    if importlib.util.find_spec("av") is None:
        pytest.skip("PyAV not installed.")
    if importlib.util.find_spec("cv2") is not None:
        pytest.fail("OpenCV should not be installed in this environment.")

    video = open_video(test_video_file, backend="pyav")
    assert video is not None
