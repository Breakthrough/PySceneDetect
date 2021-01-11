# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2020 Brandon Castellano <http://www.bcastell.com>.
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

""" PySceneDetect scenedetect.platform Tests

This file includes unit tests for the scenedetect.platform module, containing
all platform/library/OS-specific compatibility fixes.
"""

# Standard project pylint disables for unit tests using pytest.
# pylint: disable=no-self-use, protected-access, multiple-statements, invalid-name
# pylint: disable=redefined-outer-name


from __future__ import print_function
import platform
import pytest

import cv2

from scenedetect.video_manager import VideoManager

from scenedetect.platform import CommandTooLong, invoke_command
from scenedetect.platform import opencv_version_required
from scenedetect.platform import get_aspect_ratio


def test_invoke_command():
    """ Ensures the function exists and is callable without throwing
    an exception. """
    invoke_command(['echo'])


def test_long_command():
    """ [Windows Only] Ensures that a command string too large to be handled
    is translated to the correct exception for error handling.
    """
    if platform.system() == 'Windows':
        with pytest.raises(CommandTooLong):
            invoke_command('x' * 2**15)


def test_opencv_version_required():
    """ Test version requirement function for checking installed OpenCV
    version to ensure compatibility layer works correctly. """

    version = "3.1.2"
    assert opencv_version_required([2, 0, 0], version)
    assert opencv_version_required([3], version)
    assert opencv_version_required([3, 0], version)
    assert opencv_version_required([3, 1], version)
    assert opencv_version_required([3, 1, 1], version)
    assert opencv_version_required([3, 1, 2], version)
    assert not opencv_version_required([3, 1, 3], version)
    assert not opencv_version_required([3, 2], version)
    assert not opencv_version_required([4], version)

    version = "3.1"
    assert opencv_version_required([2, 0, 0], version)
    assert opencv_version_required([3], version)
    assert opencv_version_required([3, 0], version)
    assert opencv_version_required([3, 1], version)
    assert not opencv_version_required([3, 1, 1], version)
    assert not opencv_version_required([3, 1, 2], version)
    assert not opencv_version_required([3, 2], version)
    assert not opencv_version_required([4], version)

    # Test invalid version strings.
    # Incorrect version strings always return False.
    assert not opencv_version_required([2, 0, 0], "b21412")
    assert not opencv_version_required([2, 0, 0], "2b.4")


def test_get_aspect_ratio(test_video_file):
    """ Test get_aspect_ratio function. """
    expected_value = 1.0
    epsilon = 0.01

    video_manager = VideoManager([test_video_file])
    assert abs(get_aspect_ratio(video_manager) - expected_value) < epsilon

    # Ensure non-open VideoCapture returns 1.0.
    blank_cap = cv2.VideoCapture()
    assert abs(get_aspect_ratio(blank_cap) - expected_value) < epsilon
