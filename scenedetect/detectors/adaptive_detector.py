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
""":class:`AdaptiveDetector` compares the difference in content between adjacent frames similar
to `ContentDetector` except the threshold isn't fixed, but is a rolling average of adjacent frame
changes. This can help mitigate false detections in situations such as fast camera motions.

This detector is available from the command-line as the `detect-adaptive` command.
"""

from logging import getLogger
import typing as ty

import numpy as np

from scenedetect.detectors import ContentDetector
from scenedetect.scene_detector import FlashFilter

logger = getLogger('pyscenedetect')


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
        kernel_size: ty.Optional[int] = None,
        flash_filter: ty.Optional[FlashFilter] = None,
        video_manager=None,
        min_delta_hsv: ty.Optional[float] = None,
    ):
        """
        Arguments:
            adaptive_threshold: Threshold (float) that score ratio must exceed to trigger a
                new scene (see frame metric adaptive_ratio in stats file).
            min_scene_len: Defines the minimum length of a given scene. Sequences of consecutive
                cuts that occur closer than this length will be merged. Equivalent to setting
                `flash_filter = FlashFilter(length=min_scene_len)`.
                Ignored if `flash_filter` is set.
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
            flash_filter: Filter to use for scene length compliance. If None, initialized as
                `FlashFilter(length=min_scene_len)`. If set, `min_scene_length` is ignored.
            video_manager: [DEPRECATED] DO NOT USE.
            min_delta_hsv: [DEPRECATED] DO NOT USE.
        """
        # TODO(v0.7): Replace with DeprecationWarning that `video_manager` and `min_delta_hsv` will
        # be removed in v0.8.
        if video_manager is not None:
            logger.error('video_manager is deprecated, use video instead.')
        if min_delta_hsv is not None:
            logger.error('min_delta_hsv is deprecated, use min_content_val instead.')
            min_content_val = min_delta_hsv
        if window_width < 1:
            raise ValueError('window_width must be at least 1.')
        super().__init__(
            threshold=255.0,
            min_scene_len=min_scene_len,
            weights=weights,
            luma_only=luma_only,
            kernel_size=kernel_size,
            flash_filter=flash_filter,
        )
        self._adaptive_threshold = adaptive_threshold
        self._min_content_val = min_content_val
        self._window_width = window_width
        self._adaptive_ratio_key = AdaptiveDetector.ADAPTIVE_RATIO_KEY_TEMPLATE.format(
            window_width=window_width, luma_only='' if not luma_only else '_lum')
        self._buffer = []

    @property
    def event_buffer_length(self) -> int:
        """Number of frames any detected cuts will be behind the current frame due to buffering."""
        return self._window_width

    def get_metrics(self) -> ty.List[str]:
        """Combines base ContentDetector metric keys with the AdaptiveDetector one."""
        return super().get_metrics() + [self._adaptive_ratio_key]

    def stats_manager_required(self) -> bool:
        """Not required for AdaptiveDetector."""
        return False

    def process_frame(self, frame_num: int, frame_img: ty.Optional[np.ndarray]) -> ty.List[int]:
        """Process the next frame. `frame_num` is assumed to be sequential.

        Args:
            frame_num (int): Frame number of frame that is being passed. Can start from any value
                but must remain sequential.
            frame_img (numpy.ndarray or None): Video frame corresponding to `frame_img`.

        Returns:
            List[int]: List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.
        """
        frame_score = self._calculate_frame_score(frame_num=frame_num, frame_img=frame_img)
        required_frames = 1 + (2 * self._window_width)
        self._buffer.append((frame_num, frame_score))
        if not len(self._buffer) >= required_frames:
            return []
        self._buffer = self._buffer[-required_frames:]
        target = self._buffer[self._window_width]
        average_window_score = (
            sum(frame[1] for i, frame in enumerate(self._buffer) if i != self._window_width) /
            (2.0 * self._window_width))
        average_is_zero = abs(average_window_score) < 0.00001
        adaptive_ratio = 0.0
        if not average_is_zero:
            adaptive_ratio = min(target[1] / average_window_score, 255.0)
        elif average_is_zero and target[1] >= self._min_content_val:
            # if we would have divided by zero, set adaptive_ratio to the max (255.0)
            adaptive_ratio = 255.0
        if self.stats_manager is not None:
            self.stats_manager.set_metrics(target[0], {self._adaptive_ratio_key: adaptive_ratio})

        # Check to see if adaptive_ratio exceeds the adaptive_threshold as well as there
        # being a large enough content_val to trigger a cut
        found_cut: bool = (
            adaptive_ratio >= self._adaptive_threshold and target[1] >= self._min_content_val)
        return self._flash_filter.apply(frame_num=target[0], found_cut=found_cut)

    def get_content_val(self, frame_num: int) -> ty.Optional[float]:
        """Returns the average content change for a frame."""
        # TODO(v0.7): Add DeprecationWarning that `get_content_val` will be removed in v0.7.
        logger.error("get_content_val is deprecated and will be removed. Lookup the value"
                     " using a StatsManager with ContentDetector.FRAME_SCORE_KEY.")
        if self.stats_manager is not None:
            return self.stats_manager.get_metrics(frame_num, [ContentDetector.FRAME_SCORE_KEY])[0]
        return 0.0

    def post_process(self, _frame_num: int):
        # Already processed frame at self._window_width, process the rest. This ensures we emit any
        # cuts the filtering mode might require.
        cuts = []
        for (frame_num, _) in self._buffer[self._window_width + 1:]:
            cuts += self._flash_filter.apply(frame_num=frame_num, found_cut=False)
        return cuts
