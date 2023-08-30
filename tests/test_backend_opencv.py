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
""" PySceneDetect scenedetect.backend.opencv Tests

This file includes unit tests for the scenedetect.backend.opencv module that implements the
VideoStreamCv2 ('opencv') backend. These tests validate behaviour specific to this backend.

For VideoStream tests that validate conformance, see test_video_stream.py.
"""

import cv2

from scenedetect import ContentDetector, SceneManager
from scenedetect.backends.opencv import VideoStreamCv2, VideoCaptureAdapter

GROUND_TRUTH_CAPTURE_ADAPTER_TEST = [1, 90, 210]
GROUND_TRUTH_CAPTURE_ADAPTER_CALLBACK_TEST = [30, 180, 394]


def test_open_image_sequence(test_image_sequence: str):
    """Test opening an image sequence. Currently, only VideoStreamCv2 supports this."""
    sequence = VideoStreamCv2(test_image_sequence, framerate=25.0)
    assert sequence.is_seekable
    assert sequence.frame_size[0] > 0 and sequence.frame_size[1] > 0
    assert sequence.duration.frame_num == 30
    assert sequence.read() is not False
    sequence.seek(100)
    assert sequence.position == 29


def test_capture_adapter(test_movie_clip: str):
    """Test that the VideoCaptureAdapter works with SceneManager."""
    cap = cv2.VideoCapture(test_movie_clip)
    assert cap.isOpened()
    adapter = VideoCaptureAdapter(cap)
    assert adapter.read() is not False

    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    assert scene_manager.detect_scenes(video=adapter, duration=adapter.base_timecode + 10.0)
    scenes = scene_manager.get_scene_list()
    assert len(scenes) == len(GROUND_TRUTH_CAPTURE_ADAPTER_TEST)
    assert [start.get_frames() for (start, _) in scenes] == GROUND_TRUTH_CAPTURE_ADAPTER_TEST


def test_capture_adapter_callback(test_video_file: str):
    """Test that the VideoCaptureAdapter works with SceneManager and a callback."""

    callback_frames = []

    def on_new_scene(_, frame_num: int):
        nonlocal callback_frames
        callback_frames.append(frame_num)

    cap = cv2.VideoCapture(test_video_file)
    assert cap.isOpened()
    adapter = VideoCaptureAdapter(cap)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=adapter, callback=on_new_scene)
    assert callback_frames == GROUND_TRUTH_CAPTURE_ADAPTER_CALLBACK_TEST
