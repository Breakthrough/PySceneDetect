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
"""
:class:`ColorDetector` detects when a frame is mostly a single color,
e.g. a transition to a solid blue or any other color, emitting a new scene cut event.
"""

import typing as ty
from collections import deque

import cv2
import numpy

from scenedetect.common import FrameTimecode
from scenedetect.detector import SceneDetector


class ColorDetector(SceneDetector):
    """Detects frames that are mostly a single color, with consistent color across subsequent frames.

    A scene cut is triggered if:
    1. The standard deviation of all color channels (HSV) falls below a certain threshold.
    2. A minimum percentage of pixels match the dominant color.
    3. The dominant color remains consistent across `min_scene_len` consecutive frames,
       within a specified `color_tolerance`.
    """

    FRAME_SCORE_KEY = "color_val"
    """Key in statsfile representing the final frame score."""

    METRIC_KEYS = [FRAME_SCORE_KEY]
    """All statsfile keys this detector produces."""

    def __init__(
        self,
        threshold: float = 10.0,
        min_percentage: float = 0.95,
        min_scene_len: int = 15,
        color_tolerance: float = 20.0,
    ):
        """
        Arguments:
            threshold: Maximum allowed standard deviation across all HSV channels for a frame
                to be considered a single color. Lower values mean stricter detection.
            min_percentage: Minimum percentage of pixels that must be within the dominant
                color range for a frame to be considered a single color.
            min_scene_len: The minimum number of consecutive frames that must meet the
                single color and color consistency criteria to trigger a scene cut.
            color_tolerance: The maximum Euclidean distance between the mean HSV values of
                the current frame and the rolling average of previous single-color frames
                to consider the color consistent.
        """
        super().__init__()
        self._threshold: float = threshold
        self._min_percentage: float = min_percentage
        self._min_scene_len: int = min_scene_len
        self._color_tolerance: float = color_tolerance
        self._frames_in_color_state: int = 0
        self._last_cut_frame: FrameTimecode | None = None
        self._frame_score: ty.Optional[float] = None
        self._color_history: deque[numpy.ndarray] = deque(maxlen=min_scene_len)

    def get_metrics(self) -> ty.List[str]:
        return ColorDetector.METRIC_KEYS

    def _calculate_frame_score(self, frame_img: numpy.ndarray) -> ty.Tuple[float, numpy.ndarray]:
        """Calculate score representing how 'single-colored' the frame is, and its mean HSV."""

        # Convert image into HSV colorspace.
        hsv = cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV)

        # Calculate standard deviation for each channel
        h_std = numpy.std(hsv[:, :, 0])
        s_std = numpy.std(hsv[:, :, 1])
        v_std = numpy.std(hsv[:, :, 2])

        # The frame score can be the maximum standard deviation of the channels.
        # A lower score indicates a more uniform color.
        frame_score = max(h_std, s_std, v_std)

        # Calculate mean HSV for color consistency check
        mean_hsv = numpy.mean(hsv.reshape(-1, 3), axis=0)

        return frame_score, mean_hsv

    def process_frame(
        self, timecode: FrameTimecode, frame_img: numpy.ndarray
    ) -> ty.List[FrameTimecode]:
        """Process the next frame. `timecode` is assumed to be sequential."""
        self._frame_score, current_mean_hsv = self._calculate_frame_score(frame_img)

        if self.stats_manager is not None:
            self.stats_manager.set_metrics(
                timecode, {self.FRAME_SCORE_KEY: self._frame_score}
            )

        cuts = []
        is_single_color_candidate = False
        if self._frame_score <= self._threshold:
            # Check if a significant percentage of pixels are within a narrow color range
            hsv = cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV)
            # Flatten the HSV image to easily count pixel values
            flat_hsv = hsv.reshape(-1, 3)

            # Define a tolerance for each channel (e.g., 10 for H, 20 for S, 20 for V)
            h_tolerance = 10
            s_tolerance = 20
            v_tolerance = 20

            # Count pixels within the tolerance range of the mean HSV
            pixels_in_range = numpy.sum(
                (flat_hsv[:, 0] >= current_mean_hsv[0] - h_tolerance) &
                (flat_hsv[:, 0] <= current_mean_hsv[0] + h_tolerance) &
                (flat_hsv[:, 1] >= current_mean_hsv[1] - s_tolerance) &
                (flat_hsv[:, 1] <= current_mean_hsv[1] + s_tolerance) &
                (flat_hsv[:, 2] >= current_mean_hsv[2] - v_tolerance) &
                (flat_hsv[:, 2] <= current_mean_hsv[2] + v_tolerance)
            )
            percentage_in_range = pixels_in_range / flat_hsv.shape[0]

            if percentage_in_range >= self._min_percentage:
                is_single_color_candidate = True

        if is_single_color_candidate:
            if not self._color_history or self._is_color_consistent(current_mean_hsv):
                self._color_history.append(current_mean_hsv)
                self._frames_in_color_state += 1
                if self._frames_in_color_state == self._min_scene_len:
                    # Emit a cut at the start of this sequence
                    cuts.append(timecode - (self._min_scene_len - 1))
            else:
                # Color changed too much, reset sequence
                self._frames_in_color_state = 0
                self._color_history.clear()
        else:
            # Not a single color candidate, reset sequence
            self._frames_in_color_state = 0
            self._color_history.clear()
        
        self._last_cut_frame = timecode
        return cuts

    def _is_color_consistent(self, current_mean_hsv: numpy.ndarray) -> bool:
        """Checks if the current frame's dominant color is consistent with the history."""
        if not self._color_history:
            return True  # No history yet, so it's consistent by default

        # Calculate the mean of the colors in history
        history_mean_hsv = numpy.mean(list(self._color_history), axis=0)

        # Calculate Euclidean distance between current mean HSV and history mean HSV
        distance = numpy.linalg.norm(current_mean_hsv - history_mean_hsv)
        return distance <= self._color_tolerance

    def post_process(self, frame_num: int) -> ty.List[FrameTimecode]:
        """Optionally post-process the list of scenes after the last frame has been processed."""
        return []

    @property
    def event_buffer_length(self) -> int:
        return 0 # No flash filter, so buffer length is 0
