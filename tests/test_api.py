# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect API Tests

Demonstrates high-level usage of the PySceneDetect API. These tests are provided for
examples of common use cases, and only validate semantic correctness.
"""

from typing import List, Tuple

from scenedetect import detect, open_video
from scenedetect import ContentDetector, FrameTimecode, SceneManager, StatsManager
from scenedetect.backends import VideoStreamCv2

STATS_FILE_PATH = 'api_test_statsfile.csv'


def print_scenes(scene_list: List[Tuple[FrameTimecode, FrameTimecode]]):
    """Helper function to print a list of scenes to the terminal."""
    print('Scene List:')
    for i, scene in enumerate(scene_list):
        print('  Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
            i + 1,
            scene[0].get_timecode(),
            scene[0].get_frames(),
            scene[1].get_timecode(),
            scene[1].get_frames(),
        ))


def test_api_detect(test_video_file: str):
    """Demonstrate usage of the `detect()` function to process a complete video."""
    scene_list = detect(test_video_file, ContentDetector())
    print_scenes(scene_list=scene_list)


def test_api_detect_start_end_time(test_video_file: str):
    """Demonstrate usage of the `detect()` function to process a subset of a video."""
    # Can specify start/end time in seconds (float), frames (int), or timecode 'HH:MM:SSS.nnn' (str)
    scene_list = detect(test_video_file, ContentDetector(), start_time=10.5, end_time=20.9)
    print_scenes(scene_list=scene_list)


def test_api_detect_stats(test_video_file: str):
    """Demonstrate usage of the `detect()` function to generate a statsfile."""
    detect(test_video_file, ContentDetector(), stats_file_path="frame_metrics.csv")


def test_api_scene_manager(test_video_file: str):
    """Demonstrate how to use a SceneManager to implement a function similar to `detect()`."""
    video = open_video(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()
    print_scenes(scene_list=scene_list)


def test_api_scene_manager_start_end_time(test_video_file: str):
    """Demonstrate how to use a SceneManager to process a subset of the input video."""
    video = open_video(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    # See test_api_timecode_types below for all supported timecode formats.
    start_time = 20 # Start at frame (int) 20
    end_time = 15.0 # End at 15 seconds (float)
    video.seek(start_time)

    # Can also specify `duration` instead of `end_time`.
    scene_manager.detect_scenes(video=video, end_time=end_time)
    scene_list = scene_manager.get_scene_list()
    print_scenes(scene_list=scene_list)


def test_api_stats_manager(test_video_file: str):
    """Demonstrate using a StatsManager with a SceneManager to save per-frame statistics to disk."""
    video = open_video(test_video_file)
    scene_manager = SceneManager(stats_manager=StatsManager())
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()
    print_scenes(scene_list=scene_list)
    # Save per-frame statistics to disk.
    scene_manager.stats_manager.save_to_csv(csv_file=STATS_FILE_PATH)


def test_api_video_stream_opencv(test_video_file: str):
    """Demonstrate constructing and using a VideoStream backend directly, instead of
    using the `open_video` function. Only VideoStreamCv2 is guaranteed to be available.
    Applications that do not require a specific backend library should use `open_video`.
    """
    video = VideoStreamCv2(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()
    print_scenes(scene_list=scene_list)


def test_api_timecode_types():
    """Demonstrate all different types of timecodes that can be used."""
    base_timecode = FrameTimecode(timecode=0, fps=10.0)
    # Frames (int)
    timecode = base_timecode + 1
    assert timecode.get_frames() == 1
    # Seconds (float)
    timecode = base_timecode + 1.0
    assert timecode.get_frames() == 10
    # Timecode (str, 'HH:MM:SS' or 'HH:MM:SSS.nnn')
    timecode = base_timecode + '00:00:01.500'
    assert timecode.get_frames() == 15
    # Seconds (str, 'SSSs' or 'SSSS.SSSs')
    timecode = base_timecode + '1.5s'
    assert timecode.get_frames() == 15
