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

from scenedetect.frame_timecode import FrameTimecode

from scenedetect.scene_manager import SceneManager
from scenedetect.detectors import ContentDetector

from scenedetect.video_manager import VideoManager

from scenedetect.stats_manager import StatsManager
from scenedetect.stats_manager import get_stats_reader
from scenedetect.stats_manager import get_stats_writer
from scenedetect.stats_manager import FrameMetricRegistered
from scenedetect.stats_manager import FrameMetricNotRegistered
from scenedetect.stats_manager import StatsFileCorrupt
from scenedetect.stats_manager import StatsFileFramerateMismatch
from scenedetect.stats_manager import NoMetricsRegistered
from scenedetect.stats_manager import NoMetricsSet


import cv2

TEST_VIDEO_FILE = 'testvideo.mp4'

TEST_STATS_FILES = ['TEST_STATS_FILE'] * 4
TEST_STATS_FILES = ['%s_%012d.csv' % (stats_file, random.randint(0, 10**12))
    for stats_file in TEST_STATS_FILES]

# pylint: disable=protected-access

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


    def test_metrics(self):

        stats = StatsManager()
        metric_keys = ['some_metric', 'another_metric']
        frame_key = 100
        self.assertFalse(stats.is_save_required())

        stats.register_metrics(metric_keys)

        self.assertFalse(stats.is_save_required())
        self.assertRaises(FrameMetricRegistered, stats.register_metrics, metric_keys)
        
        self.assertFalse(stats.metrics_exist(frame_key, metric_keys))
        self.assertEqual(stats.get_metrics(frame_key, metric_keys), [None] * len(metric_keys))

        metric_values = { metric_keys[0]: 1.2345, metric_keys[1]: 6.7890 }

        stats.set_metrics(frame_key, metric_values)

        self.assertTrue(stats.is_save_required())

        self.assertTrue(stats.metrics_exist(frame_key, metric_keys))
        self.assertTrue(stats.metrics_exist(frame_key, metric_keys[1:]))

        self.assertEqual(
            stats.get_metrics(frame_key, metric_keys), [metric_values[metric_key] for metric_key in metric_keys])


    def test_detector_metrics(self):
        
        video_manager = VideoManager([TEST_VIDEO_FILE])
        stats_manager = StatsManager()
        scene_manager = SceneManager(stats_manager)
        base_timecode = video_manager.get_base_timecode()

        self.assertEqual(len(stats_manager._registered_metrics), 0)
        scene_manager.add_detector(ContentDetector())
        # add_detector should trigger register_metrics in the StatsManager.
        self.assertGreater(len(stats_manager._registered_metrics), 0)
        
        try:
            video_fps = video_manager.get_framerate()
            start_time = FrameTimecode('00:00:00', video_fps)
            duration = FrameTimecode('00:00:20', video_fps)
            
            video_manager.set_duration(start_time=start_time, end_time=duration)
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)

            # Check that metrics were written to the StatsManager.
            self.assertGreater(len(stats_manager._frame_metrics), 0)
            frame_key = min(stats_manager._frame_metrics.keys())
            self.assertGreater(len(stats_manager._frame_metrics[frame_key]), 0)
            self.assertTrue(
                stats_manager.metrics_exist(frame_key, list(stats_manager._registered_metrics)))

            # Since we only added 1 detector, the number of metrics from get_metrics
            # should equal the number of metric keys in _registered_metrics.
            self.assertEqual(
                len(stats_manager.get_metrics(frame_key, list(stats_manager._registered_metrics))),
                len(stats_manager._registered_metrics))

        finally:
            video_manager.stop()
            video_manager.release()


    def test_load_empty_stats(self):

        try:
            stats_file = open(TEST_STATS_FILES[0], 'w')

            stats_file.close()
            stats_file = open(TEST_STATS_FILES[0], 'r')

            stats_manager = StatsManager()
            
            stats_reader = get_stats_reader(stats_file)
            stats_manager.load_from_csv(stats_reader)

        finally:
            stats_file.close()

            os.remove(TEST_STATS_FILES[0])


    def test_load_hardcoded_file(self):

        from scenedetect.stats_manager import COLUMN_NAME_FPS
        from scenedetect.stats_manager import COLUMN_NAME_FRAME_NUMBER
        from scenedetect.stats_manager import COLUMN_NAME_TIMECODE

        stats_manager = StatsManager()
        stats_file = open(TEST_STATS_FILES[0], 'w')

        try:
            stats_writer = get_stats_writer(stats_file)

            some_metric_key = 'some_metric'
            some_metric_value = 1.2
            some_frame_key = 100
            base_timecode = FrameTimecode(0, 29.97)
            some_frame_timecode = base_timecode + some_frame_key

            # Write out a valid file.
            stats_writer.writerow([COLUMN_NAME_FPS, '%.10f' % base_timecode.get_framerate()])
            stats_writer.writerow(
                [COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE, some_metric_key])
            stats_writer.writerow(
                [some_frame_key, some_frame_timecode.get_timecode(), str(some_metric_value)])

            stats_file.close()

            stats_file = open(TEST_STATS_FILES[0], 'r')
            stats_manager.load_from_csv(csv_file=stats_file, base_timecode=base_timecode)

            # Check that we decoded the correct values.
            self.assertTrue(stats_manager.metrics_exist(some_frame_key, [some_metric_key]))
            self.assertAlmostEqual(stats_manager.get_metrics(some_frame_key, [some_metric_key])[0], some_metric_value)
            
        finally:
            stats_file.close()
            os.remove(TEST_STATS_FILES[0])


    def test_save_load_from_video(self):

        video_manager = VideoManager([TEST_VIDEO_FILE])
        stats_manager = StatsManager()
        scene_manager = SceneManager(stats_manager)

        base_timecode = video_manager.get_base_timecode()

        scene_manager.add_detector(ContentDetector())
        
        try:
            video_fps = video_manager.get_framerate()
            start_time = FrameTimecode('00:00:00', video_fps)
            duration = FrameTimecode('00:00:20', video_fps)
            
            video_manager.set_duration(start_time=start_time, end_time=duration)
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)

            with open(TEST_STATS_FILES[0], 'w') as stats_file:
                stats_manager.save_to_csv(stats_file, base_timecode)

            stats_manager_new = StatsManager()

            with open(TEST_STATS_FILES[0], 'r') as stats_file:
                stats_manager_new.load_from_csv(stats_file, base_timecode)

            # Choose the first available frame key and compare all metrics in both.
            frame_key = min(stats_manager._frame_metrics.keys())
            metric_keys = list(stats_manager._registered_metrics)
            
            self.assertTrue(stats_manager.metrics_exist(frame_key, metric_keys))
            orig_metrics = stats_manager.get_metrics(frame_key, metric_keys)
            new_metrics = stats_manager_new.get_metrics(frame_key, metric_keys)

            for i, metric_val in enumerate(orig_metrics):
                self.assertAlmostEqual(metric_val, new_metrics[i])

        finally:
            os.remove(TEST_STATS_FILES[0])

            video_manager.stop()
            video_manager.release()


    def test_load_corrupt_stats(self):

        from scenedetect.stats_manager import COLUMN_NAME_FPS
        from scenedetect.stats_manager import COLUMN_NAME_FRAME_NUMBER
        from scenedetect.stats_manager import COLUMN_NAME_TIMECODE

        stats_manager = StatsManager()

        stats_files = [open(stats_file, 'wt') for stats_file in TEST_STATS_FILES]
        try:

            stats_writers = [get_stats_writer(stats_file) for stats_file in stats_files]

            some_metric_key = 'some_metric'
            some_metric_value = str(1.2)
            some_frame_key = 100
            base_timecode = FrameTimecode(0, 29.97)
            some_frame_timecode = base_timecode + some_frame_key

            # Write out some invalid files.
            # File 0: Blank FPS [StatsFileCorrupt]
            stats_writers[0].writerow([COLUMN_NAME_FPS])
            stats_writers[0].writerow(
                [COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE, some_metric_key])
            stats_writers[0].writerow(
                [some_frame_key, some_frame_timecode.get_timecode(), some_metric_value])

            # File 1: Invalid FPS [StatsFileCorrupt]
            stats_writers[1].writerow([COLUMN_NAME_FPS, '%0.10f' % 0.0000001])
            stats_writers[1].writerow(
                [COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE, some_metric_key])
            stats_writers[1].writerow(
                [some_frame_key, some_frame_timecode.get_timecode(), some_metric_value])

            # File 2: Wrong FPS [StatsFileFramerateMismatch]
            stats_writers[2].writerow(
                [COLUMN_NAME_FPS, '%.10f' % (base_timecode.get_framerate() / 2.0)])
            stats_writers[2].writerow(
                [COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE, some_metric_key])
            stats_writers[2].writerow(
                [some_frame_key, some_frame_timecode.get_timecode(), some_metric_value])

            # File 3: Wrong Header Names [StatsFileCorrupt]
            stats_writers[3].writerow([COLUMN_NAME_FPS, '%.10f' % base_timecode.get_framerate()])
            stats_writers[3].writerow(
                [COLUMN_NAME_TIMECODE, COLUMN_NAME_FRAME_NUMBER, some_metric_key])
            stats_writers[3].writerow(
                [some_frame_key, some_frame_timecode.get_timecode(), some_metric_value])
            [stats_file.close() for stats_file in stats_files]

            stats_files = [open(stats_file, 'rt') for stats_file in TEST_STATS_FILES]

            self.assertRaises(StatsFileCorrupt, stats_manager.load_from_csv,
                              stats_files[0], base_timecode)
            self.assertRaises(StatsFileCorrupt, stats_manager.load_from_csv,
                              stats_files[1], base_timecode)
            self.assertRaises(StatsFileFramerateMismatch, stats_manager.load_from_csv,
                              stats_files[2], base_timecode)
            self.assertRaises(StatsFileCorrupt, stats_manager.load_from_csv,
                              stats_files[3], base_timecode)

        finally:
            [stats_file.close() for stats_file in stats_files]
            [os.remove(stats_file) for stats_file in TEST_STATS_FILES]
