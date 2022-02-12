# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2021 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
""" PySceneDetect scenedetect.video_stream Tests

This file includes unit tests for the scenedetect.video_stream module, as well as the video
backends implemented in scenedetect.backends.  These tests enforce a consistent interface across
all supported backends, and verify that they are functionally equivalent where possible.
"""

# Standard project pylint disables for unit tests using pytest.
# pylint: disable=no-self-use, protected-access, multiple-statements, invalid-name
# pylint: disable=redefined-outer-name

from typing import Type
import os.path
# Third-Party Library Imports
import numpy
import pytest

from scenedetect.video_stream import VideoStream
from scenedetect.backends.opencv import VideoStreamCv2

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
## List of Required/TBD Test Cases
## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##

# TODO: End of video read()/seek behaviour!

# TODO: Add checks that frame was decoded properly - compare against
# a set of hand-picked frames? Or just a few colour samples?

# TODO: Add test using image sequence.

# TODO: Create a test case which opens both a corrupted video (set random bytes in the header
# to zeroes until one fails with all backends?).  Can create dynamically by just opening
# the path to a good video, copying it to a temp location, and modifying it in place.

## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##


# Accuracy a framerate is checked to for testing purposes.
FRAMERATE_TOLERANCE = 0.001
# Accuracy a time in milliseconds is checked to for testing purposes.
TIME_TOLERANCE_MS = 0.1


def calculate_frame_delta(frame_a, frame_b, roi=None) -> float:
    if roi:
        assert False # TODO
    assert frame_a.shape == frame_b.shape
    num_pixels = frame_a.shape[0] * frame_a.shape[1]
    return numpy.sum(numpy.abs(frame_b - frame_a)) / num_pixels


def get_absolute_path(relative_path: str) -> str:
    # type: (str) -> str
    """ Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    abs_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError('Test video file (%s) must be present to run test case!' %
                                relative_path)
    return abs_path


class VideoParameters:

    def __init__(self, path: str, height: int, width: int, frame_rate: float, total_frames: int):
        self.path = path
        self.height = height
        self.width = width
        self.frame_rate = frame_rate
        self.total_frames = total_frames
        # TODO: Aspect ratio.


def get_test_video_params():
    # type: () -> str
    """Fixture for parameters of all videos."""
    return [
        VideoParameters(
            path=get_absolute_path("testvideo.mp4"),
            width=1280,
            height=720,
            frame_rate=29.97,
            total_frames=720),
        VideoParameters(
            path=get_absolute_path("goldeneye/goldeneye.mp4"),
            width=1280,
            height=544,
            frame_rate=23.976,
            total_frames=1980),
    ]


pytestmark = pytest.mark.parametrize("vs_type", [VideoStreamCv2])


@pytest.mark.parametrize("test_video", get_test_video_params())
class TestVideoStream:

    def test_basic_params(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        stream = vs_type(test_video.path)
        assert stream.frame_size == (test_video.width, test_video.height)
        assert stream.frame_rate == pytest.approx(test_video.frame_rate, FRAMERATE_TOLERANCE)
        assert stream.duration.get_frames() == test_video.total_frames
        file_name = os.path.basename(test_video.path)
        last_dot_pos = file_name.rfind('.')
        assert stream.name == file_name[:last_dot_pos]

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
        """Validates basic time keeping identities/invariants on the `VideoStream.position`,
        `VideoStream.position_ms`, and `VideoStream.frame_number` properties."""
        stream = vs_type(test_video.path)

        # Before any frame has been decoded, everything is at time/frame 0.
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        assert stream.frame_number == 0

        stream.read()
        # After the first frame has been decoded, position is still at 0 (PTS),
        # but frame_number is 1.
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        assert stream.frame_number == 1


        stream.reset()
        # After resetting the stream, we should be back in the initial time state.
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        assert stream.frame_number == 0

        # Test invariants over the first 100 frames.
        stream.reset()

        for i in range(1, 100 + 1):
            assert stream.read() is not None
            assert stream.position == stream.base_timecode + (i - 1)
            assert stream.position_ms == pytest.approx(1000.0 * (i - 1) / float(stream.frame_rate),
                                                       abs=TIME_TOLERANCE_MS)
            assert stream.frame_number == i
        stream.reset()

    def test_seek(self, vs_type: Type[VideoStream], test_video: VideoParameters):
        """Validate seeking behaviour."""
        #
        # Basic timecode "identities".
        #
        stream = vs_type(test_video.path)

        # Decode a few frames so we don't start at zero already.
        for _ in range(100):
            stream.read()

        # Seek to given time in seconds.
        stream.seek(0.0)
        assert stream.frame_number == 0
        # FrameTimecode is currently one "behind" the frame_number since it
        # starts counting from zero. This should eventually be changed.
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)

        stream.seek(2.0)
        stream.read()
        assert stream.frame_number == 1 + int(stream.frame_rate * 2.0)
        # FrameTimecode is currently one "behind" the frame_number since it
        # starts counting from zero. This should eventually be changed.
        assert stream.position == stream.base_timecode + 2.0
        assert stream.position_ms == pytest.approx(2000.0, abs=1000.0 / stream.frame_rate)

        # Seek to given FrameTimecode.
        stream.seek(stream.base_timecode)
        assert stream.frame_number == 0
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)

        # Seek to a given frame number.
        stream.seek(200)
        assert stream.position == stream.base_timecode + 199
        assert stream.position_ms == pytest.approx(1000.0 * (199.0 / float(stream.frame_rate)),
                                                   abs=TIME_TOLERANCE_MS)
        assert stream.frame_number == 200
        stream.read()
        assert stream.frame_number == 201
        assert stream.position == stream.base_timecode + 200
        assert stream.position_ms == pytest.approx(1000.0 * (200.0 / float(stream.frame_rate)),
                                                   abs=TIME_TOLERANCE_MS)

        # Seek to given time in seconds.
        stream.seek(0)
        assert stream.frame_number == 0
        # FrameTimecode is currently one "behind" the frame_number since it
        # starts counting from zero. This should eventually be changed.
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        stream.seek(1)
        assert stream.frame_number == 1
        # FrameTimecode is currently one "behind" the frame_number since it
        # starts counting from zero. This should eventually be changed.
        assert stream.position == stream.base_timecode
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        stream.read()
        assert stream.frame_number == 2


#
# Tests which only use a single video file
#

def test_invalid_path(vs_type: Type[VideoStream]):
    """Ensure correct exception is thrown if the path does not exist."""
    with pytest.raises(IOError):
        _ = vs_type('this_path_should_not_exist.mp4')


def test_seek_invalid(vs_type: Type[VideoStream], test_video_file: str):
    """Test `seek()` throws correct exception when specifying in invalid seek value."""
    stream = vs_type(test_video_file)

    with pytest.raises(ValueError):
        stream.seek(-1)

    with pytest.raises(ValueError):
        stream.seek(-0.1)



def test_reset(vs_type: Type[VideoStream], test_video_file: str):
    """Test `reset()` functions as expected."""
    stream = vs_type(test_video_file)

    for _ in range(3):
        stream.read()
    assert stream.frame_number > 0
    stream.reset()
    assert stream.frame_number == 0
    assert stream.position == 0
    assert stream.position_ms == pytest.approx(0, abs=TIME_TOLERANCE_MS)

