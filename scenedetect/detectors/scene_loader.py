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
""":py:class:`SceneLoader` is a class designed for use cases in which a list of
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
    """Used for cases in which scenes are read from a csv file. Does not
    actually detect scene boundaries.

    Incompatible with other detectors.
    """

    def __init__(self, csv_file=None, start_col="Start Frame", end_col="End Frame", framerate=None):
        """
        Arguments:
            csv_file:   Path to csv file containing scene data for video
            start_col:  Header for the column containing the frame or timecode for the beginning of
                each scene
            end_col:    Optional header for the column containing the frame or timecode for the end 
                of each scene.
            framerate:  Framerate for the input video, used for handling timecode <-> frame number
                conversions if timecodes are used as input for marking cut points
        """
        super().__init__()
        self.framerate = framerate

        # Check to make specified csv file exists
        if not csv_file:
            raise ValueError('file path to csv file must be specified')
        if not os.path.exists(csv_file):
            raise ValueError('specified csv file does not exist')

        self.csv_file = csv_file

        # Open csv and check and read first row for column headers
        self.file_reader = self._open_csv(self.csv_file)
        csv_headers = next(self.file_reader)

        # Check to make sure column headers are present
        if start_col not in csv_headers:
            raise ValueError('specified column header for scene start is not present')
        if end_col not in csv_headers:
            raise ValueError('specified column header for scene end is not present')

        self.start_col = start_col
        self.start_col_idx = csv_headers.index(start_col)
        self.end_col = end_col
        self.end_col_idx = csv_headers.index(end_col)

        self._last_scene_cut = None
        self._last_scene_row = None
        self._scene_start = None
        self._scene_end = None

    def _open_csv(self, csv_file):
        """Opens the specified csv file for reading.

        Arguments:
            csv_file:       Path to csv file containing scene data for video

        Returns:
            file_reader:    csv.reader object
        """
        input_file = open(csv_file, 'r')
        file_reader = csv.reader(input_file)

        return file_reader

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
                self._last_scene_row[self.start_col_idx], fps=self.framerate).frame_num
            self._scene_end = FrameTimecode(
                self._last_scene_row[self.end_col_idx], fps=self.framerate).frame_num
        else:
            self._scene_start = int(self._last_scene_row[self.start_col_idx]) - 1
            self._scene_end = int(self._last_scene_row[self.end_col_idx]) - 1

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

        # First time through, read first row of input csv and get beginning/end frames
        if not self._last_scene_row:
            self._get_next_scene(self.file_reader, self.framerate)
            # return cut_list

        # If frame_num is earlier than the first input scene, just return empty cut
        if frame_num < self._scene_start:
            return cut_list

        # If frame_num is at the beginning of the input scene, mark a cut and get next scene info
        if frame_num == self._scene_start:
            # To avoid duplication of beginning scene, check if next scene begins at frame 1
            # If so, just ignore this scene and get the next since it is added automatically
            if frame_num == 0:
                self._get_next_scene(self.file_reader, self.framerate)
                return cut_list

            # We have hit a cut point, add it to the cut_list and get the next scene
            cut_list.append(frame_num)
            self._get_next_scene(self.file_reader, self.framerate)

        return cut_list

    def is_processing_required(self, frame_num):
        return True
