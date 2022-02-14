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
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/PySceneDetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
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

""" ``scenedetect.stats_manager`` Module

This module contains the :py:class:`StatsManager` class, which provides a key-value store
for each :py:class:`SceneDetector <scenedetect.scene_detector.SceneDetector>` to read/write
the metrics calculated for each frame. The :py:class:`StatsManager` must be registered to a
:py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` by passing it to the
:py:class:`SceneManager constructor <scenedetect.scene_manager.SceneManager>` as the
`stats_manager` argument.

The entire :py:class:`StatsManager` can be :py:meth:`saved to <StatsManager.save_to_csv>`
and :py:meth:`loaded from <StatsManager.load_from_csv>` a human-readable CSV
file, also allowing both precise determination of the threshold or other optimal values
for video files.  See the :py:meth:`save_to_csv() <StatsManager.save_to_csv>` and
:py:meth:`load_from_csv() <StatsManager.load_from_csv>` methods for more information.

The :py:class:`StatsManager` can also be used to cache the calculation results of the scene
detectors being used, speeding up subsequent scene detection runs using the same pair of
:py:class:`SceneManager<scenedetect.scene_manager.SceneManager>`/:py:class:`StatsManager` objects.
"""

from logging import getLogger
from typing import List, TextIO
import os.path

from scenedetect.frame_timecode import FrameTimecode
from scenedetect.platform import get_csv_reader, get_csv_writer


logger = getLogger('pyscenedetect')


##
## StatsManager CSV File Column Names (Header Row)
##

COLUMN_NAME_FRAME_NUMBER = "Frame Number"
COLUMN_NAME_TIMECODE = "Timecode"


##
## StatsManager Exceptions
##

class FrameMetricRegistered(Exception):
    """ Raised when attempting to register a frame metric key which has
    already been registered. """
    def __init__(self, metric_key: str, message: str="Attempted to re-register frame metric key."):
        # Pass message string to base Exception class.
        super().__init__(message)
        self.metric_key = metric_key


class FrameMetricNotRegistered(Exception):
    """ Raised when attempting to call get_metrics(...)/set_metrics(...) with a
    frame metric that does not exist, or has not been registered. """
    def __init__(self, metric_key: str,
                 message: str="Attempted to get/set frame metrics for unregistered metric key."):
        # Pass message string to base Exception class.
        super().__init__(message)
        self.metric_key = metric_key


class StatsFileCorrupt(Exception):
    """ Raised when frame metrics/stats could not be loaded from a provided CSV file. """
    def __init__(self, message: str="Could not load frame metric data data from passed CSV file."):
        # Pass message string to base Exception class.
        super().__init__(message)


##
## StatsManager Class Implementation
##

class StatsManager:
    """ Provides a key-value store for frame metrics/calculations which can be used
    as a cache to speed up subsequent calls to a SceneManager's detect_scenes(...)
    method. The statistics can be saved to a CSV file, and loaded from disk.

    Analyzing a statistics CSV file is also very useful for finding the optimal
    algorithm parameters for certain detection methods. Additionally, the data
    may be plotted by a graphing module (e.g. matplotlib) by obtaining the
    metric of interest for a series of frames by iteratively calling get_metrics(),
    after having called the detect_scenes(...) method on the SceneManager object
    which owns the given StatsManager instance.
    """

    def __init__(self):
        # Frame metrics is a dict of frame (int): metric_dict (Dict[str, float])
        # of each frame metric key and the value it represents (usually float).
        self._frame_metrics = dict()        # Dict[FrameTimecode, Dict[str, float]]
        self._registered_metrics = set()    # Set of frame metric keys.
        self._loaded_metrics = set()        # Metric keys loaded from stats file.
        self._metrics_updated = False       # Flag indicating if metrics require saving.


    def register_metrics(self, metric_keys):
        # type: (List[str]) -> bool
        """ Register Metrics

        Register a list of metric keys that will be used by the detector.
        Used to ensure that multiple detector keys don't overlap.

        Raises:
            FrameMetricRegistered: A particular metric_key has already been registered/added
                to the StatsManager. Only if the StatsManager is being used for read-only
                access (i.e. all frames in the video have already been processed for the given
                metric_key in the exception) is this behavior desirable.
        """
        for metric_key in metric_keys:
            if metric_key not in self._registered_metrics:
                self._registered_metrics.add(metric_key)
            else:
                raise FrameMetricRegistered(metric_key)

    # TODO(v1.0): Change frame_number to a FrameTimecode now that it is just a hash and will
    # be required for VFR support.
    def get_metrics(self, frame_number, metric_keys):
        # type: (int, List[str]) -> List[Union[None, int, float, str]]
        """ Get Metrics: Returns the requested statistics/metrics for a given frame.

        Arguments:
            frame_number (int): Frame number to retrieve metrics for.
            metric_keys (List[str]): A list of metric keys to look up.

        Returns:
            A list containing the requested frame metrics for the given frame number
            in the same order as the input list of metric keys. If a metric could
            not be found, None is returned for that particular metric.
        """
        return [self._get_metric(frame_number, metric_key) for metric_key in metric_keys]


    def set_metrics(self, frame_number, metric_kv_dict):
        # type: (int, Dict[str, Union[None, int, float, str]]) -> None
        """ Set Metrics: Sets the provided statistics/metrics for a given frame.

        Arguments:
            frame_number (int): Frame number to retrieve metrics for.
            metric_kv_dict (Dict[str, metric]): A dict mapping metric keys to the
                respective integer/floating-point metric values to set.
        """
        for metric_key in metric_kv_dict:
            self._set_metric(frame_number, metric_key, metric_kv_dict[metric_key])


    def metrics_exist(self, frame_number, metric_keys):
        # type: (int, List[str]) -> bool
        """ Metrics Exist: Checks if the given metrics/stats exist for the given frame.

        Returns:
            bool: True if the given metric keys exist for the frame, False otherwise.
        """
        return all([self._metric_exists(frame_number, metric_key) for metric_key in metric_keys])


    def is_save_required(self):
        # type: () -> bool
        """ Is Save Required: Checks if the stats have been updated since loading.

        Returns:
            bool: True if there are frame metrics/statistics not yet written to disk,
            False otherwise.
        """
        return self._metrics_updated

    # TODO(v1.0): Remove csv_file, add path=None, file=None.
    def save_to_csv(self, path: str=None, file: TextIO=None, base_timecode: FrameTimecode=None, force_save=True):
        # type: (str, File [w], FrameTimecode, bool) -> None
        """ Save To CSV: Saves all frame metrics stored in the StatsManager to a CSV file.

        Arguments:
            csv_file: A file handle opened in write mode (e.g. open('...', 'w')).
            base_timecode: The base_timecode obtained from the frame source VideoStream.
                If using an OpenCV VideoCapture, create one using the video framerate by
                setting base_timecode=FrameTimecode(0, fps=video_framerate).

                TODO(v1.0): Remove this by having StatsManager lazy-init it's own StatsManager
                by accepting a path to a statsfile for the SceneManager (especially since it should
                own one instead of taking one as an argument upon construction).

            force_save: If True, forcably writes metrics out even if one is not required
                (see `is_save_required`).

        Raises:
            IOError: If fail to open file for writing.
        """
        if path is not None and file is not None:
            raise ValueError("Only one of path or file can be specified")

        # Ensure we need to write to the file, and that we have data to do so with.
        if not ((self.is_save_required() or force_save) and
                self._registered_metrics and self._frame_metrics):
            logger.info("No metrics to save.")
            return

        # If we get a path instead of an open file handle, recursively call ourselves
        # again but with file handle instead of path.
        if path is not None:
            with open(path, 'w') as file:
                return self.save_to_csv(
                    file=file, base_timecode=base_timecode, force_save=force_save)
        csv_writer = get_csv_writer(file)

        # Header rows.
        metric_keys = sorted(list(self._registered_metrics.union(self._loaded_metrics)))
        csv_writer.writerow(
            [COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE] + metric_keys)
        frame_keys = sorted(self._frame_metrics.keys())
        logger.info("Writing %d frames to CSV...", len(frame_keys))
        for frame_key in frame_keys:
            frame_timecode = base_timecode + frame_key
            csv_writer.writerow(
                [frame_timecode.get_frames(), frame_timecode.get_timecode()] +
                [str(metric) for metric in self.get_metrics(frame_key, metric_keys)])


    @staticmethod
    def valid_header(row: List[str]):
        # type: (List[str]) -> bool
        """ Validates if the given CSV row is a valid header for a statsfile.

        Arguments:
            row: A row decoded from the CSV reader.

        Returns:
            True if a valid statsfile header, False otherwise.
        """
        if not row or not len(row) >= 2:
            return False
        if row[0] != COLUMN_NAME_FRAME_NUMBER or row[1] != COLUMN_NAME_TIMECODE:
            return False
        return True

    def load_from_csv(self, path: str=None, file: TextIO=None):
        """ Load From CSV: Loads all metrics stored in a CSV file into the StatsManager instance.

        Arguments:
            csv_file: A file handle opened in read mode (e.g. open('...', 'r')) or a path as str.

        Returns:
            int or None: Number of frames/rows read from the CSV file, or None if the
            input file was blank or could not be found.

        Raises:
            StatsFileCorrupt: Stats file is corrupt and can't be loaded, or wrong file
                was specified.
        """
        if path is not None and file is not None:
            raise ValueError("Only one of path or file can be specified")
        # If we get a path instead of an open file handle, check that it exists, and if so,
        # recursively call ourselves again but with file set instead of path.
        if path is not None:
            if os.path.exists(path):
                with open(path, 'r') as file:
                    return self.load_from_csv(file=file)
            return
        csv_reader = get_csv_reader(file)
        num_cols = None
        num_metrics = None
        num_frames = None
        # First Row: Frame Num, Timecode, [metrics...]
        try:
            row = next(csv_reader)
            # Backwards compatibility for previous versions of statsfile
            # which included an additional header row.
            if not self.valid_header(row):
                row = next(csv_reader)
        except StopIteration:
            # If the file is blank or we couldn't decode anything, assume the file was empty.
            return None
        if not self.valid_header(row):
            raise StatsFileCorrupt()
        num_cols = len(row)
        num_metrics = num_cols - 2
        if not num_metrics > 0:
            raise StatsFileCorrupt('No metrics defined in CSV file.')
        self._loaded_metrics = row[2:]
        num_frames = 0
        for row in csv_reader:
            metric_dict = {}
            if not len(row) == num_cols:
                raise StatsFileCorrupt('Wrong number of columns detected in stats file row.')
            for i, metric_str in enumerate(row[2:]):
                if metric_str and metric_str != 'None':
                    try:
                        metric_dict[self._loaded_metrics[i]] = float(metric_str)
                    except ValueError:
                        raise StatsFileCorrupt('Corrupted value in stats file: %s' % metric_str) from ValueError
            self.set_metrics(int(row[0]), metric_dict)
            num_frames += 1
        logger.info('Loaded %d metrics for %d frames.', num_metrics, num_frames)
        self._metrics_updated = False
        return num_frames


    def _get_metric(self, frame_number, metric_key):
        # type: (int, str) -> Union[None, int, float, str]
        if self._metric_exists(frame_number, metric_key):
            return self._frame_metrics[frame_number][metric_key]
        return None


    def _set_metric(self, frame_number, metric_key, metric_value):
        # type: (int, str, Union[None, int, float, str]) -> None
        self._metrics_updated = True
        if not frame_number in self._frame_metrics:
            self._frame_metrics[frame_number] = dict()
        self._frame_metrics[frame_number][metric_key] = metric_value


    def _metric_exists(self, frame_number, metric_key):
        # type: (int, List[str]) -> bool
        return (frame_number in self._frame_metrics and
                metric_key in self._frame_metrics[frame_number])
