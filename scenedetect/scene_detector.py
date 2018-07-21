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

""" PySceneDetect scenedetect.scene_detector Module

This module implements the base SceneDetector class, from which all scene
detectors in the scenedetect.dectectors module are derived from.

The SceneDetector class represents the interface which detection algorithms
are expected to provide in order to be compatible with PySceneDetect.
"""

# Third-Party Library Imports
import cv2
import numpy


class SceneDetector(object):
    """Base SceneDetector class to implement a scene detection algorithm."""
    def __init__(self):
        self.stats_manager = None
        self._metric_keys = []
        self.cli_name = 'detect-none'

    def get_metrics(self):
        # type: () -> List[str]
        """ Get Metrics:  Get a list of all metric names/keys used by the detector.
        
        Returns:
            A List[str] of the frame metric key names that will be used by
            the detector when a StatsManager is passed to process_frame.
        """
        return self._metric_keys

    def process_frame(self, frame_num, frame_img):
        # type: (int, numpy.ndarray) -> Tuple[bool, Union[None, List[int]]
        """ Process Frame: Computes/stores metrics and detects any scene changes.

        Prototype method, no actual detection.

        Returns:
            Tuple of (cut_detected: bool, List[frame_nums]: List[int]/None), where if
            cut_detected is True, frame_nums is the list of integer frame numbers of
            the cut(s) to add, else None. 
        """
        return (False, 0)

    def post_process(self, frame_num):
        # type: (int) -> List[int]
        """ Post Process: Performs any processing after the last frame has been read.

        Prototype method, no actual detection.

        Returns:
            List of frame numbers of additional cuts to be added.
        """
        return []

