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

from scenedetect.platform import CommandTooLong, invoke_command
from scenedetect.platform import get_aspect_ratio


def test_invoke_command():
    """ Ensures the function exists and is callable without throwing
    an exception. """
    if platform.system() == 'Windows':
        invoke_command(['cmd'])
    else:
        invoke_command(['echo'])


def test_long_command():
    """ [Windows Only] Ensures that a command string too large to be handled
    is translated to the correct exception for error handling.
    """
    if platform.system() == 'Windows':
        with pytest.raises(CommandTooLong):
            invoke_command('x' * 2**15)


def test_get_aspect_ratio(test_video_file):
    """ Test get_aspect_ratio function. """
    expected_value = 1.0
    epsilon = 0.01

    cap = cv2.VideoCapture(test_video_file)
    assert abs(get_aspect_ratio(cap) - expected_value) < epsilon

    # Ensure non-open VideoCapture returns 1.0.
    blank_cap = cv2.VideoCapture()
    assert abs(get_aspect_ratio(blank_cap) - expected_value) < epsilon

    # TODO: Add non-square example to test cases.
