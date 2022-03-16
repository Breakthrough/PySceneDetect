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
"""Test for compatibility with v0.5 API.

Do not use this file as examples or in production code - see `test_api.py` instead.

The whole API is not compatible, but the compatibility layer makes the high level examples
work without modification.
"""

import os

from scenedetect import SceneManager, StatsManager, VideoManager, ContentDetector

# TODO(v0.6):
# - [ ] Test output is same versus api_test.py in main/v0.5 branch
# - [ ] Test output is same versus api_test.py on second run that uses statsfile


def validate_backwards_compatibility(test_video_file: str, stats_file_path: str):
    """Validate backwards compatibility wrapper for VideoManager. This is equivalent to the
    tests/api_test.py file from v0.5. See `test_api_stats_manager` in test_api.py for how this
    should be written using the v0.6 API."""
    video_manager = VideoManager([test_video_file])
    stats_file_path = test_video_file + '.csv'
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)
    scene_manager.add_detector(ContentDetector())
    base_timecode = video_manager.get_base_timecode()
    scene_list = []
    try:
        start_time = base_timecode + 20 # 00:00:00.667
        end_time = base_timecode + 20.0 # 00:00:20.000

        if os.path.exists(stats_file_path):
            with open(stats_file_path, 'r') as stats_file:
                stats_manager.load_from_csv(stats_file)
            # ContentDetector requires at least 1 frame before it can calculate any metrics.
            assert stats_manager.metrics_exist(start_time.get_frames() + 1,
                                               [ContentDetector.FRAME_SCORE_KEY])
            # Correct end frame # for presentation duration.
            assert stats_manager.metrics_exist(end_time.get_frames() - 1,
                                               [ContentDetector.FRAME_SCORE_KEY])

        video_manager.set_duration(start_time=start_time, end_time=end_time)
        video_manager.set_downscale_factor()
        video_manager.start()
        assert video_manager.get_current_timecode().get_frames() == start_time.get_frames()

        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list()

        # Correct end frame # for presentation duration.
        assert video_manager.get_current_timecode().get_frames() == end_time.get_frames() + 1

        print('List of scenes obtained:')
        for i, scene in enumerate(scene_list):
            print('    Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
                i + 1,
                scene[0].get_timecode(),
                scene[0].get_frames(),
                scene[1].get_timecode(),
                scene[1].get_frames(),
            ))

        if stats_manager.is_save_required():
            with open(stats_file_path, 'w') as stats_file:
                stats_manager.save_to_csv(stats_file, base_timecode)
    finally:
        video_manager.release()
    return scene_list


def test_backwards_compatibility_with_stats(test_video_file: str):
    """Runs equivalent code to `tests/api_test.py` from v0.5 twice to also
    exercise loading a statsfile from disk."""
    stats_file_path = test_video_file + '.csv'
    try:
        os.remove(stats_file_path)
    except FileNotFoundError:
        pass
    scenes = validate_backwards_compatibility(test_video_file, stats_file_path)
    assert scenes
    assert os.path.exists(stats_file_path)
    # Make sure run with statsfile matches previous results.
    assert validate_backwards_compatibility(test_video_file, stats_file_path) == scenes
    os.remove(stats_file_path)