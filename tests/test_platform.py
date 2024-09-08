#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect scenedetect.platform Tests

This file includes unit tests for the scenedetect.platform module, containing
all platform/library/OS-specific compatibility fixes.
"""

import platform

import pytest

from scenedetect.platform import CommandTooLong, invoke_command


def test_invoke_command():
    """Ensures the function exists and is callable without throwing
    an exception."""
    if platform.system() == "Windows":
        invoke_command(["cmd"])
    else:
        invoke_command(["echo"])


def test_long_command():
    """[Windows Only] Ensures that a command string too large to be handled
    is translated to the correct exception for error handling.
    """
    if platform.system() == "Windows":
        with pytest.raises(CommandTooLong):
            invoke_command("x" * 2**15)
