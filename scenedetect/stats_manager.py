#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""``scenedetect.stats_manager`` Module

This module contains the :class:`StatsManager` class, which provides a key-value store for each
:class:`SceneDetector <scenedetect.detector.SceneDetector>` to write the metrics calculated
for each frame. The :class:`StatsManager` must be registered to a
:class:`SceneManager <scenedetect.scene_manager.SceneManager>` upon construction.

The entire :class:`StatsManager` can be :meth:`saved to <StatsManager.save_to_csv>` a
human-readable CSV file, allowing for precise determination of the ideal threshold (or other
detection parameters) for the given input.
"""

import csv
import os.path
import typing as ty
from logging import getLogger
from pathlib import Path

from scenedetect.common import FrameTimecode

logger = getLogger("pyscenedetect")

##
## StatsManager CSV File Column Names (Header Row)
##

COLUMN_NAME_FRAME_NUMBER = "Frame Number"
"""Name of column containing frame numbers in the statsfile CSV."""

COLUMN_NAME_TIMECODE = "Timecode"
"""Name of column containing timecodes in the statsfile CSV."""

##
## StatsManager Exceptions
##


class FrameMetricRegistered(Exception):
    """[DEPRECATED - DO NOT USE] No longer used.

    :meta private:
    """

    pass


class FrameMetricNotRegistered(Exception):
    """[DEPRECATED - DO NOT USE] No longer used.

    :meta private:
    """

    pass


class StatsFileCorrupt(Exception):
    """Raised when frame metrics/stats could not be loaded from a provided CSV file."""

    def __init__(
        self, message: str = "Could not load frame metric data data from passed CSV file."
    ):
        super().__init__(message)


##
## StatsManager Class Implementation
##


# TODO(v1.0): Relax restriction on metric types only being float or int when loading from disk
# is fully deprecated.
class StatsManager:
    """Provides a key-value store for frame metrics/calculations which can be used
    for two-pass detection algorithms, as well as saving stats to a CSV file.

    Analyzing a statistics CSV file is also very useful for finding the optimal
    algorithm parameters for certain detection methods. Additionally, the data
    may be plotted by a graphing module (e.g. matplotlib) by obtaining the
    metric of interest for a series of frames by iteratively calling get_metrics(),
    after having called the detect_scenes(...) method on the SceneManager object
    which owns the given StatsManager instance.

    Only metrics consisting of `float` or `int` should be used currently.
    """

    def __init__(self, base_timecode: FrameTimecode = None):
        """Initialize a new StatsManager.

        Arguments:
            base_timecode: Timecode associated with this object. Must not be None (default value
                will be removed in a future release).
        """
        # Frame metrics is a dict of frame (int): metric_dict (Dict[str, float])
        # of each frame metric key and the value it represents (usually float).
        self._frame_metrics: ty.Dict[FrameTimecode, ty.Dict[str, float]] = dict()
        self._metric_keys: ty.Set[str] = set()
        self._metrics_updated: bool = False  # Flag indicating if metrics require saving.
        self._base_timecode: ty.Optional[FrameTimecode] = (
            base_timecode  # Used for timing calculations.
        )

    @property
    def metric_keys(self) -> ty.Iterable[str]:
        return self._metric_keys

    def register_metrics(self, metric_keys: ty.Iterable[str]) -> None:
        """Register a list of metric keys that will be used by the detector."""
        self._metric_keys = self._metric_keys.union(set(metric_keys))

    # TODO(#507): This interface is difficult to use, we should support the dictionary protocol.
    # Ideally this should work with Panadas. This could be done with the v0.7 API change.
    def get_metrics(
        self, timecode: FrameTimecode, metric_keys: ty.Iterable[str]
    ) -> ty.List[ty.Any]:
        """Return the requested statistics/metrics for a given timecode.

        Returns:
            A list containing the requested frame metrics for the given frame number, ordered as
            they are in `metric_keys`.
        """
        return [self._get_metric(timecode, metric_key) for metric_key in metric_keys]

    def set_metrics(self, timecode: FrameTimecode, metric_kv_dict: ty.Dict[str, ty.Any]) -> None:
        """Set Metrics: Sets the provided statistics/metrics for a given frame.

        Arguments:
            timecode: Timecode to set metrics for.
            metric_kv_dict: Key value mapping of metrics to their values for `timecode`.
        """
        for metric_key in metric_kv_dict:
            self._set_metric(timecode, metric_key, metric_kv_dict[metric_key])

    def metrics_exist(self, timecode: FrameTimecode, metric_keys: ty.Iterable[str]) -> bool:
        """Metrics Exist: Checks if the given metrics/stats exist for the given frame.

        Returns:
            bool: True if the given metric keys exist for the frame, False otherwise.
        """
        return all([self._metric_exists(timecode, metric_key) for metric_key in metric_keys])

    def is_save_required(self) -> bool:
        """Is Save Required: Checks if the stats have been updated since loading.

        Returns:
            bool: True if there are frame metrics/statistics not yet written to disk,
            False otherwise.
        """
        return self._metrics_updated

    def save_to_csv(
        self,
        csv_file: ty.Union[str, bytes, Path, ty.TextIO],
        force_save=True,
    ) -> None:
        """Save To CSV: Saves all frame metrics stored in the StatsManager to a CSV file.

        Arguments:
            csv_file: A file handle opened in write mode (e.g. open('...', 'w')) or a path as str.
            force_save: If True, writes metrics out even if an update is not required.

        Raises:
            OSError: If `path` cannot be opened or a write failure occurs.
        """
        if not (force_save or self.is_save_required()):
            logger.info("No metrics to write.")
            return

        # If we get a path instead of an open file handle, recursively call ourselves
        # again but with file handle instead of path.
        if isinstance(csv_file, (str, bytes, Path)):
            with open(csv_file, "w") as file:
                self.save_to_csv(csv_file=file, force_save=force_save)
                return

        csv_writer = csv.writer(csv_file, lineterminator="\n")
        metric_keys = sorted(list(self._metric_keys))
        csv_writer.writerow([COLUMN_NAME_FRAME_NUMBER, COLUMN_NAME_TIMECODE] + metric_keys)
        frame_keys = sorted(self._frame_metrics.keys())
        logger.info("Writing %d frames to CSV...", len(frame_keys))
        for frame_key in frame_keys:
            csv_writer.writerow(
                [frame_key.frame_num + 1, frame_key.get_timecode()]
                + [str(metric) for metric in self.get_metrics(frame_key, metric_keys)]
            )

    @staticmethod
    def valid_header(row: ty.List[str]) -> bool:
        """Check that the given CSV row is a valid header for a statsfile.

        Arguments:
            row: A row decoded from the CSV reader.

        Returns:
            True if `row` is a valid statsfile header, False otherwise.
        """
        if not row or not len(row) >= 2:
            return False
        if row[0] != COLUMN_NAME_FRAME_NUMBER or row[1] != COLUMN_NAME_TIMECODE:
            return False
        return True

    # TODO(v1.0): Create a replacement for a calculation cache that functions like load_from_csv
    # did, but is better integrated with detectors for cached calculations instead of statistics.
    def load_from_csv(self, csv_file: ty.Union[str, bytes, ty.TextIO]) -> ty.Optional[int]:
        """[DEPRECATED] DO NOT USE

        Load all metrics stored in a CSV file into the StatsManager instance. Will be removed in a
        future release after becoming a no-op.

        Arguments:
            csv_file: A file handle opened in read mode (e.g. open('...', 'r')) or a path as str.

        Returns:
            int or None: Number of frames/rows read from the CSV file, or None if the
            input file was blank or could not be found.

        Raises:
            StatsFileCorrupt: Stats file is corrupt and can't be loaded, or wrong file
                was specified.

        :meta private:
        """
        # TODO: Make this an error, then make load_from_csv() a no-op, and finally, remove it.
        logger.warning("load_from_csv() is deprecated and will be removed in a future release.")

        # If we get a path instead of an open file handle, check that it exists, and if so,
        # recursively call ourselves again but with file set instead of path.
        if isinstance(csv_file, (str, bytes, Path)):
            if os.path.exists(csv_file):
                with open(csv_file) as file:
                    return self.load_from_csv(csv_file=file)
            # Path doesn't exist.
            return None

        # If we get here, file is a valid file handle in read-only text mode.
        csv_reader = csv.reader(csv_file, lineterminator="\n")
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
            raise StatsFileCorrupt("No metrics defined in CSV file.")
        loaded_metrics = list(row[2:])
        num_frames = 0
        for row in csv_reader:
            metric_dict = {}
            if not len(row) == num_cols:
                raise StatsFileCorrupt("Wrong number of columns detected in stats file row.")
            frame_number = int(row[0])
            # Switch from 1-based to 0-based frame numbers.
            if frame_number > 0:
                frame_number -= 1
            self.set_metrics(frame_number, metric_dict)
            for i, metric in enumerate(row[2:]):
                if metric and metric != "None":
                    try:
                        self._set_metric(frame_number, loaded_metrics[i], float(metric))
                    except ValueError:
                        raise StatsFileCorrupt(
                            "Corrupted value in stats file: %s" % metric
                        ) from ValueError
            num_frames += 1
        self._metric_keys = self._metric_keys.union(set(loaded_metrics))
        logger.info("Loaded %d metrics for %d frames.", num_metrics, num_frames)
        self._metrics_updated = False
        return num_frames

    # TODO: Get rid of these functions and simplify the implementation of this class.

    def _get_metric(self, timecode: FrameTimecode, metric_key: str) -> ty.Optional[ty.Any]:
        if self._metric_exists(timecode, metric_key):
            return self._frame_metrics[timecode][metric_key]
        return None

    def _set_metric(self, timecode: FrameTimecode, metric_key: str, metric_value: ty.Any) -> None:
        self._metrics_updated = True
        if timecode not in self._frame_metrics:
            self._frame_metrics[timecode] = dict()
        self._frame_metrics[timecode][metric_key] = metric_value

    def _metric_exists(self, timecode: FrameTimecode, metric_key: str) -> bool:
        return timecode in self._frame_metrics and metric_key in self._frame_metrics[timecode]
