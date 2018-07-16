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

""" PySceneDetect scenedetect.scene_manager Module

This module implements the SceneManager object, which is used to coordinate
SceneDetectors and frame sources (e.g. VideoManagers, VideoCaptures), creating
a SceneResult object for each detected scene.

The SceneManager also facilitates passing a StatsManager, if any is defined,
to the associated SceneDetectors for caching of frame metrics.
"""


# Standard Library Imports
from __future__ import print_function

# PySceneDetect Library Imports
from scenedetect.frame_timecode import FrameTimecode



class SceneManager(object):

    def __init__(self, stats_manager=None):
        # type: (Optional[StatsManager])
        self._cutting_list = []
        self._detector_list = []
        self._stats_manager = stats_manager
        self._num_frames = 0
        self._start_frame = 0

    def add_detector(self, detector):
        # type: (SceneDetector) -> None
        detector.stats_manager = self._stats_manager
        self._detector_list.append(detector)
        if self._stats_manager is not None:
            self._stats_manager.register_metrics(detector.get_metrics())


    def clear(self):
        # type: () -> None
        """ Clear All Scenes/Cuts """
        self._cutting_list.clear()
        self._num_frames = 0
        self._start_frame = 0

    def clear_detectors(self):
        # type: () -> None
        self._detector_list.clear()


    def _add_cut(self, frame_num):
        # type: (int) -> None
        # Adds a cut to the cutting list.
        self._cutting_list.append(frame_num)

    def _add_cuts(self, cut_list):
        # type: (List[int]) -> None
        # Adds a list of cuts to the cutting list.
        self._cutting_list += cut_list


    def get_scene_list(self, base_timecode): #, end_time):
        # Scene list, where scenes are tuples of (Start FrameTimecode, End FrameTimecode)
        scene_list = []
        if not self._cutting_list:
            return scene_list
        cut_list = [FrameTimecode(timecode=base_timecode, new_time=cut)
                    for cut in sorted(self._cutting_list)]
        last_cut = base_timecode + self._start_frame
        for cut in cut_list:
            scene_list.append((last_cut, cut - 1))
            last_cut = cut
        #scene_list.append((last_cut, end_time))
        scene_list.append((last_cut, base_timecode + self._num_frames))

        return scene_list


    def _get_cutting_list(self):
        # type: () -> list
        return sorted(self._cutting_list)


    def _process_frame(self, frame_num, frame_im):
        # type(int, numpy.ndarray) -> None
        for detector in self._detector_list:
            cut_found, cut_list = detector.process_frame(frame_num, frame_im)
            if cut_found: self._add_cuts(cut_list)

    def _post_process(self, frame_num):
        # type(int, numpy.ndarray) -> None
        for detector in self._detector_list:
            self._add_cuts(detector.post_process(frame_num))

        
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
                Must be passed if the frame_source has been seeked past frame 0
                (i.e. calling set_duration on a VideoManager or seeking a VideoCapture).
            end_time (int or FrameTimecode): Maximum number of frames to detect
                (set to None to detect all available frames). Only needed for OpenCV
                VideoCapture objects, as VideoManager allows set_duration.
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
        self._start_frame = start_frame

        curr_frame = start_frame

        if isinstance(end_time, FrameTimecode):
            end_frame = end_time.get_frames()
        elif end_time is not None:
            end_frame = int(end_time)

        while True:
            if end_frame is not None and curr_frame >= end_frame:
                break
            ret_val, frame_im = frame_source.read()
            if not ret_val:
                break
            self._process_frame(curr_frame, frame_im)
            curr_frame += 1
            self._num_frames += 1
        
        self._post_process(curr_frame)

        num_frames = curr_frame - start_frame

        print(" ")
        print(" ")
        print(" ")
        print("READ %d FRAMES!" % num_frames)
        print(" ")
        print(" ")
        print(" ")

        return num_frames


