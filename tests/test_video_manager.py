# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2020 Brandon Castellano <http://www.bcastell.com>.
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


# Third-Party Library Imports
import pytest
import cv2

from scenedetect.scene_manager import SceneManager
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
    argument types to trigger a ValueError exception. """
    with pytest.raises(ValueError): VideoManager([0, 1, 2])
    with pytest.raises(ValueError): VideoManager([0, 'somefile'])
    with pytest.raises(ValueError): VideoManager(['somefile', 1, 2, 'somefile'])
    with pytest.raises(ValueError): VideoManager([-1])


def test_wrong_framerate_type(test_video_file):
    """ Test VideoManager constructor (__init__ method) with an invalid framerate
    argument types to trigger a TypeError exception. """
    with pytest.raises(TypeError): VideoManager([test_video_file], framerate=int(0))
    with pytest.raises(TypeError): VideoManager([test_video_file], framerate=int(10))
    with pytest.raises(TypeError): VideoManager([test_video_file], framerate='10')
    VideoManager([test_video_file], framerate=float(10)).release()


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


def test_grab_retrieve(test_video_file):
    """ Test VideoManager grab/retrieve methods. """
    video_manager = VideoManager([test_video_file] * 2)
    base_timecode = video_manager.get_base_timecode()
    try:
        video_manager.start()
        assert video_manager.get_current_timecode() == base_timecode
        for i in range(1, 10):
            # VideoManager.grab() -> bool
            ret_val = video_manager.grab()
            assert ret_val
            assert video_manager.get_current_timecode() == base_timecode + i
            # VideoManager.retrieve() -> Tuple[bool, numpy.ndarray]
            ret_val, frame_image = video_manager.retrieve()
            assert ret_val
            assert frame_image.shape[0] > 0
            assert video_manager.get_current_timecode() == base_timecode + i
    finally:
        video_manager.release()


def test_read(test_video_file):
    """ Test VideoManager read method. """
    video_manager = VideoManager([test_video_file] * 2)
    base_timecode = video_manager.get_base_timecode()
    try:
        video_manager.start()
        assert video_manager.get_current_timecode() == base_timecode
        for i in range(1, 10):
            # VideoManager.read() -> Tuple[bool, numpy.ndarray]
            ret_val, frame_image = video_manager.read()
            assert ret_val
            assert frame_image.shape[0] > 0
            assert video_manager.get_current_timecode() == base_timecode + i
    finally:
        video_manager.release()


def test_seek(test_video_file):
    """ Test VideoManager seek method. """
    video_manager = VideoManager([test_video_file] * 2)
    base_timecode = video_manager.get_base_timecode()
    try:
        video_manager.start()
        assert video_manager.get_current_timecode() == base_timecode
        ret_val, frame_image = video_manager.read()
        assert ret_val
        assert frame_image.shape[0] > 0
        assert video_manager.get_current_timecode() == base_timecode + 1

        assert video_manager.seek(base_timecode + 10)
        assert video_manager.get_current_timecode() == base_timecode + 10
        ret_val, frame_image = video_manager.read()
        assert ret_val
        assert frame_image.shape[0] > 0
        assert video_manager.get_current_timecode() == base_timecode + 11

    finally:
        video_manager.release()


def test_reset(test_video_file):
    """ Test VideoManager reset method. """
    video_manager = VideoManager([test_video_file] * 2)
    base_timecode = video_manager.get_base_timecode()
    try:
        video_manager.start()
        assert video_manager.get_current_timecode() == base_timecode
        ret_val, frame_image = video_manager.read()
        assert ret_val
        assert frame_image.shape[0] > 0
        assert video_manager.get_current_timecode() == base_timecode + 1

        video_manager.release()
        video_manager.reset()

        video_manager.start()
        assert video_manager.get_current_timecode() == base_timecode
        ret_val, frame_image = video_manager.read()
        assert ret_val
        assert frame_image.shape[0] > 0
        assert video_manager.get_current_timecode() == base_timecode + 1

    finally:
        video_manager.release()


def test_multiple_videos(test_video_file):
    """ Test VideoManager handling decoding frames across video boundaries. """

    NUM_FRAMES = 10
    NUM_VIDEOS = 3
    # Open VideoManager and get base timecode.
    video_manager = VideoManager([test_video_file] * NUM_VIDEOS)
    base_timecode = video_manager.get_base_timecode()

    # List of NUM_VIDEOS VideoManagers pointing to test_video_file.
    vm_list = [
        VideoManager([test_video_file]),
        VideoManager([test_video_file]),
        VideoManager([test_video_file])]

    # Set duration of all VideoManagers in vm_list to NUM_FRAMES frames.
    for vm in vm_list: vm.set_duration(duration=base_timecode+NUM_FRAMES)
    # (FOR TESTING PURPOSES ONLY) Manually override _cap_list with the
    # duration-limited VideoManager objects in vm_list
    video_manager._cap_list = vm_list

    try:
        for vm in vm_list: vm.start()
        video_manager.start()
        assert video_manager.get_current_timecode() == base_timecode

        curr_time = video_manager.get_base_timecode()
        while True:
            ret_val, frame_image = video_manager.read()
            if not ret_val:
                break
            assert frame_image.shape[0] > 0
            curr_time += 1
        assert curr_time == base_timecode + ((NUM_FRAMES+1) * NUM_VIDEOS)

    finally:
        # Will release the VideoManagers in vm_list as well.
        video_manager.release()

def test_many_videos_downscale_detect_scenes(test_video_file):
    """ Test scene detection on multiple videos in VideoManager. """

    NUM_VIDEOS = 3
    # Open VideoManager with NUM_VIDEOS test videos
    video_manager = VideoManager([test_video_file] * NUM_VIDEOS)
    video_manager.set_downscale_factor()

    try:
        video_manager.start()
        scene_manager = SceneManager()
        scene_manager.detect_scenes(frame_source=video_manager)
    finally:
        # Will release the VideoManagers in vm_list as well.
        video_manager.release()
