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

Demonstrates high-level usage of the PySceneDetect API.
"""

from typing import List, Tuple

from scenedetect import open_video, ContentDetector, FrameTimecode, SceneManager, StatsManager
from scenedetect.backends import VideoStreamCv2

STATS_FILE_PATH = 'api_test_statsfile.csv'


def print_scenes(scene_list: List[Tuple[FrameTimecode, FrameTimecode]]):
    """Iterate over a scene list and print it to the terminal."""
    print('Scene List:')
    for i, scene in enumerate(scene_list):
        print('  Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
            i + 1,
            scene[0].get_timecode(),
            scene[0].get_frames(),
            scene[1].get_timecode(),
            scene[1].get_frames(),
        ))


def test_api_start_end_time(test_video_file: str):
    """Demonstrate processing a subsection of a video based on a starting/ending time."""
    video = open_video(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    # See FrameTimecode docs or test_api_timecode_types for all
    # supported timecode formats.
    start_time = 20 # Start at frame (int) 20
    end_time = 15.0 # End at 15 seconds (float)
    video.seek(start_time)

    # Can specify `duration` instead of `end_time`.
    scene_manager.detect_scenes(video=video, end_time=end_time)
    scene_list = scene_manager.get_scene_list()
    print_scenes(scene_list=scene_list)


def test_api_stats_manager(test_video_file: str):
    """Demonstrate using a StatsManager to save and optionally load stats from disk."""
    video = open_video(test_video_file)
    scene_manager = SceneManager(stats_manager=StatsManager())
    scene_manager.add_detector(ContentDetector())
    # Loading from disk is optional.
    scene_manager.stats_manager.load_from_csv(path=STATS_FILE_PATH)
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()
    print_scenes(scene_list=scene_list)
    # Save per-frame statistics to disk.
    scene_manager.stats_manager.save_to_csv(path=STATS_FILE_PATH)


def test_api_video_stream_opencv(test_video_file: str):
    """Demonstrate constructing and using a VideoStream backend."""
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
