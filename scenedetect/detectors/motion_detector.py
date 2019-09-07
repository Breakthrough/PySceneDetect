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

""" PySceneDetect ``scenedetect.detectors.motion_detector`` Module

This module implements the :py:class:`MotionDetector`, which detects motion events
using background subtraction, morphological transforms, and thresholding.

This detector is available from the command-line interface by using the
`detect-motion` command.
"""

# Third-Party Library Imports
import cv2

# PySceneDetect Library Imports
from scenedetect.scene_detector import SparseSceneDetector

class MotionDetector(SparseSceneDetector):
    """Detects motion events in scenes containing a static background.

    Uses background subtraction followed by noise removal (via morphological
    opening) to generate a frame score compared against the set threshold.

    Attributes:
        threshold:  floating point value compared to each frame's score, which
            represents average intensity change per pixel (lower values are
            more sensitive to motion changes).  Default 0.5, must be > 0.0.
        num_frames_post_scene:  Number of frames to include in each motion
            event after the frame score falls below the threshold, adding any
            subsequent motion events to the same scene.
        kernel_size:  Size of morphological opening kernel for noise removal.
            Setting to -1 (default) will auto-compute based on video resolution
            (typically 3 for SD, 5-7 for HD). Must be an odd integer > 1.
    """
    def __init__(self, threshold = 0.50, num_frames_post_scene = 30,
                 kernel_size = -1):
        """Initializes motion-based scene detector object."""
        # Requires porting to v0.5 API.
        raise NotImplementedError()

        self.threshold = float(threshold)
        self.num_frames_post_scene = int(num_frames_post_scene)

        self.kernel_size = int(kernel_size)
        if self.kernel_size < 0:
            # Set kernel size when process_frame first runs based on
            # video resolution (480p = 3x3, 720p = 5x5, 1080p = 7x7).
            pass

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2( 
            detectShadows = False )

        self.last_frame_score = 0.0

        self.in_motion_event = False
        self.first_motion_frame_index = -1
        self.last_motion_frame_index = -1
        self.cli_name = 'detect-motion'
        return

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):

        # Value to return indiciating if a scene cut was found or not.
        cut_detected = False

        frame_grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        masked_frame = self.bg_subtractor.apply(frame_grayscale)

        kernel = numpy.ones((self.kernel_size, self.kernel_size), numpy.uint8)
        filtered_frame = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)

        frame_score = numpy.sum(filtered_frame) / float( 
            filtered_frame.shape[0] * filtered_frame.shape[1] )

        return cut_detected

    def post_process(self, scene_list, frame_num):
        """Writes the last scene if the video ends while in a motion event.
        """

        # If the last fade detected was a fade out, we add a corresponding new
        # scene break to indicate the end of the scene.  This is only done for
        # fade-outs, as a scene cut is already added when a fade-in is found.

        if self.in_motion_event:
            # Write new scene based on first and last motion event frames.
            pass
        return self.in_motion_event


