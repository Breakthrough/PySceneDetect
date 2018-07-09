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
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy and OpenCV; see the LICENSE-NUMPY and
# LICENSE-OPENCV files or visit one of above URLs for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.video_manager Tests

This file includes unit tests for the scenedetect.video_manager module (specifically,
the VideoManager object, which uses an underlying VideoDecoder object as a multithreaded
video decoder, allowing seeking and concatenation of multiple sources).

These tests rely on the testvideo.mp4 test video file, available by checking out the
PySceneDetect git repository "resources" branch, or the following URL to download it
directly:  https://github.com/Breakthrough/PySceneDetect/tree/resources/tests
"""

import unittest
import time
import os

import pytest
import cv2

from scenedetect.video_manager import VideoManager
from scenedetect.video_manager_async import VideoManagerAsync
from scenedetect.video_manager import VideoOpenFailure
from scenedetect.video_manager import VideoFramerateUnavailable
from scenedetect.video_manager import VideoParameterMismatch
from scenedetect.video_manager import VideoDecodingInProgress
from scenedetect.video_manager import VideoDecoderProcessStarted
from scenedetect.video_manager import VideoDecoderProcessNotStarted


TEST_VIDEO_FILE = 'testvideo.mp4'

class TestVideoManager(unittest.TestCase):
    """ VideoDecoder Unit Test Cases

    These unit tests test the VideoManager object with respect to object construction,
    testing argument format/limits, opening videos and grabbing frames, and appending
    multiple videos together.  These tests rely on testvideo.mp4, available in the
    PySceneDetect git repository "resources" branch.
    """

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_VIDEO_FILE):
            raise FileNotFoundError(
                'Test video file (%s) must be present to run test cases' % TEST_VIDEO_FILE)

    def test_video_params(self):
        video_manager = VideoManager([TEST_VIDEO_FILE] * 2)
        try:
            cap = cv2.VideoCapture(TEST_VIDEO_FILE)
            assert cap.isOpened()
            assert video_manager.get_framerate() == pytest.approx(cap.get(cv2.CAP_PROP_FPS))
            self.assertEqual(
                (cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                video_manager.get_framesize())
            cap.release()
        finally:
            video_manager.release()
        

    def test_start_stop(self):
        video_manager = VideoManager([TEST_VIDEO_FILE] * 2)
        # *must* call stop() after start() or video manager process will
        # be rogue.
        try:
            video_manager.start()
            # even if exception thrown here, video manager process will stop.
        finally:
            video_manager.stop()
            video_manager.release()


    def test_get_property(self):
        video_manager = VideoManager([TEST_VIDEO_FILE] * 3)
        self.assertAlmostEqual(
            video_manager.get(cv2.CAP_PROP_FPS), video_manager.get_framerate())
        self.assertAlmostEqual(
            video_manager.get(cv2.CAP_PROP_FPS, 1), video_manager.get_framerate())
        self.assertAlmostEqual(
            video_manager.get(cv2.CAP_PROP_FPS, 2), video_manager.get_framerate())
        video_manager.release()

    def test_wrong_video_files_type(self):
        ''' Test VideoDecoder constructor (__init__ method) with invalid video_files
        argument types to trigger ValueError/TypeError exceptions. '''
        self.assertRaises(ValueError, VideoManager, [0, 1, 2])
        self.assertRaises(ValueError, VideoManager, [0, 'somefile'])
        self.assertRaises(ValueError, VideoManager, ['somefile', 1, 2, 'somefile'])
        self.assertRaises(ValueError, VideoManager, ['somefile', 1, 'somefile', 2])
        self.assertRaises(ValueError, VideoManager, [-1])

    def test_video_open_failure(self):
        ''' Test VideoDecoder constructor (__init__ method) with invalid filename(s)
        and device IDs to trigger an IOError/VideoOpenFailure exception. '''
        # Attempt to open non-existing video files should raise an IOError.
        self.assertRaises(IOError, VideoManager, ['fauxfile.mp4'])
        self.assertRaises(IOError, VideoManager, ['fauxfile.mp4', 'otherfakefile.mp4'])
        # Attempt to open 99th video device should raise a VideoOpenFailure since
        # the OpenCV VideoCapture open() method will likely fail (unless the test
        # case computer has 100 webcams or more...)
        self.assertRaises(VideoOpenFailure, VideoManager, [99])
        # Test device IDs > 100.
        self.assertRaises(VideoOpenFailure, VideoManager, [120])
        self.assertRaises(VideoOpenFailure, VideoManager, [255])


    

class TestVideoManagerAsync(unittest.TestCase):
    """ VideoDecoderAsync Unit Test Cases

    These unit tests test the VideoManagerAsync object with respect to object construction,
    testing argument format/limits, opening videos and grabbing frames, and appending
    multiple videos together.  These tests rely on testvideo.mp4, available in the
    PySceneDetect git repository "resources" branch.
    """

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_VIDEO_FILE):
            raise FileNotFoundError(
                'Test video file (%s) must be present to run test cases' % TEST_VIDEO_FILE)

    def test_video_params(self):
        video_manager = VideoManagerAsync([TEST_VIDEO_FILE] * 2)
        try:
            cap = cv2.VideoCapture(TEST_VIDEO_FILE)
            self.assertTrue(cap.isOpened())
            self.assertAlmostEqual(
                cap.get(cv2.CAP_PROP_FPS), video_manager.get_framerate())
            self.assertEqual(
                (cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                video_manager.get_framesize())
            cap.release()
        finally:
            video_manager.release()
        

    def test_start_stop(self):
        video_manager = VideoManagerAsync([TEST_VIDEO_FILE] * 2)
        # *must* call stop() after start() or video manager process will
        # be rogue.
        try:
            video_manager.start()
            # even if exception thrown here, video manager process will stop.
        finally:
            video_manager.stop()
            video_manager.release()


    def test_get_property(self):
        video_manager = VideoManagerAsync([TEST_VIDEO_FILE] * 3)
        self.assertAlmostEqual(
            video_manager.get(cv2.CAP_PROP_FPS), video_manager.get_framerate())
        self.assertAlmostEqual(
            video_manager.get(cv2.CAP_PROP_FPS, 1), video_manager.get_framerate())
        self.assertAlmostEqual(
            video_manager.get(cv2.CAP_PROP_FPS, 2), video_manager.get_framerate())
        video_manager.release()

    def test_wrong_video_files_type(self):
        ''' Test VideoDecoder constructor (__init__ method) with invalid video_files
        argument types to trigger ValueError/TypeError exceptions. '''
        self.assertRaises(ValueError, VideoManagerAsync, [0, 1, 2])
        self.assertRaises(ValueError, VideoManagerAsync, [0, 'somefile'])
        self.assertRaises(ValueError, VideoManagerAsync, ['somefile', 1, 2, 'somefile'])
        self.assertRaises(ValueError, VideoManagerAsync, ['somefile', 1, 'somefile', 2])
        self.assertRaises(ValueError, VideoManagerAsync, [-1])

    def test_video_open_failure(self):
        ''' Test VideoDecoder constructor (__init__ method) with invalid filename(s)
        and device IDs to trigger an IOError/VideoOpenFailure exception. '''
        # Attempt to open non-existing video files should raise an IOError.
        self.assertRaises(IOError, VideoManagerAsync, ['fauxfile.mp4'])
        self.assertRaises(IOError, VideoManagerAsync, ['fauxfile.mp4', 'otherfakefile.mp4'])
        # Attempt to open 99th video device should raise a VideoOpenFailure since
        # the OpenCV VideoCapture open() method will likely fail (unless the test
        # case computer has 100 webcams or more...)
        self.assertRaises(VideoOpenFailure, VideoManagerAsync, [99])
        # Test device IDs > 100.
        self.assertRaises(VideoOpenFailure, VideoManagerAsync, [120])
        self.assertRaises(VideoOpenFailure, VideoManagerAsync, [255])


    
