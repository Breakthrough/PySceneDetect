# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""":py:class:`AdaptiveDetector` compares the difference in content between adjacent frames similar
to `ContentDetector` except the threshold isn't fixed, but is a rolling average of adjacent frame
changes. This can help mitigate false detections in situations such as fast camera motions.

This detector is available from the command-line as the `detect-adaptive` command.
"""

from logging import getLogger
from typing import List, Optional

from numpy import ndarray

from scenedetect.detectors import ContentDetector

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
        kernel_size: Optional[int] = None,
        video_manager=None,
        min_delta_hsv: Optional[float] = None,
    ):
        """
        Arguments:
            adaptive_threshold: Threshold value (float) that the calculated frame score must exceed to
                trigger a new scene (see frame metric adaptive_ratio in stats file).
            min_scene_len: Minimum length of any scene.
            window_width: Size of window (number of frames) before and after each frame to average together in'
                order to detect deviations from the mean.
            min_content_val: Minimum threshold (float) that the content_val must exceed in order to
                register as a new scene. This is calculated the same way that `detect-content`
                calculates frame score based on `weights`/`luma_only`/`kernel_size`.
            weights: Weight to place on each component when calculating frame score
                (`content_val` in a statsfile, the value `threshold` is compared against).
                If omitted, the default ContentDetector weights are used.
            luma_only: If True, only considers changes in the luminance channel of the video.
                Equivalent to specifying `weights` as :py:data:`ContentDetector.LUMA_ONLY`.
                Overrides `weights` if both are set.
            kernel_size: Size of kernel to use for post edge detection filtering. If None,
                automatically set based on video resolution.
            video_manager: [DEPRECATED] DO NOT USE. For backwards compatibility only.
            min_delta_hsv: [DEPRECATED] DO NOT USE. Use `min_content_val` instead.
        """
        # TODO(v0.7): Replace with DeprecationWarning that `video_manager` and `min_delta_hsv` will
        # be removed in v0.8.
        if video_manager is not None:
            logger.error('video_manager is deprecated, use video instead.')
        if min_delta_hsv is not None:
            logger.error('min_delta_hsv is deprecated, use min_content_val instead.')
            min_content_val = min_delta_hsv

        super().__init__(
            threshold=255.0,
            min_scene_len=0,
            weights=weights,
            luma_only=luma_only,
            kernel_size=kernel_size,
        )

        # TODO: Make all properties private.
        self.min_scene_len = min_scene_len
        self.adaptive_threshold = adaptive_threshold
        self.min_content_val = min_content_val
        self.window_width = window_width
        self._adaptive_ratio_key = AdaptiveDetector.ADAPTIVE_RATIO_KEY_TEMPLATE.format(
            window_width=window_width, luma_only='' if not luma_only else '_lum')
        self._first_frame_num = None
        self._last_frame_num = None

    def get_metrics(self) -> List[str]:
        """ Combines base ContentDetector metric keys with the AdaptiveDetector one. """
        return super().get_metrics() + [self._adaptive_ratio_key]

    def stats_manager_required(self) -> bool:
        """ Overload to indicate that this detector requires a StatsManager.

        Returns:
            True as AdaptiveDetector requires stats.
        """
        return True

    def process_frame(self, frame_num: int, frame_img: Optional[ndarray]) -> List[int]:
        """ Similar to ThresholdDetector, but using the HSV colour space DIFFERENCE instead
        of single-frame RGB/grayscale intensity (thus cannot detect slow fades with this method).

        Arguments:
            frame_num: Frame number of frame that is being passed.

            frame_img: Decoded frame image (numpy.ndarray) to perform scene
                detection on. Can be None *only* if the self.is_processing_required() method
                (inhereted from the base SceneDetector class) returns True.

        Returns:
            Empty list
        """

        # Call the process_frame function of ContentDetector but ignore any
        # returned cuts
        if self.is_processing_required(frame_num):
            super().process_frame(frame_num=frame_num, frame_img=frame_img)

        if self._first_frame_num is None:
            self._first_frame_num = frame_num
        self._last_frame_num = frame_num

        return []

    def get_content_val(self, frame_num: int) -> float:
        """
        Returns the average content change for a frame.
        """
        return self.stats_manager.get_metrics(frame_num, [ContentDetector.FRAME_SCORE_KEY])[0]

    def post_process(self, _unused_frame_num: int):
        """
        After an initial run through the video to detect content change
        between each frame, we try to identify fast cuts as short peaks in the
        `content_val` value. If a single frame has a high `content-val` while
        the frames around it are low, we can be sure it's fast cut. If several
        frames in a row have high `content-val`, it probably isn't a cut -- it
        could be fast camera movement or a change in lighting that lasts for
        more than a single frame.
        """
        cut_list = []
        if self._first_frame_num is None:
            return []
        adaptive_threshold = self.adaptive_threshold
        window_width = self.window_width
        last_cut = None

        assert self.stats_manager is not None

        if self.stats_manager is not None:
            # Loop through the stats, building the adaptive_ratio metric
            for frame_num in range(self._first_frame_num + window_width + 1,
                                   self._last_frame_num - window_width):
                # If the content-val of the frame is more than
                # adaptive_threshold times the mean content_val of the
                # frames around it, then we mark it as a cut.
                denominator = 0
                for offset in range(-window_width, window_width + 1):
                    if offset == 0:
                        continue
                    else:
                        denominator += self.get_content_val(frame_num + offset)

                denominator = denominator / (2.0 * window_width)
                denominator_is_zero = abs(denominator) < 0.00001

                if not denominator_is_zero:
                    adaptive_ratio = self.get_content_val(frame_num) / denominator
                elif denominator_is_zero and self.get_content_val(
                        frame_num) >= self.min_content_val:
                    # if we would have divided by zero, set adaptive_ratio to the max (255.0)
                    adaptive_ratio = 255.0
                else:
                    # avoid dividing by zero by setting adaptive_ratio to zero if content_val
                    # is still very low
                    adaptive_ratio = 0.0

                self.stats_manager.set_metrics(frame_num,
                                               {self._adaptive_ratio_key: adaptive_ratio})

            # Loop through the frames again now that adaptive_ratio has been calculated to detect
            # cuts using adaptive_ratio
            for frame_num in range(self._first_frame_num + window_width + 1,
                                   self._last_frame_num - window_width):
                # Check to see if adaptive_ratio exceeds the adaptive_threshold as well as there
                # being a large enough content_val to trigger a cut
                if (self.stats_manager.get_metrics(
                        frame_num, [self._adaptive_ratio_key])[0] >= adaptive_threshold
                        and self.get_content_val(frame_num) >= self.min_content_val):

                    if last_cut is None:
                        # No previously detected cuts
                        cut_list.append(frame_num)
                        last_cut = frame_num
                    elif (frame_num - last_cut) >= self.min_scene_len:
                        # Respect the min_scene_len parameter
                        cut_list.append(frame_num)
                        last_cut = frame_num

            return cut_list

        # Stats manager must be used for this detector
        return []
