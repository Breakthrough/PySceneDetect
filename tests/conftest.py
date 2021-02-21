# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2021 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect Test Configuration

This file includes all pytest configuration for running PySceneDetect's tests.

These tests rely on the files in the tests/ folder in the "resources" branch of
the PySceneDetect git repository.  These files can be downloaded manually from
the following URL:

    [ https://github.com/Breakthrough/PySceneDetect/tree/resources/tests ]

"""

import os
import pytest


#
# Helper Functions
#

def get_absolute_path(relative_path):
    # type: (str) -> str
    """ Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    abs_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), relative_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(
            'Test video file (%s) must be present to run test case!' % relative_path)
    return abs_path


#
# Test Case Fixtures
#

@pytest.fixture
def test_video_file():
    # type: () -> str
    """ Fixture for test video file path (ensures file exists).

    Access in test case by adding a test_video_file argument to obtain the path.
    """
    return get_absolute_path("testvideo.mp4")

@pytest.fixture
def test_movie_clip():
    # type: () -> str
    """ Fixture for test movie clip path (ensures file exists).

    Access in test case by adding a test_movie_clip argument to obtain the path.
    """
    return get_absolute_path("goldeneye/goldeneye.mp4")
