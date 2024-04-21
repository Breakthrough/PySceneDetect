# -*- coding: utf-8 -*-
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
"""``scenedetect.scene_detector`` Module

This module contains the :class:`SceneDetector` interface, from which all scene detectors in
:mod:`scenedetect.detectors` module are derived from.

The SceneDetector class represents the interface which detection algorithms are expected to provide
in order to be compatible with PySceneDetect.

.. warning::

    This API is still unstable, and changes and design improvements are planned for the v1.0
    release. Instead of just timecodes, detection algorithms will also provide a specific type of
    event (in, out, cut, etc...).
"""

from enum import Enum
import typing as ty

import numpy

from scenedetect.stats_manager import StatsManager


# pylint: disable=unused-argument, no-self-use
class SceneDetector:
    """ Base class to inherit from when implementing a scene detection algorithm.

    This API is not yet stable and subject to change.

    This represents a "dense" scene detector, which returns a list of frames where
    the next scene/shot begins in a video.

    Also see the implemented scene detectors in the scenedetect.detectors module
    to get an idea of how a particular detector can be created.
    """
    # TODO(v0.7): Make this a proper abstract base class.

    stats_manager: ty.Optional[StatsManager] = None
    """Optional :class:`StatsManager <scenedetect.stats_manager.StatsManager>` to
    use for caching frame metrics to and from."""

    def get_metrics(self) -> ty.List[str]:
        """Get Metrics:  Get a list of all metric names/keys used by the detector.

        Returns:
            List of strings of frame metric key names that will be used by
            the detector when a StatsManager is passed to process_frame.
        """
        return []

    def process_frame(self, frame_num: int, frame_img: numpy.ndarray) -> ty.List[int]:
        """Process the next frame. `frame_num` is assumed to be sequential.

        Args:
            frame_num (int): Frame number of frame that is being passed. Can start from any value
                but must remain sequential.
            frame_img (numpy.ndarray or None): Video frame corresponding to `frame_img`.

        Returns:
            List[int]: List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.

        Returns:
            List of frame numbers of cuts to be added to the cutting list.
        """
        return []

    def post_process(self, frame_num: int) -> ty.List[int]:
        """Post Process: Performs any processing after the last frame has been read.

        Prototype method, no actual detection.

        Returns:
            List of frame numbers of cuts to be added to the cutting list.
        """
        return []

    @property
    def event_buffer_length(self) -> int:
        """The amount of frames a given event can be buffered for, in time. Represents maximum
        amount any event can be behind `frame_number` in the result of :meth:`process_frame`.
        """
        return 0

    # DEPRECATED - TO BE REMOVED

    def is_processing_required(self, frame_num: int) -> bool:
        """[DEPRECATED] DO NOT USE"""
        metric_keys = self.get_metrics()
        return not metric_keys or not (self.stats_manager is not None
                                       and self.stats_manager.metrics_exist(frame_num, metric_keys))

    def stats_manager_required(self) -> bool:
        """[DEPRECATED] DO NOT USE"""
        return False


class SparseSceneDetector(SceneDetector):
    """[DEPRECATED] DO NOT USE"""

    def process_frame(self, frame_num: int,
                      frame_img: numpy.ndarray) -> ty.List[ty.Tuple[int, int]]:
        """Process Frame: Computes/stores metrics and detects any scene changes.

        Prototype method, no actual detection.

        Returns:
            List of frame pairs representing individual scenes
            to be added to the output scene list directly.
        """
        return []

    def post_process(self, frame_num: int) -> ty.List[ty.Tuple[int, int]]:
        """Post Process: Performs any processing after the last frame has been read.

        Prototype method, no actual detection.

        Returns:
            List of frame pairs representing individual scenes
            to be added to the output scene list directly.
        """
        return []


class FlashFilter:
    """Online filter used by detection algorithms to filter scene cuts which occur too close
    together (less than `length` frames apart)."""

    class Mode(Enum):
        """Mode specifying how the filter operates when active."""
        MERGE = 0
        """Merge consecutive cuts shorter than filter length (default)."""
        SUPPRESS = 1
        """Suppress consecutive cuts until the filter length has passed."""

    def __init__(self, length: int, mode: Mode = Mode.MERGE):
        """
        Arguments:
            length: Number of frames defining how close cuts can be before the filter is activated.
            mode: How the filter operates when active.
        """
        self._mode = mode
        self._filter_length = length  # Number of frames to use for activating the filter.
        self._last_above = None       # Last frame above threshold.
        self._merge_enabled = False   # Used to disable merging until at least one cut was found.
        self._merge_triggered = False # True when the merge filter is active.
        self._merge_start = None      # Frame number where we started the merge filter.

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        if self._filter_length <= 0:
            return "FlashFilter(length=0 [DISABLED])"
        return f"FlashFilter(mode={str(self._mode)}, length={self._filter_length})"

    def apply(self, frame_num: int, found_cut: bool) -> ty.List[int]:
        if self._filter_length <= 0:
            return [frame_num] if found_cut else []
        if self._last_above is None:
            self._last_above = frame_num
        if self._mode == FlashFilter.Mode.MERGE:
            return self._filter_merge(frame_num=frame_num, found_cut=found_cut)
        if self._mode == FlashFilter.Mode.SUPPRESS:
            return self._filter_suppress(frame_num=frame_num, found_cut=found_cut)

    def _filter_suppress(self, frame_num: int, found_cut: bool) -> ty.List[int]:
        min_length_met: bool = (frame_num - self._last_above) >= self._filter_length
        if not (found_cut and min_length_met):
            return []
        # Only advance last frame when the length requirement is satisfied.
        self._last_above = frame_num
        return [frame_num]

    def _filter_merge(self, frame_num: int, found_cut: bool) -> ty.List[int]:
        min_length_met: bool = (frame_num - self._last_above) >= self._filter_length
        # Ensure last frame is always advanced to the most recent one that was above the threshold.
        if found_cut:
            self._last_above = frame_num
        if self._merge_triggered:
            # This frame was under the threshold, see if enough frames passed to disable the filter.
            num_merged_frames = self._last_above - self._merge_start
            if min_length_met and not found_cut and num_merged_frames >= self._filter_length:
                self._merge_triggered = False
                return [self._last_above]
            # Keep merging until enough frames pass below the threshold.
            return []
        # Wait for next frame above the threshold.
        if not found_cut:
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
