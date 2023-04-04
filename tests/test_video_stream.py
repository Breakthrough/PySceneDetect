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
""" PySceneDetect scenedetect.video_stream Tests

This file includes unit tests for the scenedetect.video_stream module, as well as the video
backends implemented in scenedetect.backends.  These tests enforce a consistent interface across
all supported backends, and verify that they are functionally equivalent where possible.
"""

# pylint: disable=no-self-use,missing-function-docstring

from dataclasses import dataclass
from typing import List, Type
import os.path

import numpy
import pytest

from scenedetect.video_stream import VideoStream, SeekError
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.backends import VideoStreamAv
from scenedetect.backends import VideoStreamMoviePy
from scenedetect.video_manager import VideoManager

# Accuracy a framerate is checked to for testing purposes.
FRAMERATE_TOLERANCE = 0.001

# Accuracy a time in milliseconds is checked to for testing purposes.
TIME_TOLERANCE_MS = 0.1

# Accuracy a pixel aspect ratio is checked to for testing purposes.
PIXEL_ASPECT_RATIO_TOLERANCE = 0.001

# Filter for warnings we ignore from VideoStreamMoviePy (warnings come from FFMPEG_VideoReader).
# The warning occurs when reading the last frame, which VideoStreamMoviePy handles gracefully.
MOVIEPY_WARNING_FILTER = "ignore:.*Using the last valid frame instead.:UserWarning"


def calculate_frame_delta(frame_a, frame_b, roi=None) -> float:
    if roi:
        assert False # TODO
    assert frame_a.shape == frame_b.shape
    num_pixels = frame_a.shape[0] * frame_a.shape[1]
    return numpy.sum(numpy.abs(frame_b - frame_a)) / num_pixels


# TODO: Reduce code duplication here and in `conftest.py`
def get_absolute_path(relative_path: str) -> str:
    """ Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    abs_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError("""
Test video file (%s) must be present to run test case. This file can be obtained by running the following commands from the root of the repository:

git fetch --depth=1 https://github.com/Breakthrough/PySceneDetect.git refs/heads/resources:refs/remotes/origin/resources
git checkout refs/remotes/origin/resources -- tests/resources/
git reset
""" % relative_path)
    return abs_path


@dataclass
class VideoParameters:
    """Properties for each input a VideoStream is tested against."""
    path: str
    height: int
    width: int
    frame_rate: float
    total_frames: int
    aspect_ratio: float


# TODO: Save two "golden" frames from each video on a shot boundary, and use that to validate
# that seeking works correctly for all backends (as well as that no frames are dropped).
def get_test_video_params() -> List[VideoParameters]:
    """Fixture for parameters of all videos."""
    return [
        VideoParameters(
            path=get_absolute_path("resources/testvideo.mp4"),
            width=1280,
            height=720,
            frame_rate=29.97,
            total_frames=720,
            aspect_ratio=1.0,
        ),
        VideoParameters(
            path=get_absolute_path("resources/goldeneye.mp4"),
            width=1280,
            height=544,
            frame_rate=23.976,
            total_frames=1980,
            aspect_ratio=1.0,
        ),
        VideoParameters(
            path=get_absolute_path("resources/issue-195-aspect-ratio.mp4"),
            width=704,
            height=576,
            frame_rate=25.0,
            total_frames=628,
            aspect_ratio=1.4545454545,
        ),
    ]


pytestmark = [
    pytest.mark.parametrize(
        "vs_type",
        list(
            filter(lambda x: x is not None, [
                VideoStreamCv2,
                VideoStreamAv,
                VideoStreamMoviePy,
                VideoManager,
            ]))),
    pytest.mark.filterwarnings(MOVIEPY_WARNING_FILTER),
]


@pytest.mark.parametrize("test_video", get_test_video_params())
class TestVideoStream:
    """Fixture for tests which run against different input videos."""

    def test_properties(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate video properties: frame size, frame rate, duration, aspect ratio, etc."""
        stream = vs_type(test_video.path)
        assert stream.frame_size == (test_video.width, test_video.height)
        assert stream.frame_rate == pytest.approx(test_video.frame_rate, FRAMERATE_TOLERANCE)
        assert stream.duration.get_frames() == test_video.total_frames
        file_name = os.path.basename(test_video.path)
        last_dot_pos = file_name.rfind('.')
        assert stream.name == file_name[:last_dot_pos]
        assert stream.aspect_ratio == pytest.approx(test_video.aspect_ratio,
                                                    PIXEL_ASPECT_RATIO_TOLERANCE)

    def test_read(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate basic `read` functionality."""
        stream = vs_type(test_video.path)
        frame = stream.read()
        # For now hard-code 3 channels/pixel for each test video
        assert frame.shape == (test_video.height, test_video.width, 3)
        assert stream.frame_number == 1

    def test_read_no_advance(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate invoking `read` with `advance` set to False."""
        stream = vs_type(test_video.path)
        frame = stream.read().copy()
        assert stream.frame_number == 1
        frame_copy = stream.read(advance=False)
        assert stream.frame_number == 1
        assert calculate_frame_delta(frame, frame_copy) == pytest.approx(0.0)

    def test_read_no_decode(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate invoking `read` with `decode` set to False."""
        stream = vs_type(test_video.path)
        assert stream.read(decode=False) is True
        assert stream.frame_number == 1
        stream.read(decode=False, advance=False)
        assert stream.frame_number == 1

    def test_time_invariants(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate the `frame_number`, `position`, and `position_ms` properties."""
        stream = vs_type(test_video.path)
        # The video starts "before" the first frame, with everything set to zero.
        assert stream.frame_number == 0
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        # Read the first frame (frame number 1).
        assert stream.read() is not False
        assert stream.frame_number == 1
        # The `position`/`position_ms` properties represent the presentation time, so they
        # should still be zero for the first frame.
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        # Test that the invariants hold for the first few frames.
        for i in range(2, 10):
            assert stream.read() is not False
            assert stream.frame_number == i
            assert stream.position == stream.base_timecode + (i - 1)
            assert stream.position_ms == pytest.approx(
                1000.0 * (i - 1) / float(stream.frame_rate), abs=TIME_TOLERANCE_MS)

    def test_reset(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Test `reset()` functions as expected."""
        stream = vs_type(test_video.path)
        # Decode some frames, then reset the VideoStream and validate the time invariants.
        for _ in range(10):
            stream.read()
        assert stream.frame_number == 10
        stream.reset()
        assert stream.frame_number == 0
        assert stream.position == 0
        assert stream.position_ms == pytest.approx(0, abs=TIME_TOLERANCE_MS)

    def test_seek(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate `seek()` functionality with different offset types."""
        stream = vs_type(test_video.path)

        # Seek to a given frame number (int).
        stream.seek(200)
        assert stream.frame_number == 200
        assert stream.position == stream.base_timecode + 199
        assert stream.position_ms == pytest.approx(
            1000.0 * (199.0 / float(stream.frame_rate)), abs=TIME_TOLERANCE_MS)
        stream.read()
        assert stream.frame_number == 201
        assert stream.position == stream.base_timecode + 200
        assert stream.position_ms == pytest.approx(
            1000.0 * (200.0 / float(stream.frame_rate)), abs=TIME_TOLERANCE_MS)

        # Seek to a time in seconds (float).
        stream.seek(2.0)
        assert stream.frame_number == round(stream.frame_rate * 2.0)
        # FrameTimecode is currently one "behind" the frame_number since it
        # starts counting from zero. This should eventually be changed.
        assert stream.position == (stream.base_timecode + 2.0) - 1
        assert stream.position_ms == pytest.approx(
            2000.0 - (1000.0 / stream.frame_rate), abs=1000.0 / stream.frame_rate)
        stream.read()
        assert stream.frame_number == 1 + round(stream.frame_rate * 2.0)
        assert stream.position == stream.base_timecode + 2.0
        assert stream.position_ms == pytest.approx(2000.0, abs=1000.0 / stream.frame_rate)

        # Seek to a FrameTimecode.
        stream.seek(stream.base_timecode + 2.0)
        assert stream.frame_number == round(stream.frame_rate * 2.0)
        # FrameTimecode is currently one "behind" the frame_number since it
        # starts counting from zero. This should eventually be changed.
        assert stream.position == (stream.base_timecode + 2.0) - 1
        assert stream.position_ms == pytest.approx(
            2000.0 - (1000.0 / stream.frame_rate), abs=1000.0 / stream.frame_rate)
        stream.read()
        assert stream.frame_number == 1 + round(stream.frame_rate * 2.0)
        assert stream.position == stream.base_timecode + 2.0
        assert stream.position_ms == pytest.approx(2000.0, abs=1000.0 / stream.frame_rate)

    def test_seek_start(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate behaviour of `seek()` at the start of a video."""
        stream = vs_type(test_video.path)
        # Here we check similar invariants to test_time_invariants, but using seek().
        assert stream.frame_number == 0
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        # Seeking to frame 0 (or time 0) is equivalent to seeking "before" the first frame.
        stream.seek(0)
        assert stream.frame_number == 0
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        # Ensure invariants hold for the first few frames.
        for i in range(1, 10):
            assert stream.read() is not False
            assert stream.frame_number == i
            assert stream.position == stream.base_timecode + (i - 1)
            assert stream.position_ms == pytest.approx(
                1000.0 * (i - 1) / float(stream.frame_rate), abs=TIME_TOLERANCE_MS)
        stream.seek(0)
        assert stream.frame_number == 0
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)

        # Seek to the first frame (1) instead of the start (0) and verify the invariants.
        stream.seek(1)
        assert stream.frame_number == 1
        # Position and position_ms represent the presentation time, and thus are still zero.
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        stream.read()
        assert stream.frame_number == 2
        stream = vs_type(test_video.path)

    def test_read_eof(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Ensure calling `read()` handles the end of the video correctly."""
        stream = vs_type(test_video.path)
        # To make the test faster, we seek to the second last frame.
        stream.seek(test_video.total_frames - 1)
        while stream.read() is not False:
            pass
        # TODO: On some videos, the PyAV backend seems to drop a frame. See where this occurs.
        if vs_type == VideoStreamAv:
            assert stream.frame_number in (test_video.total_frames, test_video.total_frames - 1)
        else:
            assert stream.frame_number == test_video.total_frames

    def test_seek_past_eof(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate calling `seek()` to offset past end of video."""
        if vs_type == VideoManager:
            pytest.skip(reason='VideoManager does not have compliant end-of-video seek behaviour.')
        stream = vs_type(test_video.path)
        # Seek to a large seek offset past the end of the video. Some backends only support 32-bit
        # frame numbers so that's our max offset. Certain backends disallow seek offsets past EOF,
        # in which case they should raise a SeekError (and the test is considered a pass).
        try:
            stream.seek(2**32)
        except SeekError:
            return
        # For those backends that do allow seek offsets past EOF, they should act as though we
        # seeked to the end of the video (i.e. shouldn't be able to decode any more frames).
        assert stream.read(advance=True) is False
        assert stream.read(advance=False) is not False
        # TODO: On some videos, the PyAV backend seems to drop a frame. See where this occurs.
        if vs_type == VideoStreamAv:
            assert stream.frame_number in (test_video.total_frames, test_video.total_frames - 1)
        else:
            assert stream.frame_number == test_video.total_frames

    def test_seek_invalid(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Test `seek()` throws correct exception when specifying in invalid seek value."""
        stream = vs_type(test_video.path)

        with pytest.raises(ValueError):
            stream.seek(-1)

        with pytest.raises(ValueError):
            stream.seek(-0.1)


#
# Tests which run against a specific inputs.
#


def test_invalid_path(vs_type: Type[VideoStream]):
    """Ensure correct exception is thrown if the path does not exist."""
    with pytest.raises(OSError):
        _ = vs_type('this_path_should_not_exist.mp4')


def test_corrupt_video(vs_type: Type[VideoStream], corrupt_video_file: str):
    """Test that backend handles video with corrupt frame gracefully with defaults."""
    if vs_type == VideoManager:
        pytest.skip(reason='VideoManager does not support handling corrupt videos.')

    stream = vs_type(corrupt_video_file)

    # OpenCV usually fails to read the video at frame 45, so we make sure all backends can
    # get to 100 without reporting a failure.
    for frame in range(100):
        assert stream.read() is not False, "Failed on frame %d!" % frame
