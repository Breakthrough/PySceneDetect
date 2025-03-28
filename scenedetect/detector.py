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

import typing as ty
from enum import Enum

import numpy

from scenedetect.common import _USE_PTS_IN_DEVELOPMENT, FrameTimecode
from scenedetect.stats_manager import StatsManager


class SceneDetector:
    """Base class to inherit from when implementing a scene detection algorithm.

    This API is not yet stable and subject to change.
    """

    # TODO(v0.7): Make this a proper abstract base class.

    # TODO(v0.7): This should be a property.
    stats_manager: ty.Optional[StatsManager] = None
    """Optional :class:`StatsManager <scenedetect.stats_manager.StatsManager>` to
    use for caching frame metrics to and from."""

    def stats_manager_required(self) -> bool:
        """Stats Manager Required: Prototype indicating if detector requires stats.

        Returns:
            True if a StatsManager is required for the detector, False otherwise.
        """
        return False

    def get_metrics(self) -> ty.List[str]:
        """Returns a list of all metric names/keys used by this detector.

        Returns:
            List of strings of frame metric key names that will be used by
            the detector when a StatsManager is passed to process_frame.
        """
        return []

    def process_frame(
        self, timecode: FrameTimecode, frame_img: numpy.ndarray
    ) -> ty.List[FrameTimecode]:
        """Process the next frame. `frame_num` is assumed to be sequential.

        Args:
            timecode: Timecode corresponding to the frame being processed.
            frame_img: Video frame as a 24-bit BGR image.

        Returns:
           List of timecodes where scene cuts have been detected, if any.
        """
        return []

    def post_process(self, timecode: int) -> ty.List[FrameTimecode]:
        """Called after there are no more frames to process.

        Args:
            timecode: The last position in the video which was read.

        Returns:
           List of timecodes where scene cuts have been detected, if any.
        """
        return []

    @property
    def event_buffer_length(self) -> int:
        """The amount of frames a given event can be buffered for, in time. Represents maximum
        amount any event can be behind `frame_number` in the result of :meth:`process_frame`.
        """
        return 0


class FlashFilter:
    """Filters fast-cuts to enforce minimum scene length."""

    class Mode(Enum):
        """Which mode the filter should use for enforcing minimum scene length."""

        MERGE = 0
        """Merge consecutive cuts shorter than filter length."""
        SUPPRESS = 1
        """Suppress consecutive cuts until the filter length has passed."""

    def __init__(self, mode: Mode, length: int):
        """
        Arguments:
            mode: The mode to use when enforcing `length`.
            length: Number of frames to use when filtering cuts.
        """
        self._mode = mode
        self._filter_length = length  # Number of frames to use for activating the filter.
        self._last_above = None  # Last frame above threshold.
        self._merge_enabled = False  # Used to disable merging until at least one cut was found.
        self._merge_triggered = False  # True when the merge filter is active.
        self._merge_start = None  # Frame number where we started the merge filter.

    @property
    def max_behind(self) -> int:
        return 0 if self._mode == FlashFilter.Mode.SUPPRESS else self._filter_length

    def filter(self, timecode: FrameTimecode, above_threshold: bool) -> ty.List[FrameTimecode]:
        if not self._filter_length > 0:
            return [timecode] if above_threshold else []
        if _USE_PTS_IN_DEVELOPMENT:
            raise NotImplementedError("TODO: Change filter to use units of time instead of frames.")
        if self._last_above is None:
            self._last_above = timecode
        if self._mode == FlashFilter.Mode.MERGE:
            return self._filter_merge(frame_num=timecode, above_threshold=above_threshold)
        elif self._mode == FlashFilter.Mode.SUPPRESS:
            return self._filter_suppress(frame_num=timecode, above_threshold=above_threshold)
        raise RuntimeError("Unhandled FlashFilter mode.")

    def _filter_suppress(self, frame_num: int, above_threshold: bool) -> ty.List[int]:
        min_length_met: bool = (frame_num - self._last_above) >= self._filter_length
        if not (above_threshold and min_length_met):
            return []
        # Both length and threshold requirements were satisfied. Emit the cut, and wait until both
        # requirements are met again.
        self._last_above = frame_num
        return [frame_num]

    def _filter_merge(self, frame_num: int, above_threshold: bool) -> ty.List[int]:
        min_length_met: bool = (frame_num - self._last_above) >= self._filter_length
        # Ensure last frame is always advanced to the most recent one that was above the threshold.
        if above_threshold:
            self._last_above = frame_num
        if self._merge_triggered:
            # This frame was under the threshold, see if enough frames passed to disable the filter.
            num_merged_frames = self._last_above - self._merge_start
            if min_length_met and not above_threshold and num_merged_frames >= self._filter_length:
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
            return [frame_num]
        # Start merging cuts until the length requirement is met.
        if self._merge_enabled:
            self._merge_triggered = True
            self._merge_start = frame_num
        return []
