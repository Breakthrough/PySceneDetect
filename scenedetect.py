#!/usr/bin/env python
#
#         PySceneDetect: Python-Based Video Scene Detector
#    -----------------------------------------------------------
#        [ http://www.bcastell.com/projects/pyscenedetect/ ]
#        [ https://github.com/Breakthrough/PySceneDetect/  ]
#
# This program implements an optimized threshold-based scene detection
# algorithm, generating a list of scene/chapter timecodes (or frame)
# numbers), which can be used to split the video with an external tool
# (e.g. ffmpeg, mkvmerge) into sequential parts.  Usage:
#
#   ./scenedetect.py [-h] -i VIDEO_FILE [optional args]
#
# Where -i denotes the input video, and -h shows the help message (as
# well as a list of optional arguments and descriptions).
#
#
# Copyright (C) 2013-2015 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit the following page for details:
# http://www.bcastell.com/projects/pyscenedetect
#
# This software uses Numpy and OpenCV; see the LICENSE-NUMPY and
# LICENSE-OPENCV files for details, or visit the above URL.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

import sys
import argparse

import cv2
import numpy


VERSION_STRING = '0.3-beta-dev'
ABOUT_STRING   = """
PySceneDetect %s
-----------------------------------------------
http://www.bcastell.com/projects/pyscenedetect
https://github.com/Breakthrough/PySceneDetect
-----------------------------------------------
Copyright (C) 2013-2015 Brandon Castellano
License: BSD 2-Clause (see the included LICENSE file for details, or
         visit < http://www.bcastell.com/projects/pyscenedetect >).
This software uses the following third-party components:
  > NumPy    [Copyright (C) 2005-2013, Numpy Developers]
  > OpenCV   [Copyright (C) 2014, Itseez]
THE SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.

""" % VERSION_STRING


class SceneDetector(object):
    """Base SceneDetector class to implement a scene detection/splitting algorithm."""
    def __init__(self):
        pass

    def detect(self, current_frame, last_frame):
        """Detect if the scene changed between the last_frame and current_frame.
        Returns True if the scene changed, False otherwise."""
        # Prototype method, no actual detection, so we just return False.
        return False


class ThresholdDetector(SceneDetector):
    def __init__(self):
        super(ThresholdDetector, self).__init__()

    def detect(self, current_frame, last_frame):
        # Compare average intensity of current_frame and last_frame.
        # If absolute value of pixel intensity delta is above the threshold,
        # then we trigger a new scene.
        return False


class ContentDetector(SceneDetector):
    def __init__(self):
        super(HSVDetector, self).__init__()

    def detect(self, current_frame, last_frame):
        # Similar to ThresholdDetector, but using the HSV colour space instead
        # of RGB/grayscale intensity.
        return False


class EdgeDetector(SceneDetector):
    def __init__(self):
        super(EdgeDetector, self).__init__()

    def detect(self, current_frame, last_frame):
        # Uses a high-pass filter to compare the current_frame and last_frame
        # to detect changes to the scene's contents.
        return False

