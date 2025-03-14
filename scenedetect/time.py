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
from fractions import Fraction

# How to land this:
#   1. Figure out how to get correct timing into VideoStream.
#   2. Integrate with Detectors + SceneManager.
#   3. Handle user input for start/end time, min scene length, etc.
#


@dataclass
class Frames:
    """Duration represented as frames."""

    value: int


@dataclass
class Seconds:
    """Duration represented as seconds."""

    value: float


@dataclass
class Time:
    """Time at which a given frame should be displayed."""

    frame: Frames
    """Frame number. The first frame is frame 0."""
    time_base: Fraction
    """Base unit of time to use."""
    presentation_time: int
    """Presentation time in terms of `time_base`."""

    @property
    def time(self) -> Fraction:
        """Time in seconds as a fraction."""
        numerator, denominator = self.time_base.as_integer_ratio()
        return Fraction(numerator=(numerator * self.presentation_time), denominator=denominator)

    @property
    def seconds(self) -> Seconds:
        """Time in seconds as a float."""
        return Seconds(value=float(self.time))
