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


def test_backwards_compatibility(test_video_file: str):
    """Test backwards compatibility wrapper for VideoManager. This is equivalent to the
    api_test.py file from v0.5. See `test_api_stats_manager` in test_api.py for how this
    should be written using the v0.6 API."""
    video_manager = VideoManager([test_video_file])
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)
    scene_manager.add_detector(ContentDetector())
    base_timecode = video_manager.get_base_timecode()
    stats_file_path = test_video_file + '.csv'
    try:
        # If stats file exists, load it.
        if os.path.exists(stats_file_path):
            # Read stats from CSV file opened in read mode:
            with open(stats_file_path, 'r') as stats_file:
                # TODO(v0.6): Fix.
                #stats_manager.load_from_csv(stats_file)
                pass

        start_time = base_timecode + 20 # 00:00:00.667
        end_time = base_timecode + 20.0 # 00:00:20.000
                                        # Set video_manager duration to read frames from 00:00:00 to 00:00:20.
        video_manager.set_duration(start_time=start_time, end_time=end_time)

        # Set downscale factor to improve processing speed.
        video_manager.set_downscale_factor()

        # Start video_manager.
        video_manager.start()

        # TODO(v0.6): Add back `frame_source=video_manager`
        scene_manager.detect_scenes(video_manager)

        scene_list = scene_manager.get_scene_list()
        # Like FrameTimecodes, each scene in the scene_list can be sorted if the
        # list of scenes becomes unsorted.

        print('List of scenes obtained:')
        for i, scene in enumerate(scene_list):
            print('    Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
                i + 1,
                scene[0].get_timecode(),
                scene[0].get_frames(),
                scene[1].get_timecode(),
                scene[1].get_frames(),
            ))

        # We only write to the stats file if a save is required:
        if stats_manager.is_save_required():
            with open(stats_file_path, 'w') as stats_file:
                # TODO(v0.6): Fix.
                #stats_manager.save_to_csv(stats_file, base_timecode)
                pass

    finally:
        video_manager.release()


def test_backwards_compatibility_with_stats(test_video_file: str):
    """Same as above, but runs twice to use the statsfile."""
    test_backwards_compatibility(test_video_file)
    test_backwards_compatibility(test_video_file)

