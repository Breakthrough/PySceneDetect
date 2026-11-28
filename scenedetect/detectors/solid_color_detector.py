#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Observe intervals of spatially uniform frames without emitting scene cuts."""

from numbers import Integral, Real

import cv2
import numpy

from scenedetect.common import FrameTimecode
from scenedetect.detector import SceneDetector


class SolidColorDetector(SceneDetector):
    """Collect intervals in which every frame is approximately a solid color.

    Each BGR channel's spatial standard deviation is calculated independently. A frame is solid
    when the largest deviation is at most ``threshold``; the color itself can change between
    frames within an interval. This detector never emits scene cuts, so it can observe the same
    frames as another detector attached to a :class:`~scenedetect.scene_manager.SceneManager`.
    Retrieve completed intervals with :meth:`get_intervals` after processing finishes.
    """

    def __init__(self, threshold: float = 2.0, min_frames: int = 2):
        """
        Arguments:
            threshold: Maximum spatial standard deviation allowed in each 8-bit BGR channel,
                inclusive. Must be finite and between 0 and 127.5. Zero requires exact uniformity.
            min_frames: Minimum number of observed solid frames required for an interval. Must
                be a positive integer. Counts processed frames, even when frame skipping is used.

        Raises:
            ValueError: An argument is outside its allowed range or has an invalid type.
        """
        super().__init__()
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, Real)
            or not 0 <= threshold <= 127.5
        ):
            raise ValueError("threshold must be a finite number between 0 and 127.5.")
        if isinstance(min_frames, bool) or not isinstance(min_frames, Integral) or min_frames < 1:
            raise ValueError("min_frames must be a positive integer.")
        self._threshold = float(threshold)
        self._min_frames = int(min_frames)
        self._intervals: list[tuple[FrameTimecode, FrameTimecode]] = []
        self._start: FrameTimecode | None = None
        self._last_solid: FrameTimecode | None = None
        self._solid_frames = 0

    def process_frame(
        self, timecode: FrameTimecode, frame_img: numpy.ndarray
    ) -> list[FrameTimecode]:
        """Observe a sequential BGR frame.

        Arguments:
            timecode: Timecode corresponding to the frame being processed.
            frame_img: Video frame as a 24-bit BGR image.

        Returns:
            An empty list; this detector never emits scene cuts.
        """
        if self._threshold == 0.0:
            # meanStdDev can report tiny nonzero deviations for exactly uniform images.
            is_solid = bool((frame_img == frame_img[0, 0]).all())
        else:
            _, deviation = cv2.meanStdDev(frame_img)
            is_solid = float(deviation.max()) <= self._threshold
        if is_solid:
            if self._start is None:
                self._start = FrameTimecode(timecode)
            self._last_solid = FrameTimecode(timecode)
            self._solid_frames += 1
        else:
            self._finish_interval(timecode)
        return []

    def post_process(self, timecode: FrameTimecode) -> list[FrameTimecode]:
        """Close a trailing interval one frame after the last processed frame.

        Arguments:
            timecode: Timecode of the last frame processed.

        Returns:
            An empty list; this detector never emits scene cuts.
        """
        # If detection stops early, the decoder can be ahead of the last observed frame.
        if self._last_solid is not None:
            self._finish_interval(self._last_solid + 1)
        return []

    def get_intervals(self) -> list[tuple[FrameTimecode, FrameTimecode]]:
        """Return completed intervals in chronological order as ``(start, exclusive_end)`` pairs.

        A pending trailing interval is included only after :meth:`post_process` is called.
        Returned lists and timecodes can be modified without changing detector state.

        Returns:
            Completed ``(start, exclusive_end)`` timecode pairs in chronological order.
        """
        return [(FrameTimecode(start), FrameTimecode(end)) for start, end in self._intervals]

    def _finish_interval(self, end: FrameTimecode) -> None:
        if self._start is not None and self._solid_frames >= self._min_frames:
            self._intervals.append((self._start, FrameTimecode(end)))
        self._start = None
        self._last_solid = None
        self._solid_frames = 0
