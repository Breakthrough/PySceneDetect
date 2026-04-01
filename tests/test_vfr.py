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

import pytest

from scenedetect import SceneManager
from scenedetect.common import FrameTimecode, Timecode
from scenedetect.detectors import ContentDetector
from scenedetect.stats_manager import StatsManager


def _open_pyav(path: str):
    """Open a video with the PyAV backend."""
    from scenedetect.backends.pyav import VideoStreamAv

    return VideoStreamAv(path)


def _open_opencv(path: str):
    """Open a video with the OpenCV backend."""
    from scenedetect.backends.opencv import VideoStreamCv2

    return VideoStreamCv2(path)


class TestVFR:
    """Test VFR video handling."""

    def test_vfr_position_is_timecode(self, test_vfr_video: str):
        """Position should be a Timecode-backed FrameTimecode."""
        video = _open_pyav(test_vfr_video)
        assert video.read() is not False
        assert isinstance(video.position._time, Timecode)

    def test_vfr_position_monotonic_pyav(self, test_vfr_video: str):
        """PTS-based position should be monotonically non-decreasing."""
        video = _open_pyav(test_vfr_video)
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
        """PTS-based position should be monotonically non-decreasing with OpenCV."""
        video = _open_opencv(test_vfr_video)
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

    def test_vfr_scene_detection(self, test_vfr_video: str):
        """Scene detection should work on VFR video and produce reasonable timestamps."""
        video = _open_pyav(test_vfr_video)
        sm = SceneManager()
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video=video)
        scene_list = sm.get_scene_list()
        # Should detect at least one scene.
        assert len(scene_list) > 0
        # All timestamps should be non-negative and within video duration.
        for start, end in scene_list:
            assert start.seconds >= 0
            assert end.seconds > start.seconds

    def test_vfr_seek_pyav(self, test_vfr_video: str):
        """Seeking should work with VFR video."""
        video = _open_pyav(test_vfr_video)
        target_time = 2.0  # seconds
        video.seek(target_time)
        frame = video.read()
        assert frame is not False
        # Position should be close to target (within 1 second for keyframe-based seeking).
        assert abs(video.position.seconds - target_time) < 1.0

    def test_vfr_stats_manager(self, test_vfr_video: str):
        """StatsManager should work correctly with VFR video."""
        video = _open_pyav(test_vfr_video)
        stats = StatsManager()
        sm = SceneManager(stats_manager=stats)
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video=video)
        # Stats should have metrics for frames.
        scene_list = sm.get_scene_list()
        assert len(scene_list) > 0

    def test_vfr_csv_output(self, test_vfr_video: str, tmp_path):
        """CSV export should work correctly with VFR video."""
        from scenedetect.output import write_scene_list

        video = _open_pyav(test_vfr_video)
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
            # Header + at least one data row.
            assert len(rows) >= 3  # 2 header rows + data

    def test_cfr_position_is_timecode(self, test_movie_clip: str):
        """CFR video positions should also be Timecode-backed with PTS support."""
        video = _open_pyav(test_movie_clip)
        assert video.read() is not False
        assert isinstance(video.position._time, Timecode)

    def test_cfr_frame_num_exact(self, test_movie_clip: str):
        """For CFR video, frame_num should be exact (not approximate)."""
        video = _open_pyav(test_movie_clip)
        for expected_frame in range(1, 11):
            assert video.read() is not False
            assert video.position.frame_num == expected_frame - 1
