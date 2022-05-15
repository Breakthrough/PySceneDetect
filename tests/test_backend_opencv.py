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
""" PySceneDetect scenedetect.backend.opencv Tests

This file includes unit tests for the scenedetect.backend.opencv module that implements the
VideoStreamCv2 ('opencv') backend. These tests validate behaviour specific to this backend.

For VideoStream tests that validate conformance, see test_video_stream.py.
"""

from scenedetect.backends.opencv import VideoStreamCv2


def test_open_image_sequence(test_image_sequence: str):
    """Test opening an image sequence. Currently, only VideoStreamCv2 supports this."""
    sequence = VideoStreamCv2(path_or_device=test_image_sequence, framerate=25.0)
    assert sequence.is_seekable
    assert sequence.frame_size[0] > 0 and sequence.frame_size[1] > 0
    assert sequence.duration.frame_num == 30
    assert sequence.read() is not False
    sequence.seek(100)
    assert sequence.position == 29
