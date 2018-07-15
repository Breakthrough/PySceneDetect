# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses Numpy, OpenCV, click, pytest, mkvmerge, and ffmpeg. See
# the included LICENSE-* files, or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.video_manager Tests

This file includes unit tests for the scenedetect.video_manager module, acting as
a video container/decoder, allowing seeking and concatenation of multiple sources.

These unit tests test the VideoManager object with respect to object construction,
testing argument format/limits, opening videos and grabbing frames, and appending
multiple videos together.  These tests rely on testvideo.mp4, available in the
PySceneDetect git repository "resources" branch.

These tests rely on the testvideo.mp4 test video file, available by checking out the
PySceneDetect git repository "resources" branch, or the following URL to download it
directly:  https://github.com/Breakthrough/PySceneDetect/tree/resources/tests
"""

# Standard project pylint disables for unit tests using pytest.
# pylint: disable=no-self-use, protected-access, multiple-statements, invalid-name
# pylint: disable=redefined-outer-name


# Standard Library Imports
import os

# Third-Party Library Imports
import pytest
import cv2

# PySceneDetect Library Imports
from scenedetect.video_manager import VideoManager

from scenedetect.video_manager import VideoOpenFailure
# TODO: The following exceptions still require test cases:
from scenedetect.video_manager import VideoDecodingInProgress
from scenedetect.video_manager import VideoDecoderNotStarted
# TODO: Need to implement a mock VideoCapture to test the exceptions below.
# TODO: The following exceptions still require test cases:
from scenedetect.video_manager import VideoFramerateUnavailable
from scenedetect.video_manager import VideoParameterMismatch


TEST_VIDEO_FILE = 'testvideo.mp4'       # Video file used by test_video_file fixture.


@pytest.fixture
def test_video_file():
    # type: () -> str
    """ Fixture for test video file path (ensures file exists).
    
    Access in test case by adding a test_video_file argument to obtain the path.
    """
    if not os.path.exists(TEST_VIDEO_FILE):
        raise FileNotFoundError(
            'Test video file (%s) must be present to run test cases' % TEST_VIDEO_FILE)
    return TEST_VIDEO_FILE


def test_video_params(test_video_file):
    """ Test VideoManager get_framerate/get_framesize methods on test_video_file. """
    try:
        cap = cv2.VideoCapture(test_video_file)
        video_manager = VideoManager([test_video_file] * 2)
        assert cap.isOpened()
        assert video_manager.get_framerate() == pytest.approx(cap.get(cv2.CAP_PROP_FPS))
        assert video_manager.get_framesize() == (
            pytest.approx(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            pytest.approx(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    finally:
        cap.release()
        video_manager.release()


def test_start_release(test_video_file):
    """ Test VideoManager start/release methods on 3 appended videos. """
    video_manager = VideoManager([test_video_file] * 2)
    # *must* call release() after start() or video manager process will be rogue.
    #
    # The start method is the only big usage differences between the
    # VideoManager and cv2.VideoCapture objects from the point of view
    # of a SceneManager (the other VideoManager methods function
    # independently of it's job as a frame source).
    try:
        video_manager.start()
        # even if exception thrown here, video manager process will stop.
    finally:
        video_manager.release()


def test_get_property(test_video_file):
    """ Test VideoManager get method on test_video_file. """
    video_manager = VideoManager([test_video_file] * 3)
    video_framerate = video_manager.get_framerate()
    assert video_manager.get(cv2.CAP_PROP_FPS) == pytest.approx(video_framerate)
    assert video_manager.get(cv2.CAP_PROP_FPS, 1) == pytest.approx(video_framerate)
    assert video_manager.get(cv2.CAP_PROP_FPS, 2) == pytest.approx(video_framerate)
    video_manager.release()


def test_wrong_video_files_type():
    """ Test VideoManager constructor (__init__ method) with invalid video_files
    argument types to trigger ValueError/TypeError exceptions. """
    with pytest.raises(ValueError): VideoManager([0, 1, 2])
    with pytest.raises(ValueError): VideoManager([0, 'somefile'])
    with pytest.raises(ValueError): VideoManager(['somefile', 1, 2, 'somefile'])
    with pytest.raises(ValueError): VideoManager([-1])


def test_video_open_failure():
    """ Test VideoManager constructor (__init__ method) with invalid filename(s)
    and device IDs to trigger an IOError/VideoOpenFailure exception. """
    # Attempt to open non-existing video files should raise an IOError.
    with pytest.raises(IOError): VideoManager(['fauxfile.mp4'])
    with pytest.raises(IOError): VideoManager(['fauxfile.mp4', 'otherfakefile.mp4'])
    # Attempt to open 99th video device should raise a VideoOpenFailure since
    # the OpenCV VideoCapture open() method will likely fail (unless the test
    # case computer has 100 webcams or more...)
    with pytest.raises(VideoOpenFailure): VideoManager([99])
    # Test device IDs > 100.
    with pytest.raises(VideoOpenFailure): VideoManager([120])
    with pytest.raises(VideoOpenFailure): VideoManager([255])

