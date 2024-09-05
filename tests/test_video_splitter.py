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
"""Tests for scenedetect.video_splitter module."""

# pylint: disable=no-self-use,missing-function-docstring

from pathlib import Path
import pytest

from scenedetect import open_video
from scenedetect.video_splitter import (
    split_video_ffmpeg,
    is_ffmpeg_available,
    SceneMetadata,
    VideoMetadata,
)


@pytest.mark.skipif(
    condition=not is_ffmpeg_available(), reason="ffmpeg is not available"
)
def test_split_video_ffmpeg_default(tmp_path, test_movie_clip):
    video = open_video(test_movie_clip)
    # Extract three hard-coded scenes for testing, each 60 frames.
    scenes = [
        (video.base_timecode + 60, video.base_timecode + 120),
        (video.base_timecode + 120, video.base_timecode + 180),
        (video.base_timecode + 180, video.base_timecode + 240),
    ]
    assert split_video_ffmpeg(test_movie_clip, scenes, tmp_path) == 0
    # The default filename format should be VIDEO_NAME-Scene-SCENE_NUMBER.mp4.
    video_name = Path(test_movie_clip).stem
    entries = sorted(tmp_path.glob(f"{video_name}-Scene-*"))
    assert len(entries) == len(scenes)


@pytest.mark.skipif(
    condition=not is_ffmpeg_available(), reason="ffmpeg is not available"
)
def test_split_video_ffmpeg_formatter(tmp_path, test_movie_clip):
    video = open_video(test_movie_clip)
    # Extract three hard-coded scenes for testing, each 60 frames.
    scenes = [
        (video.base_timecode + 60, video.base_timecode + 120),
        (video.base_timecode + 120, video.base_timecode + 180),
        (video.base_timecode + 180, video.base_timecode + 240),
    ]

    # Custom filename formatter:
    def name_formatter(video: VideoMetadata, scene: SceneMetadata):
        return "abc" + video.name + "-123-" + str(scene.index) + ".mp4"

    assert (
        split_video_ffmpeg(test_movie_clip, scenes, tmp_path, formatter=name_formatter)
        == 0
    )
    video_name = Path(test_movie_clip).stem
    entries = sorted(tmp_path.glob(f"abc{video_name}-123-*"))
    assert len(entries) == len(scenes)


# TODO: Add tests for `split_video_mkvmerge`.
