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

""" PySceneDetect scenedetect.scene_manager Tests

This file includes unit tests for the scenedetect.scene_manager module (specifically,
the SceneManager object, used to coordinate using SceneDetector objects on video
capture/frame sources like the scenedetect.video_decoder.VideoManager object, or
a cv2.VideoCapture object).

These tests rely on the testvideo.mp4 test video file, available by checking out the
PySceneDetect git repository "resources" branch, or the following URL to download it
directly:  https://github.com/Breakthrough/PySceneDetect/tree/resources/tests
"""

import unittest
import time
import os

import scenedetect

from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode

from scenedetect.video_manager import VideoManager
from scenedetect.video_manager_async import VideoManagerAsync

from scenedetect.stats_manager import StatsManager


import cv2

TEST_VIDEO_FILE = 'testvideo.mp4'

class TestSceneManager(unittest.TestCase):
    """ SceneManager Unit Test Cases

    These unit tests test the VideoDecoder object with respect to object construction,
    testing argument format/limits, opening videos and grabbing frames, and appending
    multiple videos together.  These tests rely on testvideo.mp4, available in the
    PySceneDetect git repository "resources" branch.
    """

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_VIDEO_FILE):
            raise FileNotFoundError(
                'Test video file (%s) must be present to run test cases' % TEST_VIDEO_FILE)

    # Change print_runtime to False for release.
    def test_content_detect(self, print_runtime=True):
        
        vm = VideoManager([TEST_VIDEO_FILE])
        sm = SceneManager()
        sm.add_detector(scenedetect.scene_manager.ContentDetectorNew())
        
        try:
            t0 = time.time()

            video_fps = vm.get_framerate()
            start_time = FrameTimecode('00:00:00', video_fps)
            duration = FrameTimecode('00:00:05', video_fps)
            
            vm.set_duration(start_time = start_time, end_time = duration)
            vm.start()
            sm.detect_scenes(frame_source = vm)

            if print_runtime:
                print("Ran in %.1f seconds." % (time.time() - t0))

        finally:
            vm.stop()
            vm.release()


    def test_content_detect_asynchronous(self, print_runtime=True):
        
        vm = VideoManagerAsync([TEST_VIDEO_FILE])
        sm = SceneManager()
        sm.add_detector(scenedetect.scene_manager.ContentDetectorNew())

        try:
            t0 = time.time()

            video_fps = vm.get_framerate()
            start_time = FrameTimecode('00:00:00', video_fps)
            duration = FrameTimecode('00:00:05', video_fps)

            vm.set_duration(start_time = start_time, end_time = duration)
            vm.start()

            sm.detect_scenes(frame_source = vm)

            if print_runtime:
                print("Ran in %.1f seconds." % (time.time() - t0))

        finally:
            vm.stop()
            vm.release()


    def test_content_detect_opencv_videocap(self, print_runtime=True):
        
        cap = cv2.VideoCapture(TEST_VIDEO_FILE)
        sm = SceneManager()
        sm.add_detector(scenedetect.scene_manager.ContentDetectorNew())
        
        try:
            t0 = time.time()

            video_fps = cap.get(cv2.CAP_PROP_FPS)
            duration = FrameTimecode('00:00:05', video_fps)

            sm.detect_scenes(frame_source = cap, end_frame = duration)

            if print_runtime:
                print("Ran in %.1f seconds." % (time.time() - t0))

        finally:
            cap.release()



