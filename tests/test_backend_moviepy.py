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
"""PySceneDetect MoviePy Backend Tests

Comprehensive test suite for VideoStreamMoviePy functionality.
Tests the MoviePy backend with various scenarios including error handling,
frame reading, seeking, and metadata extraction.
"""

import numpy as np
import pytest

from scenedetect.common import FrameTimecode
from scenedetect.video_stream import SeekError

# Test skip conditions
moviepy = pytest.importorskip("moviepy")
try:
    from scenedetect.backends.moviepy import VideoStreamMoviePy
except ImportError:
    pytest.skip("MoviePy backend not available", allow_module_level=True)

# pylint: disable=too-many-public-methods
class TestVideoStreamMoviePyBasics:
    """Basic tests for MoviePy backend initialization and properties."""

    def test_backend_name(self):
        """Test backend name identification."""
        assert VideoStreamMoviePy.BACKEND_NAME == "moviepy"

    def test_video_open_success(self, test_video_file):
        """Test successful video opening with valid file."""
        video = VideoStreamMoviePy(test_video_file)
        assert video.path == test_video_file
        assert video.name == "testvideo"
        assert video.is_seekable is True
        assert video.frame_rate > 0
        assert video.frame_size[0] > 0 and video.frame_size[1] > 0

    def test_video_open_with_print_infos(self, test_video_file):
        """Test video opening with print_infos enabled."""
        video = VideoStreamMoviePy(test_video_file, print_infos=True)
        assert video.path == test_video_file

    def test_video_open_nonexistent_file(self):
        """Test error handling for non-existent video files."""
        with pytest.raises(OSError):
            VideoStreamMoviePy("nonexistent_video.mp4")

    def test_video_open_invalid_file(self, tmp_path):
        """Test error handling for invalid video files."""
        invalid_file = tmp_path / "invalid.mp4"
        invalid_file.write_text("This is not a video file")

        with pytest.raises(OSError):
            VideoStreamMoviePy(str(invalid_file))

    def test_framerate_override_not_implemented(self, test_video_file):
        """Test that framerate override raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="framerate.*argument"):
            VideoStreamMoviePy(test_video_file, framerate=30.0)

    def test_basic_properties(self, test_video_file):
        """Test basic video properties."""
        video = VideoStreamMoviePy(test_video_file)

        # Test frame rate
        assert isinstance(video.frame_rate, float)
        assert video.frame_rate > 0

        # Test frame size
        width, height = video.frame_size
        assert isinstance(width, int) and width > 0
        assert isinstance(height, int) and height > 0

        # Test duration
        assert video.duration is not None
        assert isinstance(video.duration, FrameTimecode)
        assert video.duration.get_seconds() > 0

        # Test aspect ratio
        assert isinstance(video.aspect_ratio, float)
        assert video.aspect_ratio > 0

    def test_initial_position(self, test_video_file):
        """Test initial position properties."""
        video = VideoStreamMoviePy(test_video_file)

        assert video.frame_number == 0
        assert video.position.get_seconds() == 0.0
        assert video.position_ms == 0.0


class TestVideoStreamMoviePyReading:
    """Tests for frame reading operations of MoviePy backend."""

    def test_frame_reading_decode_true(self, test_video_file):
        """Test frame reading with decode=True."""
        video = VideoStreamMoviePy(test_video_file)

        # Read first frame
        frame = video.read(decode=True)
        assert isinstance(frame, np.ndarray)
        assert frame.shape[2] == 3  # RGB channels
        assert video.frame_number == 1

        # Read second frame
        frame2 = video.read(decode=True)
        assert isinstance(frame2, np.ndarray)
        assert video.frame_number == 2

        # Frames should be different (assuming video has motion)
        assert not np.array_equal(frame, frame2)

    def test_frame_reading_decode_false(self, test_video_file):
        """Test frame reading with decode=False for performance."""
        video = VideoStreamMoviePy(test_video_file)

        # Read without decoding
        result = video.read(decode=False)
        assert isinstance(result, bool)
        assert result is True
        assert video.frame_number == 1

        result2 = video.read(decode=False)
        assert result2 is True
        assert video.frame_number == 2

    def test_frame_reading_until_eof(self, test_video_file):
        """Test reading frames until end of video."""
        video = VideoStreamMoviePy(test_video_file)

        frame_count = 0
        while True:
            frame = video.read(decode=False)
            if frame is False:
                break
            frame_count += 1
            assert video.frame_number == frame_count

        # Should have read some frames
        assert frame_count > 0

        # Further reads should return False
        assert video.read(decode=False) is False
        assert video.read(decode=True) is False

    def test_color_space_conversion(self, test_video_file):
        """Test that frames are properly converted to RGB."""
        video = VideoStreamMoviePy(test_video_file)

        frame = video.read(decode=True)
        assert isinstance(frame, np.ndarray)
        assert frame.shape[2] == 3  # RGB channels
        assert frame.dtype == np.uint8

        # Check that color values are in valid range
        assert np.all(frame >= 0)
        assert np.all(frame <= 255)

    def test_memory_efficiency(self, test_video_file):
        """Test memory efficiency of non-decode reads."""
        video = VideoStreamMoviePy(test_video_file)

        # Read many frames without decoding
        for _ in range(50):
            result = video.read(decode=False)
            if result is False:
                break

        # Should still be able to decode current frame
        video.seek(25)
        frame = video.read(decode=True)
        assert isinstance(frame, np.ndarray)

    def test_edge_case_single_frame(self, test_video_file):
        """Test reading exactly one frame."""
        video = VideoStreamMoviePy(test_video_file)

        frame = video.read(decode=True)
        assert isinstance(frame, np.ndarray)
        assert video.frame_number == 1

        # Position should reflect first frame
        assert video.position.get_seconds() == 0.0
        assert video.position_ms == 0.0


class TestVideoStreamMoviePySeeking:
    """Tests for seeking operations of MoviePy backend."""

    def test_seek_by_seconds(self, test_video_file):
        """Test seeking by time in seconds."""
        video = VideoStreamMoviePy(test_video_file)

        # Seek to 2 seconds
        video.seek(2.0)
        frame = video.read()
        assert frame is not False

        # Position should be approximately 2 seconds
        position_seconds = video.position.get_seconds()
        assert abs(position_seconds - 2.0) < 0.1  # Allow small tolerance

    def test_seek_by_frame_number(self, test_video_file):
        """Test seeking by frame number."""
        video = VideoStreamMoviePy(test_video_file)

        # Seek to frame 30
        video.seek(30)
        frame = video.read()
        assert frame is not False
        assert video.frame_number == 31  # After reading one frame

    def test_seek_by_timecode(self, test_video_file):
        """Test seeking using FrameTimecode object."""
        video = VideoStreamMoviePy(test_video_file)

        # Seek using FrameTimecode
        target_timecode = FrameTimecode(60, video.frame_rate)
        video.seek(target_timecode)
        frame = video.read()
        assert frame is not False
        assert video.frame_number == 61

    def test_seek_beginning(self, test_video_file):
        """Test seeking to the beginning."""
        video = VideoStreamMoviePy(test_video_file)

        # Read some frames first
        for _ in range(5):
            video.read()

        # Seek back to beginning
        video.seek(0)
        frame = video.read()
        assert frame is not False
        assert video.frame_number == 1

    def test_seek_near_end(self, test_video_file):
        """Test seeking near the end of video."""
        video = VideoStreamMoviePy(test_video_file)

        # Calculate target near end (90% of duration)
        total_frames = int(video.duration.get_frames())
        target_frame = int(total_frames * 0.9)

        video.seek(target_frame)
        frame = video.read()
        assert frame is not False

    def test_seek_past_end_error(self, test_video_file):
        """Test seeking past end of video raises SeekError."""
        video = VideoStreamMoviePy(test_video_file)

        # Try to seek way past the end
        duration_seconds = video.duration.get_seconds()
        with pytest.raises(SeekError, match="beyond end of video|EOF semantics"):
            video.seek(duration_seconds + 1000)

    def test_seek_negative_error(self, test_video_file):
        """Test seeking to negative position raises ValueError."""
        video = VideoStreamMoviePy(test_video_file)

        with pytest.raises(ValueError):
            video.seek(-1)

    def test_reset_functionality(self, test_video_file):
        """Test reset functionality."""
        video = VideoStreamMoviePy(test_video_file)

        # Read some frames and seek
        for _ in range(10):
            video.read()
        video.seek(50)

        # Reset should return to beginning
        video.reset()
        assert video.frame_number == 0
        assert video.position.get_seconds() == 0.0

        # Should be able to read from beginning again
        frame = video.read()
        assert frame is not False
        assert video.frame_number == 1

    def test_reset_with_print_infos(self, test_video_file):
        """Test reset with print_infos parameter."""
        video = VideoStreamMoviePy(test_video_file)

        # Read some frames
        for _ in range(5):
            video.read()

        # Reset with print_infos
        video.reset(print_infos=True)
        assert video.frame_number == 0

    def test_frame_consistency_after_seek(self, test_video_file):
        """Test that the same frame is returned when seeking to the same position."""
        video = VideoStreamMoviePy(test_video_file)

        # Seek to a specific position and read frame
        video.seek(30)
        frame1 = video.read(decode=True)

        # Seek to the same position and read again
        video.seek(30)
        frame2 = video.read(decode=True)

        # Frames should be identical
        assert np.array_equal(frame1, frame2)

    def test_position_tracking_accuracy(self, test_video_file):
        """Test position tracking accuracy during sequential reading."""
        video = VideoStreamMoviePy(test_video_file)

        expected_frame = 0
        for _ in range(10):
            frame = video.read()
            assert frame is not False
            expected_frame += 1
            assert video.frame_number == expected_frame

            # Position should increase monotonically
            expected_seconds = (expected_frame - 1) / video.frame_rate
            actual_seconds = video.position.get_seconds()
            assert abs(actual_seconds - expected_seconds) < 0.01


class TestVideoStreamMoviePyEdgeCases:
    """Tests for error handling and edge cases of MoviePy backend."""

    def test_eof_detection(self, test_video_file):
        """Test end-of-file detection and handling."""
        video = VideoStreamMoviePy(test_video_file)

        # Fast forward to near end
        total_frames = int(video.duration.get_frames())
        video.seek(total_frames - 2)

        # Read remaining frames
        frame1 = video.read()
        assert frame1 is not False

        video.read()  # Read without storing the frame

        # Multiple reads past EOF should consistently return False
        eof_result1 = video.read()
        eof_result2 = video.read()

        # At least one of these should be False
        assert eof_result1 is False or eof_result2 is False

    def test_multiple_instances(self, test_video_file):
        """Test creating multiple instances of the same video."""
        video1 = VideoStreamMoviePy(test_video_file)
        video2 = VideoStreamMoviePy(test_video_file)

        # Both should have same properties
        assert video1.frame_rate == video2.frame_rate
        assert video1.frame_size == video2.frame_size
        assert video1.duration.get_seconds() == video2.duration.get_seconds()

        # They should operate independently
        video1.read()
        video2.seek(10)
        video2.read()

        assert video1.frame_number == 1
        assert video2.frame_number == 11

    def test_seek_error_recovery(self, test_video_file):
        """Test that object remains in valid state after seek errors."""
        video = VideoStreamMoviePy(test_video_file)

        # Read some frames first
        for _ in range(5):
            video.read()

        # Attempt invalid seek
        try:
            video.seek(999999)
        except SeekError:
            pass

        # Object should still be usable
        frame = video.read()
        # After a failed seek, the position should be reset to beginning
        assert video.frame_number > 0
        assert frame is not False or video.frame_number == 1
