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
# This software uses the Numpy, OpenCV, click, tqdm, and pytest libraries.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.stats_manager Module

This file contains the StatsManager class, which provides a key-value store for
each SceneDetector to read/write the metrics calculated for each frame.
The StatsManager must be registered to a SceneManager by passing it to the
SceneManager's constructor.

The entire StatsManager can be saved to and loaded from a human-readable CSV file,
also allowing both precise determination of the threshold or other optimal values
for video files.

The StatsManager can also be used to cache the calculation results of the scene
detectors being used, speeding up subsequent scene detection runs using the
same pair of SceneManager/StatsManager objects.
"""

# Standard Library Imports
from __future__ import print_function
import csv
import logging

# PySceneDetect Library Imports
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.frame_timecode import MINIMUM_FRAMES_PER_SECOND_FLOAT
from scenedetect.platform import get_csv_reader
from scenedetect.platform import get_csv_writer


COLUMN_NAME_FPS = "Frame Rate:"
COLUMN_NAME_FRAME_NUMBER = "Frame Number"
COLUMN_NAME_TIMECODE = "Timecode"


class FrameMetricRegistered(Exception):
    def __init__(self, metric_key, message =
                 "Attempted to re-register frame metric key."):
        # type: (str, str)
        # Pass message string to base Exception class.
        super(FrameMetricRegistered, self).__init__(message)
        self.metric_key = metric_key

class FrameMetricNotRegistered(Exception):
    def __init__(self, metric_key, message =
                 "Attempted to get/set frame metrics for unregistered metric key."):
        # type: (str, str)
        # Pass message string to base Exception class.
        super(FrameMetricNotRegistered, self).__init__(message)
        self.metric_key = metric_key

class StatsFileCorrupt(Exception):
    def __init__(self, message =
                 "Could not load frame metric data data from passed CSV file."):
        # type: (str, str)
        # Pass message string to base Exception class.
        super(StatsFileCorrupt, self).__init__(message)

class StatsFileFramerateMismatch(Exception):
    def __init__(self, base_timecode_fps, stats_file_fps, message =
                 "Framerate differs between stats file and base timecode."):
        # type: (str, str)
        # Pass message string to base Exception class.
        super(StatsFileFramerateMismatch, self).__init__(message)
        self.base_timecode_fps = base_timecode_fps
        self.stats_file_fps = stats_file_fps

class NoMetricsRegistered(Exception):
    pass

class NoMetricsSet(Exception):
    pass



class StatsManager(object):

    def __init__(self):
        # type: ()
        # Frame metrics is a dict of frame (int): metric_dict (Dict[str, float])
        # of each frame metric key and the value it represents (usually float).
        self._frame_metrics = dict()        # Dict[FrameTimecode, Dict[str, float]]
        self._registered_metrics = set()    # Set of frame metric keys.
        self._stats_writer = None
        self._metrics_updated = False

    def register_metrics(self, metric_keys):
        # type: (List[str]) -> bool
        """ Register Metrics

        Register a list of metric keys that will be used by the detector.
        Used to ensure that multiple detector keys don't overlap.

        Raises:
            FrameMetricRegistered
        """
        for metric_key in metric_keys:
            if metric_key not in self._registered_metrics:
                self._registered_metrics.add(metric_key)
            else:
                raise FrameMetricRegistered(metric_key)

                
    def get_metrics(self, frame_number, metric_keys):
        # type: (int, List[str]) -> List[Union[None, int, float, str]]
        return [self._get_metric(frame_number, metric_key) for metric_key in metric_keys]

    def set_metrics(self, frame_number, metric_kv_dict):
        # type: (int, Dict[str, Union[None, int, float, str]]) -> None
        for metric_key in metric_kv_dict:
            self._set_metric(frame_number, metric_key, metric_kv_dict[metric_key])

    def metrics_exist(self, frame_number, metric_keys):
        # type: (int, List[str]) -> bool
        return all([self._metric_exists(frame_number, metric_key) for metric_key in metric_keys])
    

    def is_save_required(self):
        return self._metrics_updated

    def _data_can_be_saved(self):
        return self._registered_metrics and self._frame_metrics

    def save_to_csv(self, csv_file, base_timecode, force_save=False):
        # type: (File [w], FrameTimecode, bool) -> None
        csv_writer = get_csv_writer(csv_file)
        if self._data_can_be_saved() and (self.is_save_required() or force_save):
            # Header rows.
            metric_keys = list(self._registered_metrics)
            csv_writer.writerow([COLUMN_NAME_FPS, '%.10f' % base_timecode.get_framerate()])
            csv_writer.writerow(
                [COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE] + metric_keys)
            frame_keys = sorted(self._frame_metrics.keys())
            print("Writing %d frames to CSV..." % len(frame_keys))
            for frame_key in frame_keys:
                frame_timecode = base_timecode + frame_key
                csv_writer.writerow(
                    [frame_timecode.get_frames(), frame_timecode.get_timecode()] + 
                    [str(metric) for metric in self.get_metrics(frame_key, metric_keys)])
        else:
            if not self._registered_metrics:
                raise NoMetricsRegistered()
            if not self._frame_metrics:
                raise NoMetricsSet()
            

    def load_from_csv(self, csv_file, base_timecode = None, reset_save_required=True):
        # type: (File [r], Optional[FrameTimecode]) -> int
        csv_reader = get_csv_reader(csv_file)
        num_cols = None
        num_metrics = None
        num_frames = None
        # First row: Framerate, [video_framerate]
        try:
            row = next(csv_reader)
        except StopIteration:
            # If the file is blank or we couldn't decode anything, assume the file was empty.
            return
        # First Row (FPS = [...]) and ensure framerate equals base_timecode if set.
        if not len(row) == 2 or not row[0] == COLUMN_NAME_FPS:
            raise StatsFileCorrupt()
        stats_file_framerate = float(row[1])
        if stats_file_framerate < MINIMUM_FRAMES_PER_SECOND_FLOAT:
            raise StatsFileCorrupt("Invalid framerate detected in CSV stats file "
                                   "(decoded FPS: %f)." % stats_file_framerate)
        if base_timecode is not None and not base_timecode.equal_framerate(stats_file_framerate):
            raise StatsFileFramerateMismatch(base_timecode.get_framerate(), stats_file_framerate)
        # Second Row: Frame Num, Timecode, [metrics...]
        try:
            row = next(csv_reader)
        except StopIteration:
            raise StatsFileCorrupt("Header row(s) missing.")
        if not row or not len(row) >= 2:
            raise StatsFileCorrupt()
        if row[0] != COLUMN_NAME_FRAME_NUMBER or row[1] != COLUMN_NAME_TIMECODE:
            raise StatsFileCorrupt()
        num_cols = len(row)
        num_metrics = num_cols - 2
        if not num_metrics > 0:
            raise StatsFileCorrupt('No metrics defined in CSV file.')
        metric_keys = row[2:]
        num_frames = 0
        for row in csv_reader:
            metric_dict = {}
            for i, metric_str in enumerate(row[2:]):
                metric_dict[metric_keys[i]] = float(metric_str)
            self.set_metrics(int(row[0]), metric_dict)
            num_frames += 1
        logging.info('Loaded %d metrics for %d frames.', num_metrics, num_frames)
        if reset_save_required:
            self._metrics_updated = False
        return num_frames


    def _get_metric(self, frame_number, metric_key):
        # type: (int, str) -> Union[None, int, float, str]
        if self._metric_exists(frame_number, metric_key):
            return self._frame_metrics[frame_number][metric_key]
        return None

    def _set_metric(self, frame_number, metric_key, metric_value):
        self._metrics_updated = True
        # type: (int, str, Union[None, int, float, str]) -> None
        if not frame_number in self._frame_metrics:
            self._frame_metrics[frame_number] = dict()
        self._frame_metrics[frame_number][metric_key] = metric_value

    def _metric_exists(self, frame_number, metric_key):
        # type: (int, List[str]) -> bool
        return (frame_number in self._frame_metrics and
                metric_key in self._frame_metrics[frame_number])


