# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the above pages for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
""":py:class:`ContentDetector` compares the difference in content between adjacent frames
against a set threshold/score, which if exceeded, triggers a scene cut.

This detector is available from the command-line as the `detect-content` command.
"""

from typing import Iterable, List, Tuple

import numpy
import cv2

from scenedetect.scene_detector import SceneDetector


def calculate_frame_score(current_frame_hsv: Iterable[numpy.ndarray],
                          last_frame_hsv: Iterable[numpy.ndarray]) -> Tuple[float]:
    """Calculates score between two adjacent frames in the HSV colourspace. Frames should be
    split, e.g. cv2.split(cv2.cvtColor(frame_data, cv2.COLOR_BGR2HSV)).

    Arguments:
        curr_frame_hsv: Current frame.
        last_frame_hsv: Previous frame.

    Returns:

        Tuple containing the average pixel change for each component as well as the average
        across all components, e.g. (avg_h, avg_s, avg_v, avg_all).

    """
    current_frame_hsv = [x.astype(numpy.int32) for x in current_frame_hsv]
    last_frame_hsv = [x.astype(numpy.int32) for x in last_frame_hsv]
    delta_hsv = [0, 0, 0, 0]
    for i in range(3):
        num_pixels = current_frame_hsv[i].shape[0] * current_frame_hsv[i].shape[1]
        delta_hsv[i] = numpy.sum(
            numpy.abs(current_frame_hsv[i] - last_frame_hsv[i])) / float(num_pixels)

    delta_hsv[3] = sum(delta_hsv[0:3]) / 3.0
    return tuple(delta_hsv)


class ContentDetector(SceneDetector):
    """Detects fast cuts using changes in colour and intensity between frames.

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.  To detect slow fades between
    content scenes still using HSV information, use the DissolveDetector.
    """

    FRAME_SCORE_KEY = 'content_val'
    DELTA_H_KEY, DELTA_S_KEY, DELTA_V_KEY = ('delta_hue', 'delta_sat', 'delta_lum')
    METRIC_KEYS = [FRAME_SCORE_KEY, DELTA_H_KEY, DELTA_S_KEY, DELTA_V_KEY]

    def __init__(self, threshold: float = 27.0, min_scene_len: int = 15, luma_only: bool = False):
        """Construct a `ContentDetector`.

        Arguments:
            threshold: Threshold the average change in pixel intensity must exceed to trigger a cut.
            min_scene_len: Once a cut is detected, this many frames must pass before a new one can
                be added to the scene list.
            luma_only: If True, only considers changes in the luminance channel of the video. The
                default is False, which considers changes in hue, saturation, and luma.
        """
        #
        #  type: (float, Union[int, FrameTimecode]) -> None
        super().__init__()
        self.threshold = threshold
        # Minimum length of any given scene, in frames (int) or FrameTimecode
        self.min_scene_len = min_scene_len
        self.luma_only = luma_only
        self.last_frame = None
        self.last_scene_cut = None
        self.last_hsv = None

    def get_metrics(self):
        return ContentDetector.METRIC_KEYS

    def is_processing_required(self, frame_num):
        if self.stats_manager is None:
            return False
        # Note this will always return True on the last frame of a video, but that's fine
        # as the only side-effect is the frame being decoded. We still don't perform the
        # calculations for that frame in `process_frame` if the last frame's metrics exist.
        return not self.stats_manager.metrics_exist(frame_num, ContentDetector.METRIC_KEYS) or (
            not self.stats_manager.metrics_exist(frame_num + 1, ContentDetector.METRIC_KEYS))

    def _calculate_frame_score(self, frame_num: int, curr_hsv: List[numpy.ndarray],
                               last_hsv: List[numpy.ndarray]) -> float:
        delta_h, delta_s, delta_v, delta_content = calculate_frame_score(curr_hsv, last_hsv)

        if self.stats_manager is not None:
            self.stats_manager.set_metrics(
                frame_num, {
                    self.FRAME_SCORE_KEY: delta_content,
                    self.DELTA_H_KEY: delta_h,
                    self.DELTA_S_KEY: delta_s,
                    self.DELTA_V_KEY: delta_v
                })
        return delta_content if not self.luma_only else delta_v

    def process_frame(self, frame_num: int, frame_img: numpy.ndarray) -> List[int]:
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
            # We obtain the change in average of HSV (frame_score), (h)ue only,
            # (s)aturation only, and (l)uminance only.  These are refered to in a statsfile
            # as their respective metric keys.
            metric_key = (
                ContentDetector.DELTA_V_KEY if self.luma_only else ContentDetector.FRAME_SCORE_KEY)
            if (self.stats_manager is not None
                    and self.stats_manager.metrics_exist(frame_num, [metric_key])):
                frame_score = self.stats_manager.get_metrics(frame_num, [metric_key])[0]
            else:
                curr_hsv = cv2.split(cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV))
                last_hsv = self.last_hsv
                if not last_hsv:
                    last_hsv = cv2.split(cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2HSV))

                frame_score = self._calculate_frame_score(frame_num, curr_hsv, last_hsv)

                self.last_hsv = curr_hsv

            # We consider any frame over the threshold a new scene, but only if
            # the minimum scene length has been reached (otherwise it is ignored).
            if frame_score >= self.threshold and (
                (frame_num - self.last_scene_cut) >= self.min_scene_len):
                cut_list.append(frame_num)
                self.last_scene_cut = frame_num

            if self.last_frame is not None and self.last_frame is not _unused:
                del self.last_frame

        # If we have the next frame computed, don't copy the current frame
        # into last_frame since we won't use it on the next call anyways.
        if (self.stats_manager is not None
                and self.stats_manager.metrics_exist(frame_num + 1, self.get_metrics())):
            self.last_frame = _unused
        else:
            self.last_frame = frame_img.copy()

        return cut_list

    #def post_process(self, frame_num):
    #    """ TODO: Based on the parameters passed to the ContentDetector constructor,
    #        ensure that the last scene meets the minimum length requirement,
    #        otherwise it should be merged with the previous scene.
    #    """
    #    return []
