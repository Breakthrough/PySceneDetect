#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect API Tests

These tests demonstrate common workflow patterns used when integrating the PySceneDetect API."""


def test_api_detect(test_video_file: str):
    """Demonstrate usage of the `detect()` function to process a complete video."""
    from scenedetect import ContentDetector, detect

    scene_list = detect(test_video_file, ContentDetector())
    for i, scene in enumerate(scene_list):
        print(f"Scene {i + 1}: {scene[0].get_timecode()} - {scene[1].get_timecode()}")


def test_api_detect_start_end_time(test_video_file: str):
    """Demonstrate usage of the `detect()` function to process a subset of a video."""
    from scenedetect import ContentDetector, detect

    # Times can be seconds (float), frames (int), or timecode 'HH:MM:SSS.nnn' (str).
    # See test_api_timecode_types() for examples of each format.
    scene_list = detect(test_video_file, ContentDetector(), start_time=10.5, end_time=15.9)
    for i, scene in enumerate(scene_list):
        print(f"Scene {i + 1}: {scene[0].get_timecode()} - {scene[1].get_timecode()}")


def test_api_detect_stats(test_video_file: str):
    """Demonstrate usage of the `detect()` function to generate a statsfile."""
    from scenedetect import ContentDetector, detect

    detect(test_video_file, ContentDetector(), stats_file_path="frame_metrics.csv")


def test_api_scene_manager(test_video_file: str):
    """Demonstrate how to use a SceneManager to implement a function similar to `detect()`."""
    from scenedetect import ContentDetector, SceneManager, open_video

    video = open_video(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()
    for i, scene in enumerate(scene_list):
        print(f"Scene {i + 1}: {scene[0].get_timecode()} - {scene[1].get_timecode()}")


def test_api_scene_manager_start_end_time(test_video_file: str):
    """Demonstrate how to use a SceneManager to process a subset of the input video."""
    from scenedetect import ContentDetector, SceneManager, open_video

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
        print(f"Scene {i + 1}: {scene[0].get_timecode()} - {scene[1].get_timecode()}")


def test_api_timecode_types():
    """Demonstrate all different types of timecodes that can be used."""
    from scenedetect import FrameTimecode

    base_timecode = FrameTimecode(timecode=0, fps=10.0)
    # Frames (int)
    timecode = base_timecode + 1
    assert timecode.frame_num == 1
    # Seconds (float)
    timecode = base_timecode + 1.0
    assert timecode.frame_num == 10
    # Timecode (str, 'HH:MM:SS' or 'HH:MM:SSS.nnn')
    timecode = base_timecode + "00:00:01.500"
    assert timecode.frame_num == 15
    # Seconds (str, 'SSSs' or 'SSSS.SSSs')
    timecode = base_timecode + "1.5s"
    assert timecode.frame_num == 15


def test_api_stats_manager(test_video_file: str):
    """Demonstrate using a StatsManager to save per-frame statistics to disk."""
    from scenedetect import ContentDetector, SceneManager, StatsManager, open_video

    video = open_video(test_video_file)
    scene_manager = SceneManager(stats_manager=StatsManager())
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    # Save per-frame statistics to disk.
    filename = f"{test_video_file}.stats.csv"
    assert scene_manager.stats_manager is not None
    scene_manager.stats_manager.save_to_csv(csv_file=filename)


def test_api_scene_manager_callback(test_video_file: str):
    """Demonstrate how to use a callback with the SceneManager detect_scenes method."""
    import numpy

    from scenedetect import ContentDetector, FrameTimecode, SceneManager, open_video

    # Callback to invoke on the first frame of every new scene detection.
    def on_new_scene(frame_img: numpy.ndarray, position: FrameTimecode):
        print(f"New scene found at frame {position.frame_num}.")

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

    from scenedetect import ContentDetector, FrameTimecode, SceneManager, VideoCaptureAdapter

    # Callback to invoke on the first frame of every new scene detection.
    def on_new_scene(frame_img: numpy.ndarray, position: FrameTimecode):
        print(f"New scene found at frame {position.frame_num}.")

    # We open a file just for test purposes, but we can also use a device or pipe here.
    cap = cv2.VideoCapture(test_video_file)
    video = VideoCaptureAdapter(cap)
    # Now `video` can be used as normal with a `SceneManager`. If the input is non-terminating,
    # either set `end_time/duration` when calling `detect_scenes`, or call `scene_manager.stop()`.
    total_frames = 1000
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video, duration=total_frames, callback=on_new_scene)


# TODO(v0.8): Remove this test when these deprecated modules are removed from the codebase.
def test_deprecated_modules_emits_warning_on_import():
    import importlib

    import pytest

    SCENE_DETECTOR_WARNING = (
        "The `scene_detector` submodule is deprecated, import from the base package instead."
    )
    with pytest.warns(DeprecationWarning, match=SCENE_DETECTOR_WARNING):
        importlib.import_module("scenedetect.scene_detector")

    FRAME_TIMECODE_WARNING = (
        "The `frame_timecode` submodule is deprecated, import from the base package instead."
    )
    with pytest.warns(DeprecationWarning, match=FRAME_TIMECODE_WARNING):
        importlib.import_module("scenedetect.frame_timecode")

    VIDEO_SPLITTER_WARNING = (
        "The `video_splitter` submodule is deprecated, import from the base package instead."
    )
    with pytest.warns(DeprecationWarning, match=VIDEO_SPLITTER_WARNING):
        importlib.import_module("scenedetect.video_splitter")
