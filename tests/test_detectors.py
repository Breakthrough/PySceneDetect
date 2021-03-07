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

""" PySceneDetect Scene Detection Tests

These tests ensure that the detection algorithms deliver consistent
results by using known ground truths of scene cut locations in the
test case material.
"""

# Standard project pylint disables for unit tests using pytest.
# pylint: disable=no-self-use, protected-access, multiple-statements, invalid-name
# pylint: disable=redefined-outer-name

# PySceneDetect Library Imports
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_manager import VideoManager
from scenedetect.detectors import ContentDetector
from scenedetect.detectors import ThresholdDetector


# Test case ground truth format: (threshold, [scene start frame])
TEST_MOVIE_CLIP_GROUND_TRUTH_CONTENT = [
    (30, [1198, 1226, 1260, 1281, 1334, 1365, 1697, 1871]),
    (27, [1198, 1226, 1260, 1281, 1334, 1365, 1590, 1697, 1871])
]


def test_content_detector(test_movie_clip):
    """ Test SceneManager with VideoManager and ContentDetector. """
    for threshold, start_frames in TEST_MOVIE_CLIP_GROUND_TRUTH_CONTENT:
        vm = VideoManager([test_movie_clip])
        sm = SceneManager()
        sm.add_detector(ContentDetector(threshold=threshold))

        try:
            video_fps = vm.get_framerate()
            start_time = FrameTimecode('00:00:50', video_fps)
            end_time = FrameTimecode('00:01:19', video_fps)

            vm.set_duration(start_time=start_time, end_time=end_time)
            vm.set_downscale_factor()

            vm.start()
            sm.detect_scenes(frame_source=vm)
            scene_list = sm.get_scene_list()
            assert len(scene_list) == len(start_frames)
            detected_start_frames = [
                timecode.get_frames() for timecode, _ in scene_list ]
            assert all(x == y for (x, y) in zip(start_frames, detected_start_frames))

        finally:
            vm.release()


# Defaults for now.
TEST_VIDEO_FILE_GROUND_TRUTH_THRESHOLD = [
    0, 15, 198, 376
]

def test_threshold_detector(test_video_file):
    """ Test SceneManager with VideoManager and ThresholdDetector. """
    vm = VideoManager([test_video_file])
    sm = SceneManager()
    sm.add_detector(ThresholdDetector())

    try:
        vm.set_downscale_factor()

        vm.start()
        sm.detect_scenes(frame_source=vm)
        scene_list = sm.get_scene_list()
        assert len(scene_list) == len(TEST_VIDEO_FILE_GROUND_TRUTH_THRESHOLD)
        detected_start_frames = [
            timecode.get_frames() for timecode, _ in scene_list ]
        assert all(x == y for (x, y) in zip(
            TEST_VIDEO_FILE_GROUND_TRUTH_THRESHOLD, detected_start_frames))

    finally:
        vm.release()
