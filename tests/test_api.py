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

import pytest

from scenedetect.video_stream import FrameNumbering


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
    scene_list = detect(test_video_file, ContentDetector(), start_time=10.5, end_time=15.9)
    for i, scene in enumerate(scene_list):
        print(f"Scene {i + 1}: {scene[0].get_timecode()} - {scene[1].get_timecode()}")


@pytest.mark.parametrize("start_time,end_time", [(10, 15), ("10", "15")])
@pytest.mark.parametrize(
    ("options", "expected_start", "expected_end"),
    [
        pytest.param({}, 0, 5, id="default"),
        pytest.param({"frame_numbering": FrameNumbering.RELATIVE}, 0, 5, id="relative"),
        pytest.param({"frame_numbering": FrameNumbering.SOURCE}, 10, 15, id="source"),
    ],
)
def test_api_detect_frame_numbering(
    test_video_file: str,
    start_time: int | str,
    end_time: int | str,
    options: dict[str, FrameNumbering],
    expected_start: int,
    expected_end: int,
):
    """Apply numbering mode to the detected range after an integer start seek."""
    from scenedetect import ContentDetector, detect

    scene_list = detect(
        test_video_file,
        ContentDetector(),
        start_time=start_time,
        end_time=end_time,
        start_in_scene=True,
        **options,
    )
    assert len(scene_list) == 1
    start, end = scene_list[0]
    assert start.frame_number == expected_start
    assert end.frame_number == expected_end


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
    start_time = 200  # Start at frame (int) 200
    end_time = 15.0  # End at 15 seconds (float)
    video.seek(start_time)
    scene_manager.detect_scenes(video=video, end_time=end_time)
    scene_list = scene_manager.get_scene_list()
    for i, scene in enumerate(scene_list):
        print(f"Scene {i + 1}: {scene[0].get_timecode()} - {scene[1].get_timecode()}")


def test_api_open_video_framerate_legacy_alias(test_video_file: str):
    """`open_video(framerate=...)` is the deprecated alias for `frame_rate=` (issue #548).
    Both forms must produce equivalent streams; when both are provided, `frame_rate` wins."""
    from scenedetect import open_video

    with pytest.warns(DeprecationWarning, match="frame_rate"):
        legacy = open_video(test_video_file, framerate=30.0)
    canonical = open_video(test_video_file, frame_rate=30.0)
    assert legacy.frame_rate == canonical.frame_rate
    # `frame_rate` takes precedence over `framerate` when both are provided.
    with pytest.warns(DeprecationWarning, match="frame_rate"):
        both = open_video(test_video_file, frame_rate=30.0, framerate=24.0)
    assert both.frame_rate == canonical.frame_rate


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

    from scenedetect import ContentDetector, FramePosition, SceneManager, open_video

    # Callback to invoke on the first frame of every new scene detection.
    def on_new_scene(frame_img: numpy.ndarray, position: FramePosition):
        print(f"New scene found at frame {position.frame_number}.")

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

    from scenedetect import ContentDetector, FramePosition, SceneManager, VideoCaptureAdapter

    # Callback to invoke on the first frame of every new scene detection.
    def on_new_scene(frame_img: numpy.ndarray, position: FramePosition):
        print(f"New scene found at frame {position.frame_number}.")

    # We open a file just for test purposes, but we can also use a device or pipe here.
    cap = cv2.VideoCapture(test_video_file)
    video = VideoCaptureAdapter(cap)
    # Now `video` can be used as normal with a `SceneManager`. If the input is non-terminating,
    # either set `end_time/duration` when calling `detect_scenes`, or call `scene_manager.stop()`.
    total_frames = 1000
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video, duration=total_frames, callback=on_new_scene)
