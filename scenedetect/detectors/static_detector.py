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
:class:`StaticDetector` detects frames that contain a significant amount of static/noise,
similar to VHS or coaxial video interference.
"""

import typing as ty

import cv2
import numpy

from scenedetect.common import FrameTimecode
from scenedetect.detector import SceneDetector


class StaticDetector(SceneDetector):
    """Detects frames that contain a significant amount of static/noise, similar to VHS or coaxial video interference.

    A scene cut is triggered if the standard deviation of the luma channel pixel values
    exceeds a certain threshold, indicating a high level of noise.
    """

    FRAME_SCORE_KEY = "static_val"
    """Key in statsfile representing the final frame score."""

    METRIC_KEYS = [FRAME_SCORE_KEY]
    """All statsfile keys this detector produces."""

    def __init__(
        self,
        threshold: float = 20.0,
        min_scene_len: int = 15,
    ):
        """
        Arguments:
            threshold: Minimum standard deviation of the luma channel pixels for a frame
                to be considered "static" or noisy. Higher values mean more noise is required.
            min_scene_len: The minimum number of consecutive frames that must meet the
                static criteria to trigger a scene cut.
        """
        super().__init__()
        self._threshold: float = threshold
        self._min_scene_len: int = min_scene_len
        self._frames_in_static_state: int = 0
        self._last_cut_frame: FrameTimecode | None = None
        self._frame_score: ty.Optional[float] = None

    def get_metrics(self) -> ty.List[str]:
        return StaticDetector.METRIC_KEYS

    def _calculate_frame_score(self, frame_img: numpy.ndarray) -> float:
        """Calculate score representing how 'static' or noisy the frame is."""

        # Convert image to grayscale (luma channel)
        gray_frame = cv2.cvtColor(frame_img, cv2.COLOR_BGR2GRAY)

        # Calculate the standard deviation of the pixel values
        # A higher standard deviation indicates more variance in pixel values,
        # which can be a characteristic of noise.
        frame_score = numpy.std(gray_frame)

        if self.stats_manager is not None:
            # We don't have timecode here, will use current frame_img's frame_num in process_frame
            # to set the metrics.
            pass

        return frame_score

    def process_frame(
        self, timecode: FrameTimecode, frame_img: numpy.ndarray
    ) -> ty.List[FrameTimecode]:
        """Process the next frame. `timecode` is assumed to be sequential."""
        self._frame_score = self._calculate_frame_score(frame_img)

        if self.stats_manager is not None:
            self.stats_manager.set_metrics(
                timecode, {self.FRAME_SCORE_KEY: self._frame_score}
            )

        if self._frame_score is None:
            return []

        is_static = self._frame_score >= self._threshold

        cuts = []
        if is_static:
            self._frames_in_static_state += 1
            if self._frames_in_static_state == self._min_scene_len:
                # If we've just reached min_scene_len, emit a cut at the start of this sequence
                cuts.append(timecode - (self._min_scene_len - 1))
        else:
            self._frames_in_static_state = 0

        self._last_cut_frame = timecode
        return cuts

    def post_process(self, frame_num: int) -> ty.List[FrameTimecode]:
        """Optionally post-process the list of scenes after the last frame has been processed."""
        # If the video ends while in a static state and min_scene_len was met,
        # we might need to add a final cut.
        # This will be handled by the SceneManager.
        return []

    @property
    def event_buffer_length(self) -> int:
        return 0 # No flash filter, so buffer length is 0
