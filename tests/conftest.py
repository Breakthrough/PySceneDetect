# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""" PySceneDetect Test Configuration

This file includes all pytest configuration for running PySceneDetect's tests.

These tests rely on the files in the tests/resources/ folder in the "resources" branch of
the PySceneDetect git repository. These files can be checked out via git by running the
following from the root of the repo:

    git fetch --depth=1 https://github.com/Breakthrough/PySceneDetect.git refs/heads/resources:refs/remotes/origin/resources
    git checkout refs/remotes/origin/resources -- tests/resources/

Note that currently these tests create some temporary files which are not yet cleaned up.
"""

import os
import pytest

#
# Helper Functions
#


def get_absolute_path(relative_path: str) -> str:
    # type: (str) -> str
    """ Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    abs_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError('Test video file (%s) must be present to run test case!' %
                                relative_path)
    return abs_path


#
# Test Case Fixtures
#


@pytest.fixture
def test_video_file() -> str:
    """Simple test video containing both fast cuts and fades/dissolves."""
    return get_absolute_path("resources/testvideo.mp4")


@pytest.fixture
def test_movie_clip() -> str:
    """Movie clip containing fast cuts."""
    return get_absolute_path("resources/goldeneye.mp4")


@pytest.fixture
def corrupt_video_file() -> str:
    """Video containing a corrupted frame causing a decode failure."""
    return get_absolute_path("resources/corrupt_frame.mp4")
