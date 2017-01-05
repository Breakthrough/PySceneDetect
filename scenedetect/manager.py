#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains the SceneManager class, which provides a
# consistent interface to the application state, including the current
# scene list, user-defined options, and any shared objects.
#
# Copyright (C) 2012-2016 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy and OpenCV; see the LICENSE-NUMPY and
# LICENSE-OPENCV files or visit one of above URLs for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

# Standard Library Imports
from __future__ import print_function
import sys
import os
import argparse
import time
import csv

# PySceneDetect Library Imports
import scenedetect

# Third-Party Library Imports
import cv2
import numpy


class SceneManager(object):

    def __init__(self, args):
        self.scene_list = list()
        self.detector_list = list()
        self.cap = None

        self.downscale_factor = 0
        self.frame_skip = 0
        self.save_images = False
        self.save_image_prefix = ''

        self.start_frame = args.start_time
        self.end_frame = args.end_time
        self.duration_frames = args.duration

        self.quiet_mode = args.quiet_mode
        self.perf_update_rate = -1
        
        self.stats_writer = None
        #if args.stats_file:
        #    self.stats_writer = csv.writer(args.stats_file)
            





