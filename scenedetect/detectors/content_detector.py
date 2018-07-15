# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses Numpy, OpenCV, click, pytest, mkvmerge, and ffmpeg. See
# the included LICENSE-* files, or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.detectors.content_detector Module

This module implements the ContentDetector, which compares the difference
in content between adjacent frames against a set threshold/score, which if
exceeded, triggers a scene cut.
"""

# Third-Party Library Imports
import numpy
import cv2

# PySceneDetect Library Imports
from scenedetect.scene_detector import SceneDetector


class ContentDetector(SceneDetector):
    """Detects fast cuts using changes in colour and intensity between frames.

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.  To detect slow fades between
    content scenes still using HSV information, use the DissolveDetector.
    """

    def __init__(self, threshold = 30.0, min_scene_len = 15):
        self.threshold = threshold
        self.min_scene_len = min_scene_len  # minimum length of any given scene, in frames
        self.last_frame = None
        self.last_scene_cut = None
        self.last_hsv = None
        self._metric_keys = ['content_val', 'delta_hue', 'delta_sat', 'delta_lum']

    def process_frame(self, frame_num, frame_img):
        # type: (int, numpy.ndarray) -> bool, Optional[int]
        # Similar to ThresholdDetector, but using the HSV colour space DIFFERENCE instead
        # of single-frame RGB/grayscale intensity (thus cannot detect slow fades with this method).

        # Value to return indiciating if a scene cut was found or not.
        cut_detected = False
        cut_frame = None
        metric_keys = self._metric_keys

        if self.last_frame is not None:
            # Change in average of HSV (hsv), (h)ue only, (s)aturation only, (l)uminance only.
            delta_hsv_avg, delta_h, delta_s, delta_v = 0.0, 0.0, 0.0, 0.0
            
            if (self.stats_manager is not None and
                self.stats_manager.metrics_exist(frame_num, metric_keys)):
                delta_hsv_avg, delta_h, delta_s, delta_v = self.stats_manager.get_metrics(
                    frame_num, metric_keys)

            else:
                num_pixels = frame_img.shape[0] * frame_img.shape[1]
                curr_hsv = cv2.split(cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV))
                last_hsv = self.last_hsv
                if not last_hsv:
                    last_hsv = cv2.split(cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2HSV))

                delta_hsv = [0, 0, 0, 0]
                for i in range(3):
                    num_pixels = curr_hsv[i].shape[0] * curr_hsv[i].shape[1]
                    curr_hsv[i] = curr_hsv[i].astype(numpy.int32)
                    last_hsv[i] = last_hsv[i].astype(numpy.int32)
                    delta_hsv[i] = numpy.sum(numpy.abs(curr_hsv[i] - last_hsv[i])) / float(num_pixels)
                delta_hsv[3] = sum(delta_hsv[0:3]) / 3.0
                delta_h, delta_s, delta_v, delta_hsv_avg = delta_hsv

                if self.stats_manager is not None:
                    self.stats_manager.set_metrics(frame_num, {
                        metric_keys[0]: delta_hsv_avg, metric_keys[1]: delta_h,
                        metric_keys[2]: delta_s, metric_keys[3]: delta_v })

                self.last_hsv = curr_hsv

            if delta_hsv_avg >= self.threshold:
                if self.last_scene_cut is None or (
                  (frame_num - self.last_scene_cut) >= self.min_scene_len):
                    #scene_manager.add_cut(frame_num)   # Returning True will do the same now.
                    cut_detected = True
                    cut_frame = frame_num
                    self.last_scene_cut = frame_num

            #self.last_frame.release()
            del self.last_frame
                
        self.last_frame = frame_img.copy()
        return cut_detected, cut_frame


    #def post_process(self, scene_list, frame_num):
    #    """Not used for ContentDetector, as cuts are written as they are found."""
    #    return []

