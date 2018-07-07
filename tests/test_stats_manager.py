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

""" PySceneDetect scenedetect.stats_manager Tests

This file includes unit tests for the scenedetect.stats_manager module (specifically,
the StatsManager object, used to coordinate caching of frame metrics to/from a CSV
file to speed up subsequent calls to detect_scenes on a SceneManager.

These tests rely on the SceneManager, VideoManager, and ContentDetector classes.

These tests also require the testvideo.mp4 (see test_scene_manager.py for download
instructions), however any other valid video file can be used as well by setting the
global variable TEST_VIDEO_FILE to the name of the file to use.

Additionally, these tests will create, write to, and read from files which use names
TEST_STATS_FILE_XXXXXXXXXXXX.csv, where the X's will be replaced with random digits.
These files will be deleted, if possible, after the tests are completed running.
"""

import unittest
import time
import os
import csv
import random

import scenedetect

from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode

from scenedetect.video_manager import VideoManager
from scenedetect.video_manager_async import VideoManagerAsync

from scenedetect.stats_manager import StatsManager


import cv2

TEST_VIDEO_FILE = 'testvideo.mp4'

TEST_STATS_FILES = ['TEST_STATS_FILE' * 3]
TEST_STATS_FILES = ['%s_%012d.csv' % (stats_file, random.randint(0, 10**12))
    for stats_file in TEST_STATS_FILES]

class TestStatsManager(unittest.TestCase):
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
    def test_save_stats(self, print_runtime=True):
        
        video_manager = VideoManager([TEST_VIDEO_FILE])
        stats_manager = StatsManager()
        scene_manager = SceneManager(stats_manager)

        base_timecode = video_manager.get_base_timecode()

        scene_manager.add_detector(scenedetect.scene_manager.ContentDetectorNew())
        
        try:
            t0 = time.time()

            video_fps = video_manager.get_framerate()
            start_time = FrameTimecode('00:00:00', video_fps)
            duration = FrameTimecode('00:00:20', video_fps)
            
            video_manager.set_duration(start_time=start_time, end_time=duration)
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)

            if print_runtime:
                print("Ran in %.1f seconds." % (time.time() - t0))


            print("Found %d cuts." % len(scene_manager.get_cutting_list()))

            with open(TEST_STATS_FILES[0], 'w') as stats_file:
                print("Saving stats to %s..." % TEST_STATS_FILES[0])
                stats_writer = csv.writer(stats_file)
                stats_manager.save_to_csv(stats_writer, base_timecode)


        finally:
            video_manager.stop()
            video_manager.release()
