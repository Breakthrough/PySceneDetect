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
"""``scenedetect.common`` Module

This module contains common types and functions used throughout PySceneDetect."""

import typing as ty
from dataclasses import dataclass
from fractions import Fraction

# TODO(v0.7): We should move frame_timecode into this file.
from scenedetect.frame_timecode import FrameTimecode

##
## Type Aliases
##

SceneList = ty.List[ty.Tuple[FrameTimecode, FrameTimecode]]
"""Type hint for a list of scenes in the form (start time, end time)."""

CutList = ty.List[FrameTimecode]
"""Type hint for a list of cuts, where each timecode represents the first frame of a new shot."""

CropRegion = ty.Tuple[int, int, int, int]
"""Type hint for rectangle of the form X0 Y0 X1 Y1 for cropping frames. Coordinates are relative
to source frame without downscaling.
"""

TimecodePair = ty.Tuple[FrameTimecode, FrameTimecode]
"""Named type for pairs of timecodes, which typically represents the start/end of a scene."""


# TODO(@Breakthrough): Figure out interop with FrameTimecode. We can probably just store this inside
# of FrameTimecode.
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
