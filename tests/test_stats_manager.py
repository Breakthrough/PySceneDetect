# -*- coding: utf-8 -*-
#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2023 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""" PySceneDetect scenedetect.stats_manager Tests

This file includes unit tests for the scenedetect.stats_manager module (specifically,
the StatsManager object, used to coordinate caching of frame metrics to/from a CSV
file to speed up subsequent calls to detect_scenes on a SceneManager.

These tests rely on the SceneManager, VifdeoStreamCv2, and ContentDetector classes.

These tests also require the testvideo.mp4 (see test_scene_manager.py for download
instructions), however any other valid video file can be used as well by modifying
the fixture test_video_file in conftest.py.

Additionally, these tests will create, write to, and read from files which use names
TEST_STATS_FILE_XXXXXXXXXXXX.csv, where the X's will be replaced with random digits.
These files will be deleted, if possible, after the tests are completed running.
"""

#pylint: disable=protected-access

import csv
import os
import random

import pytest

from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.detectors import ContentDetector

from scenedetect.stats_manager import StatsManager
from scenedetect.stats_manager import FrameMetricRegistered
from scenedetect.stats_manager import StatsFileCorrupt

from scenedetect.stats_manager import COLUMN_NAME_FRAME_NUMBER
from scenedetect.stats_manager import COLUMN_NAME_TIMECODE

# TODO(v1.0): Need to add test case which raises scenedetect.stats_manager.FrameMetricNotRegistered.

# TODO(v1.0): use https://docs.pytest.org/en/6.2.x/tmpdir.html
TEST_STATS_FILES = ['TEST_STATS_FILE'] * 4
TEST_STATS_FILES = [
    '%s_%012d.csv' % (stats_file, random.randint(0, 10**12)) for stats_file in TEST_STATS_FILES
]


def teardown_module():
    """ Removes any created stats files, if any. """
    for stats_file in TEST_STATS_FILES:
        if os.path.exists(stats_file):
            os.remove(stats_file)


def test_metrics():
    """ Test StatsManager metric registration/setting/getting with a set of pre-defined
    key-value pairs (metric_dict).
    """
    metric_dict = {'some_metric': 1.2345, 'another_metric': 6.7890}
    metric_keys = list(metric_dict.keys())

    stats = StatsManager()
    frame_key = 100
    assert not stats.is_save_required()

    stats.register_metrics(metric_keys)

    assert not stats.is_save_required()
    with pytest.raises(FrameMetricRegistered):
        stats.register_metrics(metric_keys)

    assert not stats.metrics_exist(frame_key, metric_keys)
    assert stats.get_metrics(frame_key, metric_keys) == [None] * len(metric_keys)

    stats.set_metrics(frame_key, metric_dict)

    assert stats.is_save_required()

    assert stats.metrics_exist(frame_key, metric_keys)
    assert stats.metrics_exist(frame_key, metric_keys[1:])

    assert stats.get_metrics(
        frame_key, metric_keys) == [metric_dict[metric_key] for metric_key in metric_keys]


def test_detector_metrics(test_video_file):
    """ Test passing StatsManager to a SceneManager and using it for storing the frame metrics
    from a ContentDetector.
    """
    video = VideoStreamCv2(test_video_file)
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)

    assert not stats_manager._registered_metrics
    scene_manager.add_detector(ContentDetector())
    # add_detector should trigger register_metrics in the StatsManager.
    assert stats_manager._registered_metrics

    video_fps = video.frame_rate
    duration = FrameTimecode('00:00:20', video_fps)

    scene_manager.auto_downscale = True
    scene_manager.detect_scenes(video=video, duration=duration)

    # Check that metrics were written to the StatsManager.
    assert stats_manager._frame_metrics
    frame_key = min(stats_manager._frame_metrics.keys())
    assert stats_manager._frame_metrics[frame_key]
    assert stats_manager.metrics_exist(frame_key, list(stats_manager._registered_metrics))

    # Since we only added 1 detector, the number of metrics from get_metrics
    # should equal the number of metric keys in _registered_metrics.
    assert len(stats_manager.get_metrics(frame_key, list(
        stats_manager._registered_metrics))) == len(stats_manager._registered_metrics)


def test_load_empty_stats():
    """ Test loading an empty stats file, ensuring it results in no errors. """
    open(TEST_STATS_FILES[0], 'w').close()
    stats_manager = StatsManager()
    stats_manager.load_from_csv(TEST_STATS_FILES[0])


def test_save_no_detect_scenes():
    """Test saving without calling detect_scenes."""
    stats_manager = StatsManager()
    stats_manager.save_to_csv(TEST_STATS_FILES[0])


def test_load_hardcoded_file():
    """ Test loading a stats file with some hard-coded data generated by this test case. """

    stats_manager = StatsManager()
    with open(TEST_STATS_FILES[0], 'w') as stats_file:

        stats_writer = csv.writer(stats_file, lineterminator='\n')

        some_metric_key = 'some_metric'
        some_metric_value = 1.2
        some_frame_key = 100
        base_timecode = FrameTimecode(0, 29.97)
        some_frame_timecode = base_timecode + some_frame_key

        # Write out a valid file.
        stats_writer.writerow([COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE, some_metric_key])
        stats_writer.writerow(
            [some_frame_key + 1,
             some_frame_timecode.get_timecode(),
             str(some_metric_value)])

    stats_manager.load_from_csv(TEST_STATS_FILES[0])

    # Check that we decoded the correct values.
    assert stats_manager.metrics_exist(some_frame_key, [some_metric_key])
    assert stats_manager.get_metrics(some_frame_key,
                                     [some_metric_key])[0] == pytest.approx(some_metric_value)


def test_save_load_from_video(test_video_file):
    """ Test generating and saving some frame metrics from TEST_VIDEO_FILE to a file on disk, and
    loading the file back to ensure the loaded frame metrics agree with those that were saved.
    """
    video = VideoStreamCv2(test_video_file)
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)

    scene_manager.add_detector(ContentDetector())

    video_fps = video.frame_rate
    duration = FrameTimecode('00:00:20', video_fps)

    scene_manager.auto_downscale = True
    scene_manager.detect_scenes(video, duration=duration)

    stats_manager.save_to_csv(csv_file=TEST_STATS_FILES[0])

    stats_manager_new = StatsManager()

    stats_manager_new.load_from_csv(TEST_STATS_FILES[0])

    # Choose the first available frame key and compare all metrics in both.
    frame_key = min(stats_manager._frame_metrics.keys())
    metric_keys = list(stats_manager._registered_metrics)

    assert stats_manager.metrics_exist(frame_key, metric_keys)
    orig_metrics = stats_manager.get_metrics(frame_key, metric_keys)
    new_metrics = stats_manager_new.get_metrics(frame_key, metric_keys)

    for i, metric_val in enumerate(orig_metrics):
        assert metric_val == pytest.approx(new_metrics[i])


def test_load_corrupt_stats():
    """ Test loading a corrupted stats file created by outputting data in the wrong format. """

    stats_manager = StatsManager()

    with open(TEST_STATS_FILES[0], 'wt') as stats_file:
        stats_writer = csv.writer(stats_file, lineterminator='\n')

        some_metric_key = 'some_metric'
        some_metric_value = str(1.2)
        some_frame_key = 100
        base_timecode = FrameTimecode(0, 29.97)
        some_frame_timecode = base_timecode + some_frame_key

        # Write out some invalid files.

        # File #0: Wrong Header Names [StatsFileCorrupt]
        # Swapped timecode & frame number.
        stats_writer.writerow([COLUMN_NAME_TIMECODE, COLUMN_NAME_FRAME_NUMBER, some_metric_key])
        stats_writer.writerow(
            [some_frame_key, some_frame_timecode.get_timecode(), some_metric_value])

        stats_file.close()

        with pytest.raises(StatsFileCorrupt):
            stats_manager.load_from_csv(TEST_STATS_FILES[0])
