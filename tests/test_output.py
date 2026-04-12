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
"""Tests for scenedetect.output module."""

from pathlib import Path

import pytest

from scenedetect import (
    ContentDetector,
    FrameTimecode,
    SceneManager,
    VideoStreamCv2,
    open_video,
    save_images,
)
from scenedetect.output import (
    SceneMetadata,
    VideoMetadata,
    is_ffmpeg_available,
    split_video_ffmpeg,
)

FFMPEG_ARGS = (
    "-vf crop=128:128:0:0 -map 0:v:0 -c:v libx264 -preset ultrafast -qp 0 -tune zerolatency"
)
"""Only encodes a small crop of the frame and tuned for performance to speed up tests."""


@pytest.mark.skipif(condition=not is_ffmpeg_available(), reason="ffmpeg is not available")
def test_split_video_ffmpeg_default(tmp_path, test_movie_clip):
    video = open_video(test_movie_clip)
    # Extract three hard-coded scenes for testing, each 30 frames.
    scenes = [
        (video.base_timecode + 30, video.base_timecode + 60),
        (video.base_timecode + 60, video.base_timecode + 90),
        (video.base_timecode + 90, video.base_timecode + 120),
    ]
    assert (
        split_video_ffmpeg(test_movie_clip, scenes, output_dir=tmp_path, arg_override=FFMPEG_ARGS)
        == 0
    )
    # The default filename format should be VIDEO_NAME-Scene-SCENE_NUMBER.mp4.
    video_name = Path(test_movie_clip).stem
    entries = sorted(tmp_path.glob(f"{video_name}-Scene-*"))
    assert len(entries) == len(scenes)


@pytest.mark.skipif(condition=not is_ffmpeg_available(), reason="ffmpeg is not available")
def test_split_video_ffmpeg_formatter(tmp_path, test_movie_clip):
    video = open_video(test_movie_clip)
    # Extract three hard-coded scenes for testing, each 30 frames.
    scenes = [
        (video.base_timecode + 30, video.base_timecode + 60),
        (video.base_timecode + 60, video.base_timecode + 90),
        (video.base_timecode + 90, video.base_timecode + 120),
    ]

    # Custom filename formatter:
    def name_formatter(video: VideoMetadata, scene: SceneMetadata):
        return "abc" + video.name + "-123-" + str(scene.index) + ".mp4"

    assert (
        split_video_ffmpeg(
            test_movie_clip,
            scenes,
            output_dir=tmp_path,
            arg_override=FFMPEG_ARGS,
            formatter=name_formatter,
        )
        == 0
    )
    video_name = Path(test_movie_clip).stem
    entries = sorted(tmp_path.glob(f"abc{video_name}-123-*"))
    assert len(entries) == len(scenes)


# TODO: Add tests for `split_video_mkvmerge`.


def test_save_images(test_video_file, tmp_path: Path):
    """Test scenedetect.scene_manager.save_images function."""
    video = VideoStreamCv2(test_video_file)
    sm = SceneManager()
    sm.add_detector(ContentDetector())

    image_name_glob = "scenedetect.tempfile.*.jpg"
    image_name_template = (
        "scenedetect.tempfile.$SCENE_NUMBER.$IMAGE_NUMBER.$FRAME_NUMBER.$TIMESTAMP_MS.$TIMECODE"
    )

    video_fps = video.frame_rate
    scene_list = [
        (FrameTimecode(start, video_fps), FrameTimecode(end, video_fps))
        for start, end in [(0, 100), (200, 300), (300, 400)]
    ]

    image_filenames = save_images(
        scene_list=scene_list,
        output_dir=tmp_path,
        video=video,
        num_images=3,
        image_extension="jpg",
        image_name_template=image_name_template,
        threading=False,
    )

    # Ensure images got created, and the proper number got created.
    total_images = 0
    for scene_number in image_filenames:
        for path in image_filenames[scene_number]:
            assert tmp_path.joinpath(path).exists(), f"expected {path} to exist"
            total_images += 1

    assert total_images == len([path for path in tmp_path.glob(image_name_glob)])


def test_save_images_singlethreaded(test_video_file, tmp_path: Path):
    """Test scenedetect.scene_manager.save_images function."""
    video = VideoStreamCv2(test_video_file)
    sm = SceneManager()
    sm.add_detector(ContentDetector())

    image_name_glob = "scenedetect.tempfile.*.jpg"
    image_name_template = (
        "scenedetect.tempfile.$SCENE_NUMBER.$IMAGE_NUMBER.$FRAME_NUMBER.$TIMESTAMP_MS.$TIMECODE"
    )

    video_fps = video.frame_rate
    scene_list = [
        (FrameTimecode(start, video_fps), FrameTimecode(end, video_fps))
        for start, end in [(0, 100), (200, 300), (300, 400)]
    ]

    image_filenames = save_images(
        scene_list=scene_list,
        output_dir=tmp_path,
        video=video,
        num_images=3,
        image_extension="jpg",
        image_name_template=image_name_template,
        threading=True,
    )

    # Ensure images got created, and the proper number got created.
    total_images = 0
    for scene_number in image_filenames:
        for path in image_filenames[scene_number]:
            assert tmp_path.joinpath(path).exists(), f"expected {path} to exist"
            total_images += 1

    assert total_images == len([path for path in tmp_path.glob(image_name_glob)])


# TODO: Test other functionality against zero width scenes.
def test_save_images_zero_width_scene(test_video_file, tmp_path: Path):
    """Test scenedetect.scene_manager.save_images guards against zero width scenes."""
    video = VideoStreamCv2(test_video_file)
    image_name_glob = "scenedetect.tempfile.*.jpg"
    image_name_template = "scenedetect.tempfile.$SCENE_NUMBER.$IMAGE_NUMBER"

    video_fps = video.frame_rate
    scene_list = [
        (FrameTimecode(start, video_fps), FrameTimecode(end, video_fps))
        for start, end in [(0, 0), (1, 1), (2, 3)]
    ]
    NUM_IMAGES = 10
    image_filenames = save_images(
        scene_list=scene_list,
        output_dir=tmp_path,
        video=video,
        num_images=10,
        image_extension="jpg",
        image_name_template=image_name_template,
    )
    assert len(image_filenames) == 3
    assert all(len(image_filenames[scene]) == NUM_IMAGES for scene in image_filenames)
    total_images = 0
    for scene_number in image_filenames:
        for path in image_filenames[scene_number]:
            assert tmp_path.joinpath(path).exists(), f"expected {path} to exist"
            total_images += 1

    assert total_images == len([path for path in tmp_path.glob(image_name_glob)])
