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


# TODO(v0.8): Remove this test during the removal of `scenedetect.video_splitter`.
def test_deprecated_output_modules_emits_warning_on_import():
    VIDEO_SPLITTER_WARNING = (
        "The `video_splitter` submodule is deprecated, import from the base package instead."
    )
    with pytest.warns(DeprecationWarning, match=VIDEO_SPLITTER_WARNING):
        from scenedetect.video_splitter import split_video_ffmpeg as _


class TestImageExtractorTemporalMargin:
    """Tests for _ImageExtractor temporal margin functionality using PTS-based selection."""

    def test_temporal_margin_uses_seconds_not_frames(self):
        """Test that temporal_margin operates on presentation time, not frame count.

        With a 0.1s margin on a scene from 0s to 3s at 30fps:
        - First image should be at ~0.1s (frame 3)
        - Last image should be at ~2.9s (frame 87)
        """
        from scenedetect.output.image import _ImageExtractor

        # 30 fps, 0.1s temporal margin
        extractor = _ImageExtractor(
            num_images=3, temporal_margin=FrameTimecode(timecode=0.1, fps=30.0)
        )

        # Scene from frame 0 to 90 (0s to 3s at 30fps)
        scene_list = [
            (FrameTimecode(0, fps=30.0), FrameTimecode(90, fps=30.0)),
        ]
        timecode_list = extractor.generate_timecode_list(scene_list)
        timecodes = list(timecode_list[0])

        # First image: start.seconds + margin = 0 + 0.1 = 0.1s → frame 3
        assert timecodes[0].seconds == pytest.approx(0.1, abs=0.05)
        # Middle image: should be around middle of scene
        assert timecodes[1].seconds == pytest.approx(1.5, abs=0.1)
        # Last image: end.seconds - margin = 3.0 - 0.1 = 2.9s → frame 87
        assert timecodes[2].seconds == pytest.approx(2.9, abs=0.05)

    def test_temporal_margin_different_framerates(self):
        """Test temporal margin works consistently across different framerates.

        The same temporal margin (0.1s) should result in different frame offsets
        but the same time offset regardless of framerate.
        """
        from scenedetect.output.image import _ImageExtractor

        for fps in [24.0, 25.0, 30.0, 60.0]:
            extractor = _ImageExtractor(
                num_images=3, temporal_margin=FrameTimecode(timecode=0.1, fps=fps)
            )
            # 3 second scene
            scene_list = [
                (FrameTimecode(0, fps=fps), FrameTimecode(int(3 * fps), fps=fps)),
            ]
            timecode_list = extractor.generate_timecode_list(scene_list)
            timecodes = list(timecode_list[0])

            # First and last images should be offset by ~0.1s regardless of fps
            assert timecodes[0].seconds == pytest.approx(0.1, abs=0.05), f"Failed at {fps}fps"
            assert timecodes[2].seconds == pytest.approx(2.9, abs=0.05), f"Failed at {fps}fps"

    def test_temporal_margin_clamped_to_scene_bounds(self):
        """Test that temporal margin is clamped when scene is shorter than 2x margin."""
        from scenedetect.output.image import _ImageExtractor

        # 0.5s margin on a 0.5s scene - should clamp to scene bounds
        extractor = _ImageExtractor(
            num_images=3, temporal_margin=FrameTimecode(timecode=0.5, fps=30.0)
        )

        # Scene from frame 0 to 15 (0s to 0.5s at 30fps)
        scene_list = [
            (FrameTimecode(0, fps=30.0), FrameTimecode(15, fps=30.0)),
        ]
        timecode_list = extractor.generate_timecode_list(scene_list)
        timecodes = list(timecode_list[0])

        # All frames should be within scene bounds
        for tc in timecodes:
            assert 0.0 <= tc.seconds <= 0.5

    def test_temporal_margin_zero(self):
        """Test that zero temporal margin selects frames at scene boundaries."""
        from scenedetect.output.image import _ImageExtractor

        extractor = _ImageExtractor(
            num_images=3, temporal_margin=FrameTimecode(timecode=0.0, fps=30.0)
        )

        scene_list = [
            (FrameTimecode(30, fps=30.0), FrameTimecode(90, fps=30.0)),
        ]
        timecode_list = extractor.generate_timecode_list(scene_list)
        timecodes = list(timecode_list[0])

        # First image at scene start (1s)
        assert timecodes[0].seconds == pytest.approx(1.0, abs=0.05)
        # Last image near scene end (3s)
        assert timecodes[2].seconds == pytest.approx(2.97, abs=0.1)

    def test_temporal_margin_with_pts_timecodes(self):
        """Test temporal margin works correctly with PTS-based FrameTimecodes.

        PTS (Presentation Time Stamp) based timecodes use a time_base rather than
        a fixed framerate. This test verifies that temporal margin calculations
        work correctly when scenes are defined using PTS.
        """
        from fractions import Fraction

        from scenedetect.common import Timecode
        from scenedetect.output.image import _ImageExtractor

        # Use a time_base of 1/1000 (milliseconds) - common for many video formats
        time_base = Fraction(1, 1000)

        # Create PTS-based FrameTimecodes for a 3 second scene (0ms to 3000ms)
        start = FrameTimecode(timecode=Timecode(pts=0, time_base=time_base), fps=30.0)
        end = FrameTimecode(timecode=Timecode(pts=3000, time_base=time_base), fps=30.0)

        # 100ms (0.1s) temporal margin, also as PTS-based
        margin = FrameTimecode(timecode=Timecode(pts=100, time_base=time_base), fps=30.0)

        extractor = _ImageExtractor(num_images=3, temporal_margin=margin)

        scene_list = [(start, end)]
        timecode_list = extractor.generate_timecode_list(scene_list)
        timecodes = list(timecode_list[0])

        # First image: 0s + 0.1s margin = 0.1s
        assert timecodes[0].seconds == pytest.approx(0.1, abs=0.05)
        # Middle image: ~1.5s
        assert timecodes[1].seconds == pytest.approx(1.5, abs=0.1)
        # Last image: 3s - 0.1s margin = 2.9s
        assert timecodes[2].seconds == pytest.approx(2.9, abs=0.05)

    def test_temporal_margin_pts_preserves_time_base(self):
        """Test that output timecodes preserve the time_base from input PTS timecodes."""
        from fractions import Fraction

        from scenedetect.common import Timecode
        from scenedetect.output.image import _ImageExtractor

        time_base = Fraction(1, 90000)  # Common time_base for MPEG-TS

        # 2 second scene at pts 0 to 180000 (at 1/90000 time_base)
        start = FrameTimecode(timecode=Timecode(pts=0, time_base=time_base), fps=30.0)
        end = FrameTimecode(timecode=Timecode(pts=180000, time_base=time_base), fps=30.0)

        # 0.1s margin = 9000 pts at 1/90000 time_base
        margin = FrameTimecode(timecode=Timecode(pts=9000, time_base=time_base), fps=30.0)

        extractor = _ImageExtractor(num_images=2, temporal_margin=margin)

        scene_list = [(start, end)]
        timecode_list = extractor.generate_timecode_list(scene_list)
        timecodes = list(timecode_list[0])

        # Verify time values are correct
        assert timecodes[0].seconds == pytest.approx(0.1, abs=0.01)
        assert timecodes[1].seconds == pytest.approx(1.9, abs=0.01)

    def test_frame_margin_backwards_compatibility(self):
        """Test that frame_margin still works when temporal_margin is not set.

        This ensures backwards compatibility with existing code using frame_margin.
        """
        from scenedetect.output.image import _ImageExtractor

        # 3 frame margin at 30fps = 0.1s
        extractor = _ImageExtractor(num_images=3, frame_margin=3)

        # Scene from frame 0 to 90 (0s to 3s at 30fps)
        scene_list = [
            (FrameTimecode(0, fps=30.0), FrameTimecode(90, fps=30.0)),
        ]
        timecode_list = extractor.generate_timecode_list(scene_list)
        timecodes = list(timecode_list[0])

        # First image: 3 frames = 0.1s at 30fps
        assert timecodes[0].seconds == pytest.approx(0.1, abs=0.05)
        # Middle image: ~1.5s
        assert timecodes[1].seconds == pytest.approx(1.5, abs=0.1)
        # Last image: 3s - 3 frames = 2.9s
        assert timecodes[2].seconds == pytest.approx(2.9, abs=0.05)

    def test_temporal_margin_overrides_frame_margin(self):
        """Test that temporal_margin takes precedence over frame_margin when both are set."""
        from scenedetect.output.image import _ImageExtractor

        # Set frame_margin to 30 frames (1s at 30fps), but temporal_margin to 0.1s
        # temporal_margin should win
        extractor = _ImageExtractor(
            num_images=3,
            frame_margin=30,  # Would be 1s at 30fps
            temporal_margin=FrameTimecode(timecode=0.1, fps=30.0),  # 0.1s
        )

        scene_list = [
            (FrameTimecode(0, fps=30.0), FrameTimecode(90, fps=30.0)),
        ]
        timecode_list = extractor.generate_timecode_list(scene_list)
        timecodes = list(timecode_list[0])

        # Should use temporal_margin (0.1s), not frame_margin (1s)
        assert timecodes[0].seconds == pytest.approx(0.1, abs=0.05)
        assert timecodes[2].seconds == pytest.approx(2.9, abs=0.05)
