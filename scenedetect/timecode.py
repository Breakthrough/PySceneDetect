#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#

from dataclasses import dataclass


@dataclass
class Framerate:
    """Describes how time passes between frames in the video."""

    rate: float
    """Framerate in frames per second."""
    fixed: bool
    """True for constant frame rate (CFR), false for variable frame rate (VFR)."""


@dataclass
class Timecode:
    """Timing information associated with a given frame."""

    time: float
    """Presentation time in seconds."""
    duration: float
    """Presentation duration in seconds."""
    frame: int
    """Frame number."""
