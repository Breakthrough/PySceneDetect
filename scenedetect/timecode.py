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
"""``scenedetect.timecode`` Module

This module contains types and functions for handling video timecodes, including parsing user input
and timecode format conversion.
"""

from dataclasses import dataclass
from fractions import Fraction


# TODO(@Breakthrough): Add conversion from Timecode -> FrameTimecode for backwards compatibility.
# TODO(@Breakthrough): How should we deal with frame numbers? We might need to detect if a video is
# VFR or not, and if so, either omit them or always start them from 0 regardless of the start seek.
# With PyAV we can probably assume the video is VFR if the guessed rate of the stream differs
# from the average rate.
#
# Each backend has slight nuances we have to take into account:
#   - PyAV: Does not include a position in frames, we can probably estimate it. Need to also compare
#     with how OpenCV handles this. It also seems to fail to decode the last frame. This library
#     provides the most accurate timing information however.
#   - OpenCV: Lacks any kind of timebase, only provides position in milliseconds and as frames.
#     This is probably sufficient, since we could just use 1ms as a timebase.
#   - MoviePy: Assumes fixed framerate and doesn't include timing information. Fixing this is
#     probably not feasible, so we should make sure the docs warn users about this.
#
#
@dataclass
class Timecode:
    """Timing information associated with a given frame."""

    pts: int
    """Presentation timestamp of the frame in units of `time_base`."""
    time_base: Fraction
    """The base unit in which `pts` is measured."""

    @property
    def seconds(self) -> float:
        return float(self.time_base * self.pts)
