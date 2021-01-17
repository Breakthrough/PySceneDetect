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

""" PySceneDetect scenedetect.stats_manager Tests

This file includes unit tests for the scenedetect.stats_manager module (specifically,
the StatsManager object, used to coordinate caching of frame metrics to/from a CSV
file to speed up subsequent calls to detect_scenes on a SceneManager.

These tests rely on the SceneManager, VideoManager, and ContentDetector classes.

These tests also require the testvideo.mp4 (see test_scene_manager.py for download
instructions), however any other valid video file can be used as well by modifying
the fixture test_video_file in conftest.py.

Additionally, these tests will create, write to, and read from files which use names
TEST_STATS_FILE_XXXXXXXXXXXX.csv, where the X's will be replaced with random digits.
These files will be deleted, if possible, after the tests are completed running.
"""

# Standard project pylint disables for unit tests using pytest.
# pylint: disable=no-self-use, protected-access, multiple-statements, invalid-name
# pylint: disable=redefined-outer-name


# Standard Library Imports
import os
import random

# Third-Party Library Imports
import pytest

# PySceneDetect Library Imports
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_manager import VideoManager
from scenedetect.detectors import ContentDetector

from scenedetect.platform import get_csv_reader
from scenedetect.platform import get_csv_writer

from scenedetect.stats_manager import StatsManager
from scenedetect.stats_manager import FrameMetricRegistered
from scenedetect.stats_manager import StatsFileCorrupt

from scenedetect.stats_manager import COLUMN_NAME_FRAME_NUMBER
from scenedetect.stats_manager import COLUMN_NAME_TIMECODE

# TODO: The following exceptions still require test cases:
from scenedetect.stats_manager import FrameMetricNotRegistered
from scenedetect.stats_manager import NoMetricsRegistered
from scenedetect.stats_manager import NoMetricsSet


# TODO: Replace TEST_STATS_FILES with a @pytest.fixture called generate_stats_file.
#       It should generate the path to a random stats file for use in a test case.
TEST_STATS_FILES = ['TEST_STATS_FILE'] * 4
TEST_STATS_FILES = ['%s_%012d.csv' % (stats_file, random.randint(0, 10**12))
                    for stats_file in TEST_STATS_FILES]


def teardown_module():
    # type: () -> None
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

    assert stats.get_metrics(frame_key, metric_keys) == [
        metric_dict[metric_key] for metric_key in metric_keys]


def test_detector_metrics(test_video_file):
    """ Test passing StatsManager to a SceneManager and using it for storing the frame metrics
    from a ContentDetector.
    """
    video_manager = VideoManager([test_video_file])
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)
    #base_timecode = video_manager.get_base_timecode()

    assert not stats_manager._registered_metrics
    scene_manager.add_detector(ContentDetector())
    # add_detector should trigger register_metrics in the StatsManager.
    assert stats_manager._registered_metrics

    try:
        video_fps = video_manager.get_framerate()
        start_time = FrameTimecode('00:00:00', video_fps)
        duration = FrameTimecode('00:00:20', video_fps)

        video_manager.set_duration(start_time=start_time, end_time=duration)
        video_manager.set_downscale_factor()
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)

        # Check that metrics were written to the StatsManager.
        assert stats_manager._frame_metrics
        frame_key = min(stats_manager._frame_metrics.keys())
        assert stats_manager._frame_metrics[frame_key]
        assert stats_manager.metrics_exist(frame_key, list(stats_manager._registered_metrics))

        # Since we only added 1 detector, the number of metrics from get_metrics
        # should equal the number of metric keys in _registered_metrics.
        assert len(stats_manager.get_metrics(
            frame_key, list(stats_manager._registered_metrics))) == len(
                stats_manager._registered_metrics)

    finally:
        video_manager.release()


def test_load_empty_stats():
    """ Test loading an empty stats file, ensuring it results in no errors. """

    open(TEST_STATS_FILES[0], 'w').close()

    with open(TEST_STATS_FILES[0], 'r') as stats_file:

        stats_manager = StatsManager()

        stats_reader = get_csv_reader(stats_file)
        stats_manager.load_from_csv(stats_reader)



def test_load_hardcoded_file():
    """ Test loading a stats file with some hard-coded data generated by this test case. """

    stats_manager = StatsManager()
    with open(TEST_STATS_FILES[0], 'w') as stats_file:

        stats_writer = get_csv_writer(stats_file)

        some_metric_key = 'some_metric'
        some_metric_value = 1.2
        some_frame_key = 100
        base_timecode = FrameTimecode(0, 29.97)
        some_frame_timecode = base_timecode + some_frame_key

        # Write out a valid file.
        stats_writer.writerow(
            [COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE, some_metric_key])
        stats_writer.writerow(
            [some_frame_key, some_frame_timecode.get_timecode(), str(some_metric_value)])

        stats_file.close()

        stats_file = open(TEST_STATS_FILES[0], 'r')
        stats_manager.load_from_csv(csv_file=stats_file)

        # Check that we decoded the correct values.
        assert stats_manager.metrics_exist(some_frame_key, [some_metric_key])
        assert stats_manager.get_metrics(
            some_frame_key, [some_metric_key])[0] == pytest.approx(some_metric_value)



def test_load_hardcoded_file_backwards_compat():
    """ Test loading a stats file with some hard-coded data generated by this test case.

    Ensures backwards compatibility with old statsfiles which included an addional header.
    """

    stats_manager = StatsManager()
    with open(TEST_STATS_FILES[0], 'w') as stats_file:
        stats_writer = get_csv_writer(stats_file)

        some_metric_key = 'some_metric'
        some_metric_value = 1.2
        some_frame_key = 100
        base_timecode = FrameTimecode(0, 29.97)
        some_frame_timecode = base_timecode + some_frame_key

        # Write out a valid file as per PySceneDetect v0.5.4 and prior.
        stats_writer.writerow(
            ['Video Framerate', '23.976'])
        stats_writer.writerow(
            [COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE, some_metric_key])
        stats_writer.writerow(
            [some_frame_key, some_frame_timecode.get_timecode(), str(some_metric_value)])

        stats_file.close()

        stats_file = open(TEST_STATS_FILES[0], 'r')
        stats_manager.load_from_csv(csv_file=stats_file)

        # Check that we decoded the correct values.
        assert stats_manager.metrics_exist(some_frame_key, [some_metric_key])
        assert stats_manager.get_metrics(
            some_frame_key, [some_metric_key])[0] == pytest.approx(some_metric_value)


def test_save_load_from_video(test_video_file):
    """ Test generating and saving some frame metrics from TEST_VIDEO_FILE to a file on disk, and
    loading the file back to ensure the loaded frame metrics agree with those that were saved.
    """
    video_manager = VideoManager([test_video_file])
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)

    base_timecode = video_manager.get_base_timecode()

    scene_manager.add_detector(ContentDetector())

    try:
        video_fps = video_manager.get_framerate()
        start_time = FrameTimecode('00:00:00', video_fps)
        duration = FrameTimecode('00:00:20', video_fps)

        video_manager.set_duration(start_time=start_time, end_time=duration)
        video_manager.set_downscale_factor()
        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)

        with open(TEST_STATS_FILES[0], 'w') as stats_file:
            stats_manager.save_to_csv(stats_file, base_timecode)

        stats_manager_new = StatsManager()

        with open(TEST_STATS_FILES[0], 'r') as stats_file:
            stats_manager_new.load_from_csv(stats_file)

        # Choose the first available frame key and compare all metrics in both.
        frame_key = min(stats_manager._frame_metrics.keys())
        metric_keys = list(stats_manager._registered_metrics)

        assert stats_manager.metrics_exist(frame_key, metric_keys)
        orig_metrics = stats_manager.get_metrics(frame_key, metric_keys)
        new_metrics = stats_manager_new.get_metrics(frame_key, metric_keys)

        for i, metric_val in enumerate(orig_metrics):
            assert metric_val == pytest.approx(new_metrics[i])

    finally:
        video_manager.release()


def test_load_corrupt_stats():
    """ Test loading a corrupted stats file created by outputting data in the wrong format. """

    stats_manager = StatsManager()

    with open(TEST_STATS_FILES[0], 'wt') as stats_file:
        stats_writer = get_csv_writer(stats_file)

        some_metric_key = 'some_metric'
        some_metric_value = str(1.2)
        some_frame_key = 100
        base_timecode = FrameTimecode(0, 29.97)
        some_frame_timecode = base_timecode + some_frame_key

        # Write out some invalid files.

        # File #0: Wrong Header Names [StatsFileCorrupt]
        # Swapped timecode & frame number.
        stats_writer.writerow(
            [COLUMN_NAME_TIMECODE, COLUMN_NAME_FRAME_NUMBER, some_metric_key])
        stats_writer.writerow(
            [some_frame_key, some_frame_timecode.get_timecode(), some_metric_value])

        stats_file.close()

        with pytest.raises(StatsFileCorrupt):
            stats_manager.load_from_csv(TEST_STATS_FILES[0])
