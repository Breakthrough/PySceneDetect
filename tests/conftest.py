# -*- coding: utf-8 -*-
#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2023 Brandon Castellano <http://www.bcastell.com>.
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
    git reset

Note that currently these tests create some temporary files which are not yet cleaned up.
"""

from typing import AnyStr
import logging
import os

import pytest

#
# Helper Functions
#


def check_exists(path: AnyStr) -> AnyStr:
    """ Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    if not os.path.exists(path):
        raise FileNotFoundError("""
Test video file (%s) must be present to run test case. This file can be obtained by running the following commands from the root of the repository:

git fetch --depth=1 https://github.com/Breakthrough/PySceneDetect.git refs/heads/resources:refs/remotes/origin/resources
git checkout refs/remotes/origin/resources -- tests/resources/
git reset
""" % path)
    return path


#
# Test Case Fixtures
#


@pytest.fixture(autouse=True)
def no_logs_gte_error(caplog):
    """Ensure no log messages with error severity or higher were reported during test execution."""
    yield
    errors = [record for record in caplog.get_records('call') if record.levelno >= logging.ERROR]
    assert not errors, "Test failed due to presence of one or more logs with ERROR severity."


@pytest.fixture
def test_video_file() -> str:
    """Simple test video containing both fast cuts and fades/dissolves."""
    return check_exists("tests/resources/testvideo.mp4")


@pytest.fixture
def test_movie_clip() -> str:
    """Movie clip containing fast cuts."""
    return check_exists("tests/resources/goldeneye.mp4")


@pytest.fixture
def corrupt_video_file() -> str:
    """Video containing a corrupted frame causing a decode failure."""
    return check_exists("tests/resources/corrupt_frame.mp4")


@pytest.fixture
def rotated_video_file() -> str:
    """Video containing a corrupted frame causing a decode failure."""
    return check_exists("tests/resources/issue-134-rotate.mp4")


@pytest.fixture
def test_image_sequence() -> str:
    """Path to a short image sequence (from counter.mp4)."""
    return "tests/resources/counter/frame%03d.png"


@pytest.fixture
def test_fades_clip() -> str:
    """Clip containing fades in/out."""
    return check_exists("tests/resources/fades.mp4")
