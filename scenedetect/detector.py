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

"""``scenedetect.detector`` Module

This module contains the :class:`Detector` interface which all detectors must implement (e.g. those
in the :mod:`scenedetect.detectors` module)."""

import typing as ty
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

import numpy

from scenedetect.frame_timecode import FrameTimecode
from scenedetect.stats_manager import StatsManager

# TODO: Documentation.


class EventType(Enum):
    CUT = 0
    FADE_IN = 1
    FADE_OUT = 2


@dataclass
class Event:
    type: EventType
    time: FrameTimecode
    data: ty.Dict[str, ty.Any] = field(default_factory=dict)


class DetectorBase:
    def __init__(self):
        self._stats = None

    @property
    def stats(self) -> ty.Optional[StatsManager]:
        return self._stats

    # For use by SceneManager to register stats handler with this detector.
    def _set_stats_manager(self, stats: StatsManager):
        assert self._stats is None
        self._stats = stats


class Detector(ABC, DetectorBase):
    @abstractmethod
    def process(self, frame: numpy.ndarray, timecode: FrameTimecode) -> ty.List[Event]: ...

    def postprocess(self) -> ty.List[Event]:
        return []
