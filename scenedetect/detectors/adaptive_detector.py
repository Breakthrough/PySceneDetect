# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2021 Brandon Castellano <http://www.bcastell.com>.
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

""" Module: ``scenedetect.detectors.adaptive_detector``

This module implements the :py:class:`AdaptiveDetector`, which compares the
difference in content between adjacent frames similar to `ContentDetector` except the
threshold isn't fixed, but is a rolling average of adjacent frame changes. This can
help mitigate false detections in situations such as fast camera motions.

This detector is available from the command-line interface by using the
`adaptive-detect-content` command.
"""

# PySceneDetect Library Imports
from scenedetect.detectors import ContentDetector


class AdaptiveDetector(ContentDetector):
    """Detects cuts using HSV changes similar to ContentDetector, but with a
    rolling average that can help mitigate false detections in situations such
    as camera moves.
    """

    ADAPTIVE_RATIO_KEY_TEMPLATE = "adaptive_ratio{luma_only} (w={window_width})"

    def __init__(self, video_manager, adaptive_threshold=3.0,
                 luma_only=False, min_scene_len=15, min_delta_hsv=15.0, window_width=2):
        super(AdaptiveDetector, self).__init__()
        self.video_manager = video_manager
        self.min_scene_len = min_scene_len  # minimum length of any given scene, in frames (int) or FrameTimecode
        self.adaptive_threshold = adaptive_threshold
        self.min_delta_hsv = min_delta_hsv
        self.window_width = window_width
        self._luma_only = luma_only
        self._adaptive_ratio_key = AdaptiveDetector.ADAPTIVE_RATIO_KEY_TEMPLATE.format(
            window_width=window_width, luma_only='' if not luma_only else '_lum')


    def get_metrics(self):
        # type: () -> List[str]
        """ Combines base ContentDetector metric keys with the AdaptiveDetector one. """
        return super(AdaptiveDetector, self).get_metrics() + [self._adaptive_ratio_key]

    def stats_manager_required(self):
        # type: () -> bool
        """ Overload to indicate that this detector requires a StatsManager.

        Returns:
            True as AdaptiveDetector requires stats.
        """
        return True

    def process_frame(self, frame_num, frame_img):
        # type: (int, numpy.ndarray) -> List[int]
        """ Similar to ThresholdDetector, but using the HSV colour space DIFFERENCE instead
        of single-frame RGB/grayscale intensity (thus cannot detect slow fades with this method).

        Arguments:
            frame_num (int): Frame number of frame that is being passed.

            frame_img (Optional[int]): Decoded frame image (numpy.ndarray) to perform scene
                detection on. Can be None *only* if the self.is_processing_required() method
                (inhereted from the base SceneDetector class) returns True.

        Returns:
            Empty list
        """

        # Call the process_frame function of ContentDetector but ignore any
        # returned cuts
        if self.is_processing_required(frame_num):
            super(AdaptiveDetector, self).process_frame(
                frame_num=frame_num, frame_img=frame_img)

        return []


    def get_content_val(self, frame_num):
        """
        Returns the average content change for a frame.
        """
        metric_key = (ContentDetector.FRAME_SCORE_KEY if not self._luma_only
            else ContentDetector.DELTA_V_KEY)
        return self.stats_manager.get_metrics(
            frame_num, [metric_key])[0]


    def post_process(self, _):
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
        adaptive_threshold = self.adaptive_threshold
        window_width = self.window_width
        last_cut = None

        assert self.stats_manager is not None

        if self.stats_manager is not None:
            # Loop through the stats, building the adaptive_ratio metric
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

                denominator = denominator / (2.0 * window_width)
                denominator_is_zero = abs(denominator) < 0.00001

                if not denominator_is_zero:
                    adaptive_ratio = self.get_content_val(frame_num) / denominator
                elif denominator_is_zero and self.get_content_val(frame_num) >= self.min_delta_hsv:
                    # if we would have divided by zero, set adaptive_ratio to the max (255.0)
                    adaptive_ratio = 255.0
                else:
                    # avoid dividing by zero by setting adaptive_ratio to zero if content_val
                    # is still very low
                    adaptive_ratio = 0.0

                self.stats_manager.set_metrics(
                    frame_num, {self._adaptive_ratio_key: adaptive_ratio})

            # Loop through the frames again now that adaptive_ratio has been calculated to detect
            # cuts using adaptive_ratio
            for frame_num in range(start_frame + window_width + 1, end_frame - window_width):
                # Check to see if adaptive_ratio exceeds the adaptive_threshold as well as there
                # being a large enough content_val to trigger a cut
                if (self.stats_manager.get_metrics(
                    frame_num, [self._adaptive_ratio_key])[0] >= adaptive_threshold and
                        self.get_content_val(frame_num) >= self.min_delta_hsv):

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
