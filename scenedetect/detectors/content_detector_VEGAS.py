# -*- coding: utf-8 -*-
#
#         VEGASSceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.hlinke.de/   ]
#     [  Github: coming soon  ]
#     [  Documentation: coming soon    ]
#
#  Copyright (C) 2019 Harold Linke <http://www.hlinke.de>.
# VEGASSceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file
#
# VEGASSceneDetect is based on pySceneDetect by Brandon Castellano
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses the Numpy, OpenCV, click, tqdm, and pytest libraries.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect `scenedetect.detectors.content_detector` Module

This module implements the ContentDetector, which compares the difference
in content between adjacent frames against a set threshold/score, which if
exceeded, triggers a scene cut.
"""

# Third-Party Library Imports
import numpy
import cv2

# PySceneDetect Library Imports
from scenedetect.scene_detector import SceneDetector

class ContentDetector_VEGAS(SceneDetector):
    """Detects fast cuts using changes in colour and intensity between frames.

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.  To detect slow fades between
    content scenes still using HSV information, use the DissolveDetector.
    """

    def __init__(self, threshold=30.0, min_scene_len=15, showFrameValues=False, use_hsv = False):
        super(ContentDetector_VEGAS, self).__init__()
        self.threshold = threshold
        self.min_scene_len = min_scene_len  # minimum length of any given scene, in frames
        self.last_scene_cut = None
        self.last_img = None
        self.showFrameValues = showFrameValues
        self.use_hsv = use_hsv
 
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
            List[int]: List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.
        """
        cut_list = []
                
        # Change in average of HSV (hsv), (h)ue only, (s)aturation only, (l)uminance only.
        delta_avg = 0.0
                        
        last_img = self.last_img
                
        if last_img is None:
            curr_hsv = cv2.cvtColor(frame_img,cv2.COLOR_BGR2HSV)
        else:
            if self.use_hsv:
                curr_hsv = cv2.cvtColor(frame_img,cv2.COLOR_BGR2HSV)
                delta_img = cv2.absdiff(curr_hsv , last_img)
            else:
                delta_img = cv2.absdiff(frame_img, last_img) # use RGB only

            delta_mean = [0, 0, 0,0]
            delta_mean = cv2.mean(delta_img)
                
            delta_avg = sum(delta_mean[0:3]) / 3.0
            delta_h, delta_s, delta_v, dummy = delta_mean
           
        if self.showFrameValues:
            print("Frame:", frame_num,"-", delta_avg)

        if self.use_hsv:
            self.last_img = curr_hsv
        else:
            self.last_img = frame_img

        if delta_avg >= self.threshold:
            if self.last_scene_cut is None or (
                    (frame_num - self.last_scene_cut) >= self.min_scene_len):
                cut_list.append(frame_num)
                self.last_scene_cut = frame_num
 
        return cut_list


    #def post_process(self, frame_num):
    #    """ Not used for ContentDetector, as unlike ThresholdDetector, cuts
    #    are always written as they are found.
    #    """
    #    return []

