# -*- coding: utf-8 -*-
#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect API Tests

These tests function as demonstrations of the PySceneDetect API. These tests provide examples
of common use cases, which can be integrated into applications, or used from an interactive
Python environment. When processing longer videos, it is useful to set `show_progress=True`
when calling `detect()` or `detect_scenes()`.
"""

# pylint: disable=import-outside-toplevel, redefined-outer-name, unused-argument


def test_api_detect(test_video_file: str):
    """Demonstrate usage of the `detect()` function to process a complete video."""
    from scenedetect import detect, ContentDetector

    scene_list = detect(test_video_file, ContentDetector())
    for i, scene in enumerate(scene_list):
        print(
            "Scene %d: %s - %s"
            % (i + 1, scene[0].get_timecode(), scene[1].get_timecode())
        )


def test_api_detect_start_end_time(test_video_file: str):
    """Demonstrate usage of the `detect()` function to process a subset of a video."""
    from scenedetect import detect, ContentDetector

    # Times can be seconds (float), frames (int), or timecode 'HH:MM:SSS.nnn' (str).
    # See test_api_timecode_types() for examples of each format.
    scene_list = detect(
        test_video_file, ContentDetector(), start_time=10.5, end_time=15.9
    )
    for i, scene in enumerate(scene_list):
        print(
            "Scene %d: %s - %s"
            % (i + 1, scene[0].get_timecode(), scene[1].get_timecode())
        )


def test_api_detect_stats(test_video_file: str):
    """Demonstrate usage of the `detect()` function to generate a statsfile."""
    from scenedetect import detect, ContentDetector

    detect(test_video_file, ContentDetector(), stats_file_path="frame_metrics.csv")


def test_api_scene_manager(test_video_file: str):
    """Demonstrate how to use a SceneManager to implement a function similar to `detect()`."""
    from scenedetect import SceneManager, ContentDetector, open_video

    video = open_video(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()
    for i, scene in enumerate(scene_list):
        print(
            "Scene %d: %s - %s"
            % (i + 1, scene[0].get_timecode(), scene[1].get_timecode())
        )


def test_api_scene_manager_start_end_time(test_video_file: str):
    """Demonstrate how to use a SceneManager to process a subset of the input video."""
    from scenedetect import SceneManager, ContentDetector, open_video

    video = open_video(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    # Times can be seconds (float), frames (int), or timecode 'HH:MM:SSS.nnn' (str).
    # See test_api_timecode_types() for examples of each format.
    start_time = 200  # Start at frame (int) 200
    end_time = 15.0  # End at 15 seconds (float)
    video.seek(start_time)
    scene_manager.detect_scenes(video=video, end_time=end_time)
    scene_list = scene_manager.get_scene_list()
    for i, scene in enumerate(scene_list):
        print(
            "Scene %d: %s - %s"
            % (i + 1, scene[0].get_timecode(), scene[1].get_timecode())
        )


def test_api_timecode_types():
    """Demonstrate all different types of timecodes that can be used."""
    from scenedetect import FrameTimecode

    base_timecode = FrameTimecode(timecode=0, fps=10.0)
    # Frames (int)
    timecode = base_timecode + 1
    assert timecode.get_frames() == 1
    # Seconds (float)
    timecode = base_timecode + 1.0
    assert timecode.get_frames() == 10
    # Timecode (str, 'HH:MM:SS' or 'HH:MM:SSS.nnn')
    timecode = base_timecode + "00:00:01.500"
    assert timecode.get_frames() == 15
    # Seconds (str, 'SSSs' or 'SSSS.SSSs')
    timecode = base_timecode + "1.5s"
    assert timecode.get_frames() == 15


def test_api_stats_manager(test_video_file: str):
    """Demonstrate using a StatsManager to save per-frame statistics to disk."""
    from scenedetect import SceneManager, StatsManager, ContentDetector, open_video

    video = open_video(test_video_file)
    scene_manager = SceneManager(stats_manager=StatsManager())
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    # Save per-frame statistics to disk.
    filename = "%s.stats.csv" % test_video_file
    scene_manager.stats_manager.save_to_csv(csv_file=filename)


def test_api_scene_manager_callback(test_video_file: str):
    """Demonstrate how to use a callback with the SceneManager detect_scenes method."""
    import numpy
    from scenedetect import SceneManager, ContentDetector, open_video

    # Callback to invoke on the first frame of every new scene detection.
    def on_new_scene(frame_img: numpy.ndarray, frame_num: int):
        print("New scene found at frame %d." % frame_num)

    video = open_video(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video, callback=on_new_scene)


def test_api_device_callback(test_video_file: str):
    """Demonstrate how to use a webcam/device/pipe and a callback function.
    Instead of calling `open_video()`, an existing `cv2.VideoCapture` can be used by
    wrapping it with a `VideoCaptureAdapter.`"""
    import cv2
    import numpy
    from scenedetect import SceneManager, ContentDetector, VideoCaptureAdapter

    # Callback to invoke on the first frame of every new scene detection.
    def on_new_scene(frame_img: numpy.ndarray, frame_num: int):
        print("New scene found at frame %d." % frame_num)

    # We open a file just for test purposes, but we can also use a device or pipe here.
    cap = cv2.VideoCapture(test_video_file)
    video = VideoCaptureAdapter(cap)
    # Now `video` can be used as normal with a `SceneManager`. If the input is non-terminating,
    # either set `end_time/duration` when calling `detect_scenes`, or call `scene_manager.stop()`.
    total_frames = 1000
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(
        video=video, duration=total_frames, callback=on_new_scene
    )
