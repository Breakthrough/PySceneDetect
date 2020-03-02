# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2019 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" Module: ``scenedetect.detectors.content_detector``

This module implements the :py:class:`ContentDetector`, which compares the
difference in content between adjacent frames against a set threshold/score,
which if exceeded, triggers a scene cut.

This detector is available from the command-line interface by using the
`detect-content` command.
"""

# Third-Party Library Imports
import numpy
import cv2

# PySceneDetect Library Imports
from scenedetect.scene_detector import SceneDetector


class AdaptiveContentDetector(SceneDetector):
    """Detects cuts using HSV changes similar to ContentDetector, but with a
    rolling average that can help mitigate false detections in situations such
    as camera moves.
    """

    def __init__(self, video_manager=None, adaptive_threshold=3.0, min_scene_len=15, min_delta_hsv=5.0, window_width=2):
        super(AdaptiveContentDetector, self).__init__()
        self.video_manager = video_manager
        self.min_scene_len = min_scene_len  # minimum length of any given scene, in frames (int) or FrameTimecode
        self.adaptive_threshold = adaptive_threshold
        self.min_delta_hsv = min_delta_hsv
        self.window_width = window_width
        self.last_frame = None
        self.last_scene_cut = None
        self.last_hsv = None
        self._metric_keys = ['content_val', 'delta_hue', 'delta_sat',
                             'delta_lum', 'con_val_ratio']
        self.cli_name = 'adaptive-detect-content'

    def process_frame(self, frame_num, frame_img):
        # type: (int, numpy.ndarray) -> List[int]
        """ Similar to ContentDetector, but looking for frames in which the HSV difference is
        significantly different than the neighboring frames.

        Arguments:
            frame_num (int): Frame number of frame that is being passed.

            frame_img (Optional[int]): Decoded frame image (numpy.ndarray) to perform scene
                detection on. Can be None *only* if the self.is_processing_required() method
                (inhereted from the base SceneDetector class) returns True.

        Returns:
            Empty list: The process_frame function for this detector does not register any cuts,
                instead only calculating scene metrics that are used to detect cuts with the
                post_process function.
        """

        metric_keys = self._metric_keys
        _unused = ''

        # We can only start detecting once we have a frame to compare with.
        if self.last_frame is not None:
            # Change in average of HSV (hsv), (h)ue only, (s)aturation only, (l)uminance only.
            # These are refered to in a statsfile as their respective self._metric_keys string.
            delta_hsv_avg, delta_h, delta_s, delta_v = 0.0, 0.0, 0.0, 0.0

            if (self.stats_manager is not None and
                    self.stats_manager.metrics_exist(frame_num, metric_keys)):
                delta_hsv_avg, delta_h, delta_s, delta_v = self.stats_manager.get_metrics(
                    frame_num, metric_keys)[:4]

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
                    delta_hsv[i] = numpy.sum(
                        numpy.abs(curr_hsv[i] - last_hsv[i])) / float(num_pixels)
                delta_hsv[3] = sum(delta_hsv[0:3]) / 3.0
                delta_h, delta_s, delta_v, delta_hsv_avg = delta_hsv

                if self.stats_manager is not None:
                    self.stats_manager.set_metrics(frame_num, {
                        metric_keys[0]: delta_hsv_avg,
                        metric_keys[1]: delta_h,
                        metric_keys[2]: delta_s,
                        metric_keys[3]: delta_v})

                self.last_hsv = curr_hsv

        if self.last_frame is not None and self.last_frame is not _unused:
            del self.last_frame

        # If we have the next frame computed, don't copy the current frame
        # into last_frame since we won't use it on the next call anyways.
        if (self.stats_manager is not None and
                self.stats_manager.metrics_exist(frame_num+1, metric_keys)):
            self.last_frame = _unused
        else:
            self.last_frame = frame_img.copy()

        return []

    def get_content_val(self, frame_num):
        """
        Returns the average content change for a frame.
        """
        return self.stats_manager.get_metrics(frame_num, ['content_val'])[0]

    def post_process(self, frame):
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
        _, start_timecode, end_timecode = self.video_manager.get_duration()
        start_frame = start_timecode.get_frames()
        end_frame = end_timecode.get_frames()
        metric_keys = self._metric_keys
        adaptive_threshold = self.adaptive_threshold
        window_width = self.window_width
        last_cut = None

        if self.stats_manager is not None:
            # Loop through the stats, building the con_val_ratio metric
            for frame_num in range(start_frame + window_width + 1, end_frame - window_width):
                # If the content-val of the frame is more than
                # adaptive_threshold times the mean content_val of the
                # frames around it, then we mark it as a cut.
                denominator = 0
                for offset in range(-window_width, window_width + 1):
                    if offset == 0:
                        continue
                    else:
                        denominator += self.get_content_val(frame_num + offset)

                denominator = denominator / (2 * window_width)

                if denominator != 0:
                    # store the calculated con_val_ratio in our metrics
                    self.stats_manager.set_metrics(
                        frame_num,
                        {metric_keys[4]: self.get_content_val(frame_num) / denominator})

                elif denominator == 0 and self.get_content_val(frame_num) >= self.min_delta_hsv:
                    # avoid dividing by zero, setting con_val_ratio to above the threshold
                    self.stats_manager.set_metrics(frame_num, {metric_keys[4]: adaptive_threshold + 1})

                else:
                    # avoid dividing by zero, setting con_val_ratio to zero if content_val is still very low
                    self.stats_manager.set_metrics(frame_num, {metric_keys[4]: 0})

            # Loop through the frames again now that con_val_ratio has been calculated to detect
            # cuts using con_val_ratio
            for frame_num in range(start_frame + window_width + 1, end_frame - window_width):
                # Check to see if con_val_ratio exceeds the adaptive_threshold as well as there
                # being a large enough content_val to trigger a cut
                if (self.stats_manager.get_metrics(
                    frame_num, ['con_val_ratio'])[0] >= adaptive_threshold and
                        self.stats_manager.get_metrics(
                            frame_num, ['content_val'])[0] >= self.min_delta_hsv):

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
        return None
