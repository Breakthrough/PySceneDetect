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
""":class:`AdaptiveDetector` compares the difference in content between adjacent frames similar
to `ContentDetector` except the threshold isn't fixed, but is a rolling average of adjacent frame
changes. This can help mitigate false detections in situations such as fast camera motions.

This detector is available from the command-line as the `detect-adaptive` command.
"""

from logging import getLogger
from typing import List, Optional

import numpy as np

from scenedetect.detectors import ContentDetector

logger = getLogger("pyscenedetect")


class AdaptiveDetector(ContentDetector):
    """Two-pass detector that calculates frame scores with ContentDetector, and then applies
    a rolling average when processing the result that can help mitigate false detections
    in situations such as camera movement.
    """

    ADAPTIVE_RATIO_KEY_TEMPLATE = "adaptive_ratio{luma_only} (w={window_width})"

    def __init__(
        self,
        adaptive_threshold: float = 3.0,
        min_scene_len: int = 15,
        window_width: int = 2,
        min_content_val: float = 15.0,
        weights: ContentDetector.Components = ContentDetector.DEFAULT_COMPONENT_WEIGHTS,
        luma_only: bool = False,
        kernel_size: Optional[int] = None,
        video_manager=None,
        min_delta_hsv: Optional[float] = None,
    ):
        """
        Arguments:
            adaptive_threshold: Threshold (float) that score ratio must exceed to trigger a
                new scene (see frame metric adaptive_ratio in stats file).
            min_scene_len: Once a cut is detected, this many frames must pass before a new one can
                be added to the scene list. Can be an int or FrameTimecode type.
            window_width: Size of window (number of frames) before and after each frame to
                average together in order to detect deviations from the mean. Must be at least 1.
            min_content_val: Minimum threshold (float) that the content_val must exceed in order to
                register as a new scene. This is calculated the same way that `detect-content`
                calculates frame score based on `weights`/`luma_only`/`kernel_size`.
            weights: Weight to place on each component when calculating frame score
                (`content_val` in a statsfile, the value `threshold` is compared against).
                If omitted, the default ContentDetector weights are used.
            luma_only: If True, only considers changes in the luminance channel of the video.
                Equivalent to specifying `weights` as :data:`ContentDetector.LUMA_ONLY`.
                Overrides `weights` if both are set.
            kernel_size: Size of kernel to use for post edge detection filtering. If None,
                automatically set based on video resolution.
            video_manager: [DEPRECATED] DO NOT USE. For backwards compatibility only.
            min_delta_hsv: [DEPRECATED] DO NOT USE. Use `min_content_val` instead.
        """
        # TODO(v0.7): Replace with DeprecationWarning that `video_manager` and `min_delta_hsv` will
        # be removed in v0.8.
        if video_manager is not None:
            logger.error("video_manager is deprecated, use video instead.")
        if min_delta_hsv is not None:
            logger.error("min_delta_hsv is deprecated, use min_content_val instead.")
            min_content_val = min_delta_hsv
        if window_width < 1:
            raise ValueError("window_width must be at least 1.")

        super().__init__(
            threshold=255.0,
            min_scene_len=0,
            weights=weights,
            luma_only=luma_only,
            kernel_size=kernel_size,
        )

        # TODO: Turn these options into properties.
        self.min_scene_len = min_scene_len
        self.adaptive_threshold = adaptive_threshold
        self.min_content_val = min_content_val
        self.window_width = window_width

        self._adaptive_ratio_key = AdaptiveDetector.ADAPTIVE_RATIO_KEY_TEMPLATE.format(
            window_width=window_width, luma_only="" if not luma_only else "_lum"
        )
        self._first_frame_num = None

        # NOTE: This must be different than `self._last_scene_cut` which is used by the base class.
        self._last_cut: Optional[int] = None

        self._buffer = []

    @property
    def event_buffer_length(self) -> int:
        """Number of frames any detected cuts will be behind the current frame due to buffering."""
        return self.window_width

    def get_metrics(self) -> List[str]:
        """Combines base ContentDetector metric keys with the AdaptiveDetector one."""
        return super().get_metrics() + [self._adaptive_ratio_key]

    def stats_manager_required(self) -> bool:
        """Not required for AdaptiveDetector."""
        return False

    def process_frame(self, frame_num: int, frame_img: Optional[np.ndarray]) -> List[int]:
        """Process the next frame. `frame_num` is assumed to be sequential.

        Args:
            frame_num (int): Frame number of frame that is being passed. Can start from any value
                but must remain sequential.
            frame_img (numpy.ndarray or None): Video frame corresponding to `frame_img`.

        Returns:
            List[int]: List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.
        """

        # TODO(#283): Merge this with ContentDetector and turn it on by default.

        super().process_frame(frame_num=frame_num, frame_img=frame_img)

        # Initialize last scene cut point at the beginning of the frames of interest.
        if self._last_cut is None:
            self._last_cut = frame_num

        required_frames = 1 + (2 * self.window_width)
        self._buffer.append((frame_num, self._frame_score))
        if not len(self._buffer) >= required_frames:
            return []
        self._buffer = self._buffer[-required_frames:]
        (target_frame, target_score) = self._buffer[self.window_width]
        average_window_score = sum(
            score for i, (_frame, score) in enumerate(self._buffer) if i != self.window_width
        ) / (2.0 * self.window_width)

        average_is_zero = abs(average_window_score) < 0.00001

        adaptive_ratio = 0.0
        if not average_is_zero:
            adaptive_ratio = min(target_score / average_window_score, 255.0)
        elif average_is_zero and target_score >= self.min_content_val:
            # if we would have divided by zero, set adaptive_ratio to the max (255.0)
            adaptive_ratio = 255.0
        if self.stats_manager is not None:
            self.stats_manager.set_metrics(target_frame, {self._adaptive_ratio_key: adaptive_ratio})

        # Check to see if adaptive_ratio exceeds the adaptive_threshold as well as there
        # being a large enough content_val to trigger a cut
        threshold_met: bool = (
            adaptive_ratio >= self.adaptive_threshold and target_score >= self.min_content_val
        )
        min_length_met: bool = (frame_num - self._last_cut) >= self.min_scene_len
        if threshold_met and min_length_met:
            self._last_cut = target_frame
            return [target_frame]
        return []

    def get_content_val(self, frame_num: int) -> Optional[float]:
        """Returns the average content change for a frame."""
        # TODO(v0.7): Add DeprecationWarning that `get_content_val` will be removed in v0.7.
        logger.error(
            "get_content_val is deprecated and will be removed. Lookup the value"
            " using a StatsManager with ContentDetector.FRAME_SCORE_KEY."
        )
        if self.stats_manager is not None:
            return self.stats_manager.get_metrics(frame_num, [ContentDetector.FRAME_SCORE_KEY])[0]
        return 0.0

    def post_process(self, _unused_frame_num: int):
        """Not required for AdaptiveDetector."""
        return []
