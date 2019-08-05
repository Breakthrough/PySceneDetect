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

""" PySceneDetect `scenedetect.detectors.threshold_detector` Module

This module implements the ThresholdDetector, which uses a set intensity level
to detect scene cuts when the average frame intensity passes the set threshold.
"""

# Third-Party Library Imports
import numpy

# PySceneDetect Library Imports
from scenedetect.scene_detector import SceneDetector


##
## ThresholdDetector Helper Functions
##

def compute_frame_average(frame):
    """Computes the average pixel value/intensity for all pixels in a frame.

    The value is computed by adding up the 8-bit R, G, and B values for
    each pixel, and dividing by the number of pixels multiplied by 3.

    Returns:
        Floating point value representing average pixel intensity.
    """
    num_pixel_values = float(
        frame.shape[0] * frame.shape[1] * frame.shape[2])
    avg_pixel_value = numpy.sum(frame[:, :, :]) / num_pixel_values
    return avg_pixel_value


##
## ThresholdDetector Class Implementation
##

class ThresholdDetector(SceneDetector):
    """Detects fast cuts/slow fades in from and out to a given threshold level.

    Detects both fast cuts and slow fades so long as an appropriate threshold
    is chosen (especially taking into account the minimum grey/black level).

    Attributes:
        threshold:  8-bit intensity value that each pixel value (R, G, and B)
            must be <= to in order to trigger a fade in/out.
        min_percent:  Float between 0.0 and 1.0 which represents the minimum
            percent of pixels in a frame that must meet the threshold value in
            order to trigger a fade in/out.
        min_scene_len:  Unsigned integer greater than 0 representing the
            minimum length, in frames, of a scene (or subsequent scene cut).
        fade_bias:  Float between -1.0 and +1.0 representing the percentage of
            timecode skew for the start of a scene (-1.0 causing a cut at the
            fade-to-black, 0.0 in the middle, and +1.0 causing the cut to be
            right at the position where the threshold is passed).
        add_final_scene:  Boolean indicating if the video ends on a fade-out to
            generate an additional scene at this timecode.
        block_size:  Number of rows in the image to sum per iteration (can be
            tuned to increase performance in some cases; should be computed
            programmatically in the future).
    """
    def __init__(self, threshold=12, min_percent=0.95, min_scene_len=15,
                 fade_bias=0.0, add_final_scene=False, block_size=8):
        """Initializes threshold-based scene detector object."""

        super(ThresholdDetector, self).__init__()
        self.threshold = int(threshold)
        self.fade_bias = fade_bias
        self.min_percent = min_percent
        self.min_scene_len = min_scene_len
        self.last_frame_avg = None
        self.last_scene_cut = None
        # Whether to add an additional scene or not when ending on a fade out
        # (as cuts are only added on fade ins; see post_process() for details).
        self.add_final_scene = add_final_scene
        # Where the last fade (threshold crossing) was detected.
        self.last_fade = {
            'frame': 0,         # frame number where the last detected fade is
            'type': None        # type of fade, can be either 'in' or 'out'
        }
        self.block_size = block_size
        self._metric_keys = ['delta_rgb']
        self.cli_name = 'detect-threshold'

    def frame_under_threshold(self, frame):
        """Check if the frame is below (true) or above (false) the threshold.

        Instead of using the average, we check all pixel values (R, G, and B)
        meet the given threshold (within the minimum percent).  This ensures
        that the threshold is not exceeded while maintaining some tolerance for
        compression and noise.

        This is the algorithm used for absolute mode of the threshold detector.

        Returns:
            Boolean, True if the number of pixels whose R, G, and B values are
            all <= the threshold is within min_percent pixels, or False if not.
        """
        # First we compute the minimum number of pixels that need to meet the
        # threshold. Internally, we check for values greater than the threshold
        # as it's more likely that a given frame contains actual content. This
        # is done in blocks of rows, so in many cases we only have to check a
        # small portion of the frame instead of inspecting every single pixel.
        num_pixel_values = float(frame.shape[0] * frame.shape[1] * frame.shape[2])
        min_pixels = int(num_pixel_values * (1.0 - self.min_percent))

        curr_frame_amt = 0
        curr_frame_row = 0

        while curr_frame_row < frame.shape[0]:
            # Add and total the number of individual pixel values (R, G, and B)
            # in the current row block that exceed the threshold.
            curr_frame_amt += int(numpy.sum(
                frame[curr_frame_row : curr_frame_row + self.block_size, :, :] > self.threshold))
            # If we've already exceeded the most pixels allowed to be above the
            # threshold, we can skip processing the rest of the pixels.
            if curr_frame_amt > min_pixels:
                return False
            curr_frame_row += self.block_size
        return True

    def process_frame(self, frame_num, frame_img):
        # type: (int, Optional[numpy.ndarray]) -> List[int]
        """
        Args:
            frame_num (int): Frame number of frame that is being passed.
            frame_img (numpy.ndarray or None): Decoded frame image (numpy.ndarray) to perform
                scene detection with. Can be None *only* if the self.is_processing_required()
                method (inhereted from the base SceneDetector class) returns True.
        Returns:
            List[int]: List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.
        """

        # Compare the # of pixels under threshold in current_frame & last_frame.
        # If absolute value of pixel intensity delta is above the threshold,
        # then we trigger a new scene cut/break.

        # List of cuts to return.
        cut_list = []

        # The metric used here to detect scene breaks is the percent of pixels
        # less than or equal to the threshold; however, since this differs on
        # user-supplied values, we supply the average pixel intensity as this
        # frame metric instead (to assist with manually selecting a threshold)
        frame_avg = 0.0

        if (self.stats_manager is not None and
                self.stats_manager.metrics_exist(frame_num, self._metric_keys)):
            frame_avg = self.stats_manager.get_metrics(frame_num, self._metric_keys)[0]
        else:
            frame_avg = compute_frame_average(frame_img)
            if self.stats_manager is not None:
                self.stats_manager.set_metrics(frame_num, {
                    self._metric_keys[0]: frame_avg})

        if self.last_frame_avg is not None:
            if self.last_fade['type'] == 'in' and self.frame_under_threshold(frame_img):
                # Just faded out of a scene, wait for next fade in.
                self.last_fade['type'] = 'out'
                self.last_fade['frame'] = frame_num
            elif self.last_fade['type'] == 'out' and not self.frame_under_threshold(frame_img):
                # Only add the scene if min_scene_len frames have passed.
                if (self.last_scene_cut is None and frame_num >= self.min_scene_len) or (
                        (frame_num - self.last_scene_cut) >= self.min_scene_len):
                    # Just faded into a new scene, compute timecode for the scene
                    # split based on the fade bias.
                    f_out = self.last_fade['frame']
                    f_split = int((frame_num + f_out +
                                   int(self.fade_bias * (frame_num - f_out))) / 2)
                    cut_list.append(f_split)
                    self.last_scene_cut = frame_num
                self.last_fade['type'] = 'in'
                self.last_fade['frame'] = frame_num
        else:
            self.last_fade['frame'] = 0
            if self.frame_under_threshold(frame_img):
                self.last_fade['type'] = 'out'
            else:
                self.last_fade['type'] = 'in'
        # Before returning, we keep track of the last frame average (can also
        # be used to compute fades independently of the last fade type).
        self.last_frame_avg = frame_avg
        return cut_list

    def post_process(self, frame_num):
        """Writes a final scene cut if the last detected fade was a fade-out.

        Only writes the scene cut if add_final_scene is true, and the last fade
        that was detected was a fade-out.  There is no bias applied to this cut
        (since there is no corresponding fade-in) so it will be located at the
        exact frame where the fade-out crossed the detection threshold.
        """

        # If the last fade detected was a fade out, we add a corresponding new
        # scene break to indicate the end of the scene.  This is only done for
        # fade-outs, as a scene cut is already added when a fade-in is found.
        cut_times = []
        if self.last_fade['type'] == 'out' and self.add_final_scene and (
                (self.last_scene_cut is None and frame_num >= self.min_scene_len) or
                (frame_num - self.last_scene_cut) >= self.min_scene_len):
            cut_times.append(self.last_fade['frame'])
        return cut_times
