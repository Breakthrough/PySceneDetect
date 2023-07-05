# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2023 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""":class:`SceneLoader` is a class designed for use cases in which a list of
scenes is read from a csv file and actual detection of scene boundaries does not
need to occur.

This is available from the command-line as the `load-scenes` command.
"""

import os
import csv

from typing import List

import numpy

from scenedetect.scene_detector import SceneDetector
from scenedetect.frame_timecode import FrameTimecode


class SceneLoader(SceneDetector):
    """Detector which load a list of predefined cuts from a CSV file. Used by the CLI to implement
    the `load-scenes` functionality. Incompatible with other detectors.
    """

    def __init__(self, file=None, cut_col_name="Start Frame", framerate=None):
        """
        Arguments:
            file:   Path to csv file containing scene data for video
            cut_col_name:  Header for the column containing the frame or timecode where new scenes
                should start.
            framerate:  Framerate for the input video, used for handling timecode to frame number
                conversions. Only used if timecodes are used as input for cut points.
        """
        super().__init__()
        self.framerate = framerate

        # Check to make specified csv file exists
        if not file:
            raise ValueError('file path to csv file must be specified')
        if not os.path.exists(file):
            raise ValueError('specified csv file does not exist')

        self.csv_file = file

        # Open csv and check and read first row for column headers
        (self.file_reader, csv_headers) = self._open_csv(self.csv_file, cut_col_name)

        # Check to make sure column headers are present
        if cut_col_name not in csv_headers:
            raise ValueError('specified column header for scene start is not present')

        self._col_idx = csv_headers.index(cut_col_name)
        self._last_scene_row = None
        self._scene_start = None

        self._get_next_scene(self.file_reader, self.framerate)
        # PySceneDetect works on cuts, so we have to skip the first scene and use the first frame
        # of the next scene as the cut point.
        self._get_next_scene(self.file_reader, self.framerate)

    def _open_csv(self, csv_file, cut_col_name):
        """Opens the specified csv file for reading.

        Arguments:
            csv_file:       Path to csv file containing scene data for video

        Returns:
            (reader, headers):    csv.reader object and headers
        """
        input_file = open(csv_file, 'r')
        file_reader = csv.reader(input_file)
        csv_headers = next(file_reader)
        if not cut_col_name in csv_headers:
            csv_headers = next(file_reader)
        return (file_reader, csv_headers)

    def _get_next_scene(self, file_reader, framerate=None):
        """Reads the next scene information from the input csv file.

        Arguments:
            file_reader:    The csv.reader object for the detector
            framerate:      If timecodes are used as an input, a framerate is required for
                timecode <-> frame number conversions
        """
        try:
            self._last_scene_row = next(file_reader)
        except StopIteration:
            # We have reached the end of the csv file, do not modify scene list
            pass

        if framerate:
            self._scene_start = FrameTimecode(
                self._last_scene_row[self._col_idx], fps=self.framerate).frame_num
        else:
            self._scene_start = int(self._last_scene_row[self._col_idx]) - 1

    def process_frame(self, frame_num: int, frame_img: numpy.ndarray) -> List[int]:
        """Simply reads cut data from a given csv file. Video is not analyzed. Therefore this
        detector is incompatible with other detectors or a StatsManager.

        Arguments:
            frame_num:  Frame number of frame that is being passed.
            frame_img:  Decoded frame image (numpy.ndarray) to perform scene detection on. This is
                unused for this detector as the video is not analyzed, but is allowed for
                compatiblity.

        Returns:
            cut_list:   List of cuts (as provided by input csv file)
        """
        cut_list = []

        # If frame_num is earlier than the first input scene, just return empty cut
        if frame_num < self._scene_start:
            return cut_list

        # If frame_num is at the beginning of the input scene, mark a cut and get next scene info
        if frame_num == self._scene_start:
            # We have hit a cut point, add it to the cut_list and get the next scene
            cut_list.append(frame_num)
            self._get_next_scene(self.file_reader, self.framerate)

        return cut_list

    def is_processing_required(self, frame_num):
        return True
