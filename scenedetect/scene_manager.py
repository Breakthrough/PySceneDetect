# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains the SceneManager class, which provides a
# consistent interface to the application state, including the current
# scene list, user-defined options, and any shared objects.
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy, OpenCV, and click; see the included LICENSE-
# files for copyright information, or visit one of the above URLs.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.scene_manager Module

This module implements the SceneManager object, which is used to coordinate
SceneDetectors and frame sources (e.g. VideoManagers, VideoCaptures), creating
a SceneResult object for each detected scene.

The SceneManager also facilitates passing a StatsManager, if any is defined,
to the associated SceneDetectors for caching of frame metrics.
"""


# Standard Library Imports
from __future__ import print_function
import time

# PySceneDetect Library Imports
import scenedetect.platform
import scenedetect.scene_detectors

import scenedetect.frame_timecode
from scenedetect.frame_timecode import FrameTimecode

import scenedetect.video_manager
from scenedetect.video_manager import VideoManager
from scenedetect.video_manager_async import compute_queue_size

import scenedetect.stats_manager
from scenedetect.stats_manager import StatsManager

# Third-Party Library Imports
import cv2
import numpy


class SceneManager(object):

    def __init__(self, stats_manager=None):
        # type: (Optional[StatsManager])
        self._cutting_list = []
        self._detector_list = []
        self._stats_manager = stats_manager
        self._base_timecode = None

    def add_detector(self, detector):
        # type: (SceneDetector) -> None
        self._detector_list.append(detector)
        if self._stats_manager is not None:
            self._stats_manager.register_metrics(detector.get_metrics())


    def clear(self):
        # type: () -> None
        """ Clear All Scenes/Cuts """
        self._cutting_list.clear()

    def clear_detectors(self):
        # type: () -> None
        self._detector_list.clear()


    def add_cut(self, frame_num):
        # type: (int) -> None
        # Adds a cut to the cutting list.
        self._cutting_list.append(frame_num)


    def get_scene_list(self):
        # Need to go through all cuts & cutting list frames
        raise NotImplementedError()


    def _get_cutting_list(self):
        # type: () -> list
        return sorted(self._cutting_list)


    def process_frame(self, frame_num, frame_im):
        # type(int, numpy.ndarray) -> None
        cut_detected = False
        for detector in self._detector_list:
            cut_detected, cut_frame = detector.process_frame(
                frame_num, frame_im, self._stats_manager)
            if cut_detected:
                cut_detected = True
                self.add_cut(cut_frame)

        
    def detect_scenes(self, frame_source, start_time=0, end_time=None):
        # type: (VideoManager, Union[int, FrameTimecode],
        #        Optional[Union[int, FrameTimecode]]) -> int
        """ Perform scene detection using passed video(s) in frame_source and
        detector(s) in detector_list.  Blocks until all frames in the frame_source
        have been processed.  Returns tuple of (frames processed, scenes detected).
        Results can be obtained by calling the get_scene_list() method afterwards.  

        Arguments:
            frame_source (scenedetect.VideoManager or cv2.VideoCapture):  A source of
                frames to process (using frame_source.read() as in VideoCapture).
                VideoManager is preferred as it allows concatenation of multiple videos
                as well as seeking, by defining start time and end time/duration.
            start_time (int or FrameTimecode): Time/frame the passed frame_source object
                is currently at in time (i.e. the frame # read() will return next).
            end_time (int or FrameTimecode): Maximum number of frames to detect
                (set to None to detect all available frames).
        Returns:
            Tuple of (# frames processed, # scenes detected).
        Raises:
            ValueError
        """

        start_frame = 0
        curr_frame = 0
        end_frame = None

        if isinstance(start_time, FrameTimecode):
            start_frame = start_time.get_frames()
        elif start_time is not None:
            start_frame = int(start_time)

        curr_frame = start_frame

        if isinstance(end_time, FrameTimecode):
            end_frame = end_time.get_frames()
        elif end_time is not None:
            end_frame = int(end_time)

        while True:
            if end_frame is not None and curr_frame > end_frame:
                break
            ret_val, frame_im = frame_source.read()
            if not ret_val:
                break
            self.process_frame(curr_frame, frame_im)
            curr_frame += 1


        num_frames = curr_frame - start_frame

        print(" ")
        print(" ")
        print(" ")
        print("READ %d FRAMES!" % num_frames)
        print(" ")
        print(" ")
        print(" ")

        return num_frames



class ContentDetectorNew(scenedetect.scene_detectors.SceneDetector):
    """Detects fast cuts using changes in colour and intensity between frames.

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.  To detect slow fades between
    content scenes still using HSV information, use the DissolveDetector.
    """

    def __init__(self, threshold = 30.0, min_scene_len = 15):
        super(ContentDetectorNew, self).__init__()
        self.threshold = threshold
        self.min_scene_len = min_scene_len  # minimum length of any given scene, in frames
        self.last_frame = None
        self.last_scene_cut = None
        self.last_hsv = None
        self._metric_keys = ['delta_hsv_avg', 'delta_hue', 'delta_sat', 'delta_lum']


    def get_metrics(self):
        # type: () -> List[str]
        """ Get Metrics:  Get a list of all metric names/keys used by the detector.
        
        Returns:
            A List[str] of the frame metric key names that will be used by
            the detector when a StatsManager is passed to process_frame.
        """
        return self._metric_keys


    def process_frame(self, frame_num, frame_img, stats_manager=None):
        # type: (int, numpy.ndarray, Optional[StatsManager]) -> bool, Optional[int]
        # Similar to ThresholdDetector, but using the HSV colour space DIFFERENCE instead
        # of single-frame RGB/grayscale intensity (thus cannot detect slow fades with this method).

        # Value to return indiciating if a scene cut was found or not.
        cut_detected = False
        cut_frame = None
        metric_keys = self._metric_keys

        if self.last_frame is not None:
            # Change in average of HSV (hsv), (h)ue only, (s)aturation only, (l)uminance only.
            delta_hsv_avg, delta_h, delta_s, delta_v = 0.0, 0.0, 0.0, 0.0

            if stats_manager is not None and stats_manager.metrics_exist(frame_num, metric_keys):
                delta_hsv_avg, delta_h, delta_s, delta_v = stats_manager.get_metrics(
                    frame_num, metric_keys)

            else:
                num_pixels = frame_img.shape[0] * frame_img.shape[1]
                curr_hsv = cv2.split(cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV))
                last_hsv = self.last_hsv
                if not last_hsv:
                    last_hsv = cv2.split(cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2HSV))

                delta_hsv = [0, 0, 0, 0]
                for i in range(3):
                    num_pixels = curr_hsv[i].shape[0] * curr_hsv[i].shape[1]
                    curr_hsv[i] = curr_hsv[i].astype(numpy.int32)
                    last_hsv[i] = last_hsv[i].astype(numpy.int32)
                    delta_hsv[i] = numpy.sum(numpy.abs(curr_hsv[i] - last_hsv[i])) / float(num_pixels)
                delta_hsv[3] = sum(delta_hsv[0:3]) / 3.0
                delta_h, delta_s, delta_v, delta_hsv_avg = delta_hsv

                if stats_manager is not None:
                    stats_manager.set_metrics(frame_num, {
                        metric_keys[0]: delta_hsv_avg, metric_keys[1]: delta_h,
                        metric_keys[2]: delta_s, metric_keys[3]: delta_v })

                self.last_hsv = curr_hsv

            if delta_hsv_avg >= self.threshold:
                if self.last_scene_cut is None or (
                  (frame_num - self.last_scene_cut) >= self.min_scene_len):
                    #scene_manager.add_cut(frame_num)   # Returning True will do the same now.
                    cut_detected = True
                    cut_frame = frame_num
                    self.last_scene_cut = frame_num

            #self.last_frame.release()
            del self.last_frame
                
        self.last_frame = frame_img.copy()
        return cut_detected, cut_frame

    def post_process(self, scene_list, frame_num):
        """Not used for ContentDetector, as cuts are written as they are found."""
        return
