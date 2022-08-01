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
""":py:class:`ContentDetector` compares the difference in content between adjacent frames against a
set threshold/score, which if exceeded, triggers a scene cut.

This detector is available from the command-line as the `detect-content` command.
"""

from typing import Iterable, List, Optional, Tuple

import numpy
import cv2

from scenedetect.scene_detector import SceneDetector


def calculate_frame_components(frame: numpy.ndarray,
                               calculate_edges: bool = True,
                               sigma: float = 1.0 / 3.0):
    hsv = cv2.split(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV))
    if not calculate_edges:
        return hsv
    median = numpy.median(hsv[2])
    # TODO: Add config file entries for sigma, aperture size, etc.
    low = int(max(0, (1.0 - sigma) * median))
    high = int(min(255, (1.0 + sigma) * median))
    edge = cv2.Canny(hsv[2], low, high)
    # TODO: Use morphological filter to open edges based on resolution, need to increase line width
    # accordingly - just automatically size and allow to be overriden in config file.
    return (*hsv, edge)


def calculate_frame_score(current_frame_hsve: Iterable[numpy.ndarray],
                          last_frame_hsve: Iterable[numpy.ndarray],
                          weight_map: Iterable[float]) -> Tuple[float]:
    """Calculates score between two adjacent frames in the HSVE colourspace. Frames should be
    split, e.g. cv2.split(cv2.cvtColor(frame_data, cv2.COLOR_BGR2HSV)), and edge information
    appended.

    Arguments:
        curr_frame_hsv: Current frame.
        last_frame_hsv: Previous frame.

    Returns:

        Tuple containing the average pixel change for each component as well as the average
        across all components, e.g. (avg_h, avg_s, avg_v, avg_e, avg_all).

    """
    current_frame_hsve = [x.astype(numpy.int32) for x in current_frame_hsve]
    last_frame_hsve = [x.astype(numpy.int32) for x in last_frame_hsve]
    delta_hsve = [0.0] * 5
    num_components = len(current_frame_hsve)
    for i in range(num_components):
        num_pixels = current_frame_hsve[i].shape[0] * current_frame_hsve[i].shape[1]
        delta_hsve[i] = numpy.sum(
            numpy.abs(current_frame_hsve[i] - last_frame_hsve[i])) / float(num_pixels)
    if num_components < 4:
        delta_hsve[3] = None
    delta_hsve[4] = sum([(delta_hsve[i] * weight_map[i]) for i in range(num_components)
                        ]) / sum(weight_map)
    return tuple(delta_hsve)


# TODO: May need to create a dataclass of ContentDetector options:
# - threshold, min_scene_len, luma_only, weight_h, weight_l, ....


class ContentDetector(SceneDetector):
    """Detects fast cuts using changes in colour and intensity between frames.

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.  To detect slow fades between
    content scenes still using HSV information, use the DissolveDetector.
    """

    FRAME_SCORE_KEY = 'content_val'
    DELTA_H_KEY, DELTA_S_KEY, DELTA_V_KEY, DELTA_E_KEY = ('delta_hue', 'delta_sat', 'delta_lum',
                                                          'delta_edge')
    METRIC_KEYS = [FRAME_SCORE_KEY, DELTA_H_KEY, DELTA_S_KEY, DELTA_V_KEY, DELTA_E_KEY]

    # TODO: Come up with some good weights for a new default if there is one that can pass
    # a wider variety of test cases.
    DEFAULT_HSLE_WEIGHT_MAP = (1.0, 1.0, 1.0, 0.0)

    def __init__(
            self,
            threshold: float = 27.0,
            min_scene_len: int = 15,
            luma_only: bool = False, # TODO(v0.6.1): Mark luma_only as deprecated.
            hsle_weights=DEFAULT_HSLE_WEIGHT_MAP):
        """
        Arguments:
            threshold: Threshold the average change in pixel intensity must exceed to trigger a cut.
            min_scene_len: Once a cut is detected, this many frames must pass before a new one can
                be added to the scene list.
            luma_only: If True, only considers changes in the luminance channel of the video. The
                default is False, which considers changes in hue, saturation, and luma.
        """
        super().__init__()
        self.threshold = threshold
                                     # Minimum length of any given scene, in frames (int) or FrameTimecode
        self.min_scene_len = min_scene_len

        self.last_frame = None
        self.last_scene_cut = None
        self.last_hsve = None
        self._hsle_weights = hsle_weights
        # TODO: Need to calculate filter sizes based on downscale factor when creating the detector
        self._debug_mode = False
        self._edge_mask_out: Optional[cv2.VideoWriter] = None

    def get_metrics(self):
        return ContentDetector.METRIC_KEYS

    def is_processing_required(self, frame_num):
        # TODO(v0.6.1): Deprecate this method.
        return True

    def _calculate_frame_score(self, frame_num: int, curr_hsve: List[numpy.ndarray],
                               last_hsve: List[numpy.ndarray]) -> float:
        delta_h, delta_s, delta_v, delta_e, delta_content = calculate_frame_score(
            curr_hsve, last_hsve, self._hsle_weights)
        if self.stats_manager is not None:
            self.stats_manager.set_metrics(
                frame_num, {
                    self.FRAME_SCORE_KEY: delta_content,
                    self.DELTA_H_KEY: delta_h,
                    self.DELTA_S_KEY: delta_s,
                    self.DELTA_V_KEY: delta_v,
                    self.DELTA_E_KEY: delta_e,
                })

        # TODO: Try to add debug mode params to the config file,
        # e.g. allow edge_mask_file = video.avi in [detect-content].
        if self._debug_mode:
            out_frame = cv2.cvtColor(curr_hsve[3], cv2.COLOR_GRAY2BGR)
            if self._edge_mask_out is None:
                self._edge_mask_out = cv2.VideoWriter('debug.avi',
                                                      cv2.VideoWriter_fourcc('X', 'V', 'I',
                                                                             'D'), 23.976,
                                                      (out_frame.shape[1], out_frame.shape[0]))
            self._edge_mask_out.write(out_frame)

        return delta_content

    def process_frame(self, frame_num: int, frame_img: Optional[numpy.ndarray]) -> List[int]:
        """ Similar to ThresholdDetector, but using the HSV colour space DIFFERENCE instead
        of single-frame RGB/grayscale intensity (thus cannot detect slow fades with this method).

        Arguments:
            frame_num: Frame number of frame that is being passed.
            frame_img: Decoded frame image (numpy.ndarray) to perform scene
                detection on. Can be None *only* if the self.is_processing_required() method
                (inhereted from the base SceneDetector class) returns True.

        Returns:
            List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.
        """
        cut_list = []
        _unused = ''

        # Initialize last scene cut point at the beginning of the frames of interest.
        if self.last_scene_cut is None:
            self.last_scene_cut = frame_num

        # We can only start detecting once we have a frame to compare with.
        if self.last_frame is not None:

            calculate_edges: bool = (self._hsle_weights[3] > 0.0) or self._debug_mode
            curr_hsve = calculate_frame_components(frame_img, calculate_edges=calculate_edges)
            last_hsve = self.last_hsve
            if not last_hsve:
                last_hsve = calculate_frame_components(
                    self.last_frame, calculate_edges=calculate_edges)
            frame_score = self._calculate_frame_score(frame_num, curr_hsve, last_hsve)
            self.last_hsve = curr_hsve

            # We consider any frame over the threshold a new scene, but only if
            # the minimum scene length has been reached (otherwise it is ignored).
            if frame_score >= self.threshold and (
                (frame_num - self.last_scene_cut) >= self.min_scene_len):
                cut_list.append(frame_num)
                self.last_scene_cut = frame_num

            if self.last_frame is not None and self.last_frame is not _unused:
                del self.last_frame

        self.last_frame = frame_img.copy()

        return cut_list

    # TODO(#250): Based on the parameters passed to the ContentDetector constructor,
    # ensure that the last scene meets the minimum length requirement, otherwise it
    # should be merged with the previous scene.

    #def post_process(self, frame_num):
    #    """
    #    return []
