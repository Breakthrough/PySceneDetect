# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2023 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""" PySceneDetect Scene Detection Tests

These tests ensure that the detection algorithms deliver consistent
results by using known ground truths of scene cut locations in the
test case material.
"""

import time

from scenedetect import detect, SceneManager, FrameTimecode, StatsManager
from scenedetect.detectors import AdaptiveDetector, ContentDetector, ThresholdDetector, HashDetector
from scenedetect.backends.opencv import VideoStreamCv2

# TODO(v1.0): Parameterize these tests like VideoStreams are.
# Current test output cannot be used for profiling cases which iterate over multiple detectors.

# TODO(v1.0): Add new test video.

TEST_MOVIE_CLIP_START_FRAMES_ACTUAL = [1199, 1226, 1260, 1281, 1334, 1365, 1590, 1697, 1871]
"""Ground truth of start frame for each fast cut in `test_movie_clip`."""

TEST_VIDEO_FILE_START_FRAMES_ACTUAL = [0, 15, 198, 376]
"""Results for `test_video_file` with default ThresholdDetector values."""

FADES_FLOOR_START_FRAMES = [0, 84, 167, 245]
"""Results for `test_fades_clip` with default ThresholdDetector values."""

FADES_CEILING_START_FRAMES = [0, 42, 125, 209]
"""Results for `test_fades_clip` with ThresholdDetector fade to light with threshold 243."""


def test_detect(test_video_file):
    """ Test scenedetect.detect and ThresholdDetector. """
    scene_list = detect(video_path=test_video_file, detector=ThresholdDetector())
    assert len(scene_list) == len(TEST_VIDEO_FILE_START_FRAMES_ACTUAL)
    detected_start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert all(x == y for (x, y) in zip(TEST_VIDEO_FILE_START_FRAMES_ACTUAL, detected_start_frames))


def test_content_detector(test_movie_clip):
    """ Test SceneManager with VideoStreamCv2 and ContentDetector. """
    video = VideoStreamCv2(test_movie_clip)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())

    video_fps = video.frame_rate
    start_time = FrameTimecode('00:00:50', video_fps)
    end_time = FrameTimecode('00:01:19', video_fps)

    video.seek(start_time)
    scene_manager.auto_downscale = True

    scene_manager.detect_scenes(video=video, end_time=end_time)
    scene_list = scene_manager.get_scene_list()
    assert len(scene_list) == len(TEST_MOVIE_CLIP_START_FRAMES_ACTUAL)
    detected_start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert TEST_MOVIE_CLIP_START_FRAMES_ACTUAL == detected_start_frames
    # Ensure last scene's end timecode matches the end time we set.
    assert scene_list[-1][1] == end_time


def test_adaptive_detector(test_movie_clip):
    """ Test SceneManager with VideoStreamCv2 and AdaptiveDetector. """
    video = VideoStreamCv2(test_movie_clip)
    scene_manager = SceneManager()
    scene_manager.add_detector(AdaptiveDetector())
    scene_manager.auto_downscale = True

    video_fps = video.frame_rate
    start_time = FrameTimecode('00:00:50', video_fps)
    end_time = FrameTimecode('00:01:19', video_fps)

    video.seek(start_time)
    scene_manager.detect_scenes(video=video, end_time=end_time)

    scene_list = scene_manager.get_scene_list()
    assert len(scene_list) == len(TEST_MOVIE_CLIP_START_FRAMES_ACTUAL)
    detected_start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert TEST_MOVIE_CLIP_START_FRAMES_ACTUAL == detected_start_frames
    # Ensure last scene's end timecode matches the end time we set.
    assert scene_list[-1][1] == end_time


def test_hash_detector(test_movie_clip):
    """ Test SceneManager with VideoStreamCv2 and HashDetector. """
    video = VideoStreamCv2(test_movie_clip)
    scene_manager = SceneManager()
    scene_manager.add_detector(HashDetector())
    scene_manager.auto_downscale = True

    video_fps = video.frame_rate
    start_time = FrameTimecode('00:00:50', video_fps)
    end_time = FrameTimecode('00:01:19', video_fps)

    video.seek(start_time)
    scene_manager.detect_scenes(video=video, end_time=end_time)

    scene_list = scene_manager.get_scene_list()
    assert len(scene_list) == len(TEST_MOVIE_CLIP_START_FRAMES_ACTUAL)
    detected_start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert TEST_MOVIE_CLIP_START_FRAMES_ACTUAL == detected_start_frames
    # Ensure last scene's end timecode matches the end time we set.
    assert scene_list[-1][1] == end_time


def test_threshold_detector(test_video_file):
    """ Test SceneManager with VideoStreamCv2 and ThresholdDetector. """
    video = VideoStreamCv2(test_video_file)
    scene_manager = SceneManager()
    scene_manager.add_detector(ThresholdDetector())
    scene_manager.auto_downscale = True
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    assert len(scene_list) == len(TEST_VIDEO_FILE_START_FRAMES_ACTUAL)
    detected_start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert all(x == y for (x, y) in zip(TEST_VIDEO_FILE_START_FRAMES_ACTUAL, detected_start_frames))


def test_detectors_with_stats(test_video_file):
    """ Test all detectors functionality with a StatsManager. """
    # TODO(v1.0): Parameterize this test case (move fixture from cli to test config).
    for detector in [ContentDetector, ThresholdDetector, AdaptiveDetector, HashDetector]:
        video = VideoStreamCv2(test_video_file)
        stats = StatsManager()
        scene_manager = SceneManager(stats_manager=stats)
        scene_manager.add_detector(detector())
        scene_manager.auto_downscale = True
        end_time = FrameTimecode('00:00:08', video.frame_rate)
        benchmark_start = time.time()
        scene_manager.detect_scenes(video=video, end_time=end_time)
        benchmark_end = time.time()
        time_no_stats = benchmark_end - benchmark_start
        initial_scene_len = len(scene_manager.get_scene_list())
        assert initial_scene_len > 0 # test case must have at least one scene!
                                     # Re-analyze using existing stats manager.
        scene_manager = SceneManager(stats_manager=stats)
        scene_manager.add_detector(detector())

        video.reset()
        scene_manager.auto_downscale = True

        benchmark_start = time.time()
        scene_manager.detect_scenes(video=video, end_time=end_time)
        benchmark_end = time.time()
        time_with_stats = benchmark_end - benchmark_start
        scene_list = scene_manager.get_scene_list()
        assert len(scene_list) == initial_scene_len

        print("--------------------------------------------------------------------")
        print("StatsManager Benchmark For %s" % (detector.__name__))
        print("--------------------------------------------------------------------")
        print("No Stats:\t%2.1fs" % time_no_stats)
        print("With Stats:\t%2.1fs" % time_with_stats)
        print("--------------------------------------------------------------------")


def test_threshold_detector_fade_out(test_fades_clip):
    """Test ThresholdDetector handles fading out to black."""
    video = VideoStreamCv2(test_fades_clip)
    scene_manager = SceneManager()
    scene_manager.add_detector(ThresholdDetector(add_final_scene=True))
    scene_manager.auto_downscale = True
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    assert len(scene_list) == len(FADES_FLOOR_START_FRAMES)
    detected_start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert all(x == y for (x, y) in zip(FADES_FLOOR_START_FRAMES, detected_start_frames))


def test_threshold_detector_fade_in(test_fades_clip):
    """Test ThresholdDetector handles fading in from white."""
    video = VideoStreamCv2(test_fades_clip)
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ThresholdDetector(
            threshold=243, method=ThresholdDetector.Method.CEILING, add_final_scene=True))
    scene_manager.auto_downscale = True
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    assert len(scene_list) == len(FADES_CEILING_START_FRAMES)
    detected_start_frames = [timecode.get_frames() for timecode, _ in scene_list]
    assert all(x == y for (x, y) in zip(FADES_CEILING_START_FRAMES, detected_start_frames))
