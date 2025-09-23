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

import typing as ty
from logging import getLogger

import numpy as np

from scenedetect.common import FrameTimecode
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
        kernel_size: ty.Optional[int] = None,
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
        """
        if window_width < 1:
            raise ValueError("window_width must be at least 1.")

        super().__init__(
            threshold=255.0,
            min_scene_len=0,
            weights=weights,
            luma_only=luma_only,
            kernel_size=kernel_size,
        )

        # TODO: Turn these public options into properties.
        self.min_scene_len = min_scene_len
        self.adaptive_threshold = adaptive_threshold
        self.min_content_val = min_content_val
        self.window_width = window_width

        self._adaptive_ratio_key = AdaptiveDetector.ADAPTIVE_RATIO_KEY_TEMPLATE.format(
            window_width=window_width, luma_only="" if not luma_only else "_lum"
        )
        self._buffer: ty.List[ty.Tuple[FrameTimecode, float]] = []
        # NOTE: The name of last cut is different from `self._last_scene_cut` from our base class,
        # and serves a different purpose!
        self._last_cut: ty.Optional[FrameTimecode] = None

    @property
    def event_buffer_length(self) -> int:
        return self.window_width

    def get_metrics(self) -> ty.List[str]:
        return super().get_metrics() + [self._adaptive_ratio_key]

    def process_frame(
        self, timecode: FrameTimecode, frame_img: np.ndarray
    ) -> ty.List[FrameTimecode]:
        super().process_frame(timecode=timecode, frame_img=frame_img)

        # Initialize last scene cut point at the beginning of the frames of interest.
        if self._last_cut is None:
            self._last_cut = timecode

        required_frames = 1 + (2 * self.window_width)
        self._buffer.append((timecode, self._frame_score))
        if not len(self._buffer) >= required_frames:
            return []
        self._buffer = self._buffer[-required_frames:]
        (target_timecode, target_score) = self._buffer[self.window_width]
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
            self.stats_manager.set_metrics(
                target_timecode, {self._adaptive_ratio_key: adaptive_ratio}
            )

        # Check to see if adaptive_ratio exceeds the adaptive_threshold as well as there
        # being a large enough content_val to trigger a cut
        threshold_met: bool = (
            adaptive_ratio >= self.adaptive_threshold and target_score >= self.min_content_val
        )
        min_length_met: bool = (timecode - self._last_cut) >= self.min_scene_len
        if threshold_met and min_length_met:
            self._last_cut = target_timecode
            return [target_timecode]
        return []
