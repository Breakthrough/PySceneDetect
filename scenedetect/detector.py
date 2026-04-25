#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""``scenedetect.detector`` Module

This module contains the :class:`SceneDetector` interface, from which all scene detectors in
:mod:`scenedetect.detectors` module are derived from.

The SceneDetector class represents the interface which detection algorithms are expected to provide
in order to be compatible with PySceneDetect.

.. warning::

    This API is still unstable, and changes and design improvements are planned for the v1.0
    release. Instead of just timecodes, detection algorithms will also provide a specific type of
    event (in, out, cut, etc...).
"""

import math
from abc import ABC, abstractmethod
from enum import Enum

import numpy

from scenedetect.common import FrameTimecode
from scenedetect.stats_manager import StatsManager


class SceneDetector(ABC):
    """Base class to inherit from when implementing a scene detection algorithm.

    This API is not yet stable and subject to change.
    """

    def __init__(self):
        self._stats_manager: StatsManager | None = None

    # Required Methods

    @abstractmethod
    def process_frame(
        self, timecode: FrameTimecode, frame_img: numpy.ndarray
    ) -> list[FrameTimecode]:
        """Process the next frame. `timecode` is assumed to be sequential.

        Args:
            timecode: Timecode corresponding to the frame being processed.
            frame_img: Video frame as a 24-bit BGR image.

        Returns:
           List of timecodes where scene cuts have been detected, if any.
        """

    # Optional Methods

    def post_process(self, timecode: FrameTimecode) -> list[FrameTimecode]:
        """Called after there are no more frames to process.

        Args:
            timecode: The last position in the video which was read.

        Returns:
           List of timecodes where scene cuts have been detected, if any.
        """
        return []

    @property
    def event_buffer_length(self) -> int:
        """The amount of frames a given event can be buffered for, in time. This must be set to the
        amount of frames a detector might emit an event in the past."""
        return 0

    # Frame Stats/Metrics

    @property
    def stats_manager(self) -> StatsManager | None:
        """Optional :class:`StatsManager <scenedetect.stats_manager.StatsManager>` to use for
        storing frame metrics. When this detector is added to a parent
        :class:`SceneManager <scenedetect.scene_manager.SceneManager>`, then this is set to the
        same :class:`StatsManager <scenedetect.stats_manager.StatsManager>` of the parent - but
        only if it has one itself."""
        return self._stats_manager

    @stats_manager.setter
    def stats_manager(self, value: StatsManager | None):
        self._stats_manager = value

    def get_metrics(self) -> list[str]:
        """Returns a list of all metric names/keys used by this detector.

        Returns:
            List of strings of frame metric key names that will be used by
            the detector when a StatsManager is passed to process_frame.
        """
        return []


class FlashFilter:
    """Filters fast-cuts to enforce minimum scene length."""

    class Mode(Enum):
        """Which mode the filter should use for enforcing minimum scene length."""

        MERGE = 0
        """Merge consecutive cuts shorter than filter length."""
        SUPPRESS = 1
        """Suppress consecutive cuts until the filter length has passed."""

    def __init__(self, mode: Mode, length: int | float | str):
        """
        Arguments:
            mode: The mode to use when enforcing `length`.
            length: Minimum scene length. Accepts an `int` (number of frames), `float` (seconds),
                or `str` (timecode, e.g. ``"0.6s"`` or ``"00:00:00.600"``).
        """
        self._mode = mode
        # Frame count (int) and seconds (float) representations of `length`. Exactly one is
        # populated up front; the other is computed on the first frame once the framerate is
        # known. Temporal inputs (float/non-digit str) populate `_filter_secs`; integer inputs
        # (int/digit str) populate `_filter_length`.
        self._filter_length: int = 0
        self._filter_secs: float | None = None
        if isinstance(length, float):
            self._filter_secs = length
        elif isinstance(length, str) and not length.strip().isdigit():
            self._filter_secs = FrameTimecode(timecode=length, fps=100.0).seconds
        else:
            self._filter_length = int(length)
        self._last_above: FrameTimecode | None = None  # Last frame above threshold.
        self._merge_enabled = False  # Used to disable merging until at least one cut was found.
        self._merge_triggered = False  # True when the merge filter is active.
        self._merge_start: FrameTimecode | None = None  # Frame where we started merging.

    @property
    def max_behind(self) -> int:
        if self._mode == FlashFilter.Mode.SUPPRESS:
            return 0
        if self._filter_secs is not None:
            # Estimate using 240fps so the event buffer is large enough for any reasonable input.
            return math.ceil(self._filter_secs * 240.0)
        return self._filter_length

    @property
    def _is_disabled(self) -> bool:
        if self._filter_secs is not None:
            return self._filter_secs <= 0.0
        return self._filter_length <= 0

    def filter(self, timecode: FrameTimecode, above_threshold: bool) -> list[FrameTimecode]:
        if self._is_disabled:
            return [timecode] if above_threshold else []
        if self._last_above is None:
            self._last_above = timecode
        if self._mode == FlashFilter.Mode.MERGE:
            return self._filter_merge(timecode=timecode, above_threshold=above_threshold)
        elif self._mode == FlashFilter.Mode.SUPPRESS:
            return self._filter_suppress(timecode=timecode, above_threshold=above_threshold)
        raise RuntimeError("Unhandled FlashFilter mode.")

    def _filter_suppress(
        self, timecode: FrameTimecode, above_threshold: bool
    ) -> list[FrameTimecode]:
        framerate = timecode.framerate
        assert framerate is not None and framerate >= 0
        assert self._last_above is not None
        # Compute the threshold in seconds once from the first frame's framerate. This avoids
        # using an incorrect average fps (e.g. OpenCV on VFR video) on subsequent frames.
        if self._filter_secs is None:
            self._filter_secs = self._filter_length / framerate
        min_length_met: bool = (timecode - self._last_above) >= self._filter_secs
        if not (above_threshold and min_length_met):
            return []
        # Both length and threshold requirements were satisfied. Emit the cut, and wait until both
        # requirements are met again.
        self._last_above = timecode
        return [timecode]

    def _filter_merge(self, timecode: FrameTimecode, above_threshold: bool) -> list[FrameTimecode]:
        framerate = timecode.framerate
        assert framerate is not None and framerate >= 0
        assert self._last_above is not None
        # Compute the threshold in seconds once from the first frame's framerate.
        if self._filter_secs is None:
            self._filter_secs = self._filter_length / framerate
        min_length_met: bool = (timecode - self._last_above) >= self._filter_secs
        # Ensure last frame is always advanced to the most recent one that was above the threshold.
        if above_threshold:
            self._last_above = timecode
        if self._merge_triggered:
            # This frame was under the threshold, see if enough frames passed to disable the filter.
            assert self._merge_start is not None
            if (
                min_length_met
                and not above_threshold
                and (self._last_above - self._merge_start) >= self._filter_secs
            ):
                self._merge_triggered = False
                return [self._last_above]
            # Keep merging until enough frames pass below the threshold.
            return []
        # Wait for next frame above the threshold.
        if not above_threshold:
            return []
        # If we met the minimum length requirement, no merging is necessary.
        if min_length_met:
            # Only allow the merge filter once the first cut is emitted.
            self._merge_enabled = True
            return [timecode]
        # Start merging cuts until the length requirement is met.
        if self._merge_enabled:
            self._merge_triggered = True
            self._merge_start = timecode
        return []
