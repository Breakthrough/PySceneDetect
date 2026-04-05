#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Tests for VFR (Variable Frame Rate) video support."""

import csv
import os
import typing as ty

import cv2
import numpy as np
import pytest

from scenedetect import SceneManager, open_video
from scenedetect.common import Timecode
from scenedetect.detectors import ContentDetector
from scenedetect.output import save_images
from scenedetect.stats_manager import StatsManager

# Expected scene cuts for `goldeneye-vfr.mp4` detected with ContentDetector() and end_time=10.0s.
# Entries are (start_timecode, end_timecode). All backends should agree on cut timecodes since
# CAP_PROP_POS_MSEC gives accurate PTS-derived timestamps. The last scene ends at the clip
# boundary (end_time) which may vary slightly between backends based on frame counting.
EXPECTED_SCENES_VFR: ty.List[ty.Tuple[str, str]] = [
    ("00:00:00.000", "00:00:03.921"),
    ("00:00:03.921", "00:00:09.676"),
]

# Expected scene cuts for `goldeneye-vfr-drop3.mp4` — a synthetic VFR clip created from the first
# 10s of goldeneye.mp4 by dropping every 3rd frame (frames 2,5,8,...). PTS durations alternate
# between 1001 and 2002 (time_base=1/24000), nominal fps=24000/1001, avg fps≈16. The last scene
# ends at the clip boundary and may vary slightly between backends.
EXPECTED_SCENES_VFR_DROP3: ty.List[ty.Tuple[str, str]] = [
    ("00:00:00.000", "00:00:03.754"),
    ("00:00:03.754", "00:00:08.759"),
]


class TestVFR:
    """Test VFR video handling."""

    def test_vfr_position_is_timecode(self, test_vfr_video: str):
        """Position should be a Timecode-backed FrameTimecode."""
        video = open_video(test_vfr_video, backend="pyav")
        assert video.read() is not False
        assert isinstance(video.position._time, Timecode)

    def test_vfr_position_monotonic_pyav(self, test_vfr_video: str):
        """PTS-based position should be monotonically non-decreasing (PyAV)."""
        video = open_video(test_vfr_video, backend="pyav")
        last_seconds = -1.0
        frame_count = 0
        while True:
            frame = video.read()
            if frame is False:
                break
            current = video.position.seconds
            assert current >= last_seconds, (
                f"Position decreased at frame {frame_count}: {current} < {last_seconds}"
            )
            last_seconds = current
            frame_count += 1
        assert frame_count > 0

    def test_vfr_position_monotonic_opencv(self, test_vfr_video: str):
        """PTS-based position should be monotonically non-decreasing (OpenCV)."""
        video = open_video(test_vfr_video, backend="opencv")
        last_seconds = -1.0
        frame_count = 0
        while True:
            frame = video.read()
            if frame is False:
                break
            current = video.position.seconds
            assert current >= last_seconds, (
                f"Position decreased at frame {frame_count}: {current} < {last_seconds}"
            )
            last_seconds = current
            frame_count += 1
        assert frame_count > 0

    @pytest.mark.parametrize("backend", ["pyav", "opencv"])
    def test_vfr_scene_detection(self, test_vfr_video: str, backend: str):
        """Scene detection on VFR video should produce timestamps matching known ground truth.

        Both PyAV (native PTS) and OpenCV (CAP_PROP_POS_MSEC) should agree on scene cuts since
        both expose accurate PTS-derived timestamps.
        """
        video = open_video(test_vfr_video, backend=backend)
        sm = SceneManager()
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video=video, end_time=10.0)
        scene_list = sm.get_scene_list()

        # The last scene ends at the clip boundary which may vary by backend; only check known cuts.
        assert len(scene_list) >= len(EXPECTED_SCENES_VFR), (
            f"[{backend}] Expected at least {len(EXPECTED_SCENES_VFR)} scenes, got {len(scene_list)}"
        )
        for i, ((start, end), (exp_start_tc, exp_end_tc)) in enumerate(
            zip(scene_list, EXPECTED_SCENES_VFR, strict=False)
        ):
            assert start.get_timecode() == exp_start_tc, (
                f"[{backend}] Scene {i + 1} start: expected {exp_start_tc!r}, got {start.get_timecode()!r}"
            )
            assert end.get_timecode() == exp_end_tc, (
                f"[{backend}] Scene {i + 1} end: expected {exp_end_tc!r}, got {end.get_timecode()!r}"
            )

    def test_vfr_seek_pyav(self, test_vfr_video: str):
        """Seeking should work with VFR video."""
        video = open_video(test_vfr_video, backend="pyav")
        target_time = 2.0  # seconds
        video.seek(target_time)
        frame = video.read()
        assert frame is not False
        # Position should be close to target (within 1 second for keyframe-based seeking).
        assert abs(video.position.seconds - target_time) < 1.0

    def test_vfr_stats_manager(self, test_vfr_video: str):
        """StatsManager should work correctly with VFR video."""
        video = open_video(test_vfr_video, backend="pyav")
        stats = StatsManager()
        sm = SceneManager(stats_manager=stats)
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video=video)
        assert len(sm.get_scene_list()) > 0

    def test_vfr_csv_output(self, test_vfr_video: str, tmp_path):
        """CSV export should work correctly with VFR video."""
        from scenedetect.output import write_scene_list

        video = open_video(test_vfr_video, backend="pyav")
        sm = SceneManager()
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video=video)
        scene_list = sm.get_scene_list()
        assert len(scene_list) > 0

        csv_path = os.path.join(str(tmp_path), "scenes.csv")
        with open(csv_path, "w", newline="") as f:
            write_scene_list(f, scene_list)

        # Verify CSV contains valid data.
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) >= 3  # 2 header rows + data

    @pytest.mark.parametrize("backend", ["pyav", "opencv"])
    def test_vfr_drop3_scene_detection(self, test_vfr_drop3_video: str, backend: str):
        """Synthetic VFR video (drop every 3rd frame, alternating 1x/2x durations) should produce
        timecodes matching known ground truth with both backends."""
        video = open_video(test_vfr_drop3_video, backend=backend)
        sm = SceneManager()
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video=video, show_progress=False)
        scene_list = sm.get_scene_list()

        assert len(scene_list) >= len(EXPECTED_SCENES_VFR_DROP3), (
            f"[{backend}] Expected at least {len(EXPECTED_SCENES_VFR_DROP3)} scenes, got {len(scene_list)}"
        )
        for i, ((start, end), (exp_start_tc, exp_end_tc)) in enumerate(
            zip(scene_list, EXPECTED_SCENES_VFR_DROP3, strict=False)
        ):
            assert start.get_timecode() == exp_start_tc, (
                f"[{backend}] Scene {i + 1} start: expected {exp_start_tc!r}, got {start.get_timecode()!r}"
            )
            assert end.get_timecode() == exp_end_tc, (
                f"[{backend}] Scene {i + 1} end: expected {exp_end_tc!r}, got {end.get_timecode()!r}"
            )

    @pytest.mark.parametrize("backend", ["pyav", "opencv"])
    def test_vfr_drop3_position_monotonic(self, test_vfr_drop3_video: str, backend: str):
        """PTS-based position should be monotonically non-decreasing on synthetic VFR video."""
        video = open_video(test_vfr_drop3_video, backend=backend)
        last_seconds = -1.0
        frame_count = 0
        while True:
            if video.read() is False:
                break
            current = video.position.seconds
            assert current >= last_seconds, (
                f"[{backend}] Position decreased at frame {frame_count}: {current} < {last_seconds}"
            )
            last_seconds = current
            frame_count += 1
        assert frame_count == 160  # 2/3 of original 240 frames in 10s at 24000/1001

    def test_cfr_position_is_timecode(self, test_movie_clip: str):
        """CFR video positions should also be Timecode-backed with PTS support."""
        video = open_video(test_movie_clip, backend="pyav")
        assert video.read() is not False
        assert isinstance(video.position._time, Timecode)

    def test_cfr_frame_num_exact(self, test_movie_clip: str):
        """For CFR video, frame_num should be exact (not approximate)."""
        video = open_video(test_movie_clip, backend="pyav")
        for expected_frame in range(1, 11):
            assert video.read() is not False
            assert video.position.frame_num == expected_frame - 1

    def test_vfr_save_images_opencv_matches_pyav(self, test_vfr_video: str, tmp_path):
        """OpenCV save-images thumbnails should match PyAV thumbnails for all scenes.

        If the OpenCV seek off-by-one bug is present, scene thumbnails will show content from the
        wrong scene; MSE against PyAV (ground truth) will be very high for those scenes.
        """
        # Run save-images for both backends with 1 image per scene for simplicity.
        scene_lists = {}
        for backend in ("pyav", "opencv"):
            out_dir = tmp_path / backend
            out_dir.mkdir()
            video = open_video(test_vfr_video, backend=backend)
            sm = SceneManager()
            sm.add_detector(ContentDetector())
            sm.detect_scenes(video=video)
            scene_lists[backend] = sm.get_scene_list()
            assert len(scene_lists[backend]) > 0
            save_images(scene_lists[backend], video, num_images=1, output_dir=str(out_dir))

        pyav_imgs = sorted((tmp_path / "pyav").glob("*.jpg"))
        opencv_imgs = sorted((tmp_path / "opencv").glob("*.jpg"))
        assert len(pyav_imgs) > 0
        assert len(pyav_imgs) == len(opencv_imgs), (
            f"Image count mismatch: pyav={len(pyav_imgs)}, opencv={len(opencv_imgs)}"
        )

        # Compare every corresponding thumbnail. Wrong-scene content produces very high MSE.
        MAX_MSE = 5000
        for pyav_path, opencv_path in zip(pyav_imgs, opencv_imgs, strict=False):
            img_pyav = cv2.imread(str(pyav_path))
            img_opencv = cv2.imread(str(opencv_path))
            assert img_pyav is not None, f"Failed to load {pyav_path}"
            assert img_opencv is not None, f"Failed to load {opencv_path}"
            if img_pyav.shape != img_opencv.shape:
                # Resize opencv image to match pyav dimensions before comparing.
                img_opencv = cv2.resize(img_opencv, (img_pyav.shape[1], img_pyav.shape[0]))
            mse = float(np.mean((img_pyav.astype(np.float32) - img_opencv.astype(np.float32)) ** 2))
            assert mse < MAX_MSE, (
                f"Thumbnail mismatch for {pyav_path.name} vs {opencv_path.name}: MSE={mse:.0f}"
            )
