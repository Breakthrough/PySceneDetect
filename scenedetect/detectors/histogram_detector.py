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
""":py:class:`HistogramDetector` compares the difference in the RGB histograms of subsequent
frames. If the difference exceeds a given threshold, a cut is detected.

This detector is available from the command-line as the `detect-hist` command.
"""

from typing import List

import cv2
import numpy

# PySceneDetect Library Imports
from scenedetect.scene_detector import SceneDetector


class HistogramDetector(SceneDetector):
    """Compares the difference in the RGB histograms of subsequent
    frames. If the difference exceeds a given threshold, a cut is detected."""

    METRIC_KEYS = ['hist_diff']

    def __init__(self, threshold: float = 0.95, bins: int = 256, min_scene_len: int = 15):
        """
        Arguments:
            threshold: Threshold value (float) that the calculated difference between subsequent
                        histograms must exceed to trigger a new scene.
                        The threshold value should be between 0 and 1 (perfect positive correlation, identical histograms).
                        Values close to 1 indicate very similar frames, while lower values suggest changes.
            bins: Number of bins to use for the histogram.
            min_scene_len:  Minimum length of any scene.
        """
        super().__init__()
        self._threshold = threshold
        self._bins = bins
        self._min_scene_len = min_scene_len
        self._last_hist = None
        self._last_scene_cut = None

    def process_frame(self, frame_num: int, frame_img: numpy.ndarray) -> List[int]:
        """Computes the histogram of the luma channel of the frame image and compares it with the
        histogram of the luma channel of the previous frame. If the difference between the histograms
        exceeds the threshold, a scene cut is detected.
        Histogram difference is computed using the correlation metric.

        Arguments:
            frame_num: Frame number of frame that is being passed.
            frame_img: Decoded frame image (numpy.ndarray) to perform scene
                detection on.

        Returns:
            List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.
        """
        cut_list = []

        np_data_type = frame_img.dtype

        if np_data_type != numpy.uint8:
            raise ValueError('Image must be 8-bit rgb for HistogramDetector')

        if frame_img.shape[2] != 3:
            raise ValueError('Image must have three color channels for HistogramDetector')

        # Initialize last scene cut point at the beginning of the frames of interest.
        if not self._last_scene_cut:
            self._last_scene_cut = frame_num

        hist = self.calculate_histogram(frame_img, bins = self._bins)

        # We can only start detecting once we have a frame to compare with.
        if self._last_hist is not None:
            #TODO: We can have EMA of histograms to make it more robust
            # ema_hist = alpha * hist + (1 - alpha) * ema_hist

            # Compute histogram difference between frames
            hist_diff = cv2.compareHist(self._last_hist, hist, cv2.HISTCMP_CORREL)

            # Check if a new scene should be triggered
            # Set a correlation threshold to determine scene changes.
            # The threshold value should be between -1 (perfect negative correlation, not applicable here)
            # and 1 (perfect positive correlation, identical histograms).
            # Values close to 1 indicate very similar frames, while lower values suggest changes.
            # Example: If `_threshold` is set to 0.8, it implies that only changes resulting in a correlation
            # less than 0.8 between histograms will be considered significant enough to denote a scene change.
            if hist_diff <= self._threshold and ((frame_num - self._last_scene_cut)
                                                 >= self._min_scene_len):
                cut_list.append(frame_num)
                self._last_scene_cut = frame_num

            # Save stats to a StatsManager if it is being used
            if self.stats_manager is not None:
                self.stats_manager.set_metrics(frame_num, {self.METRIC_KEYS[0]: hist_diff})

        self._last_hist = hist

        return cut_list

    def calculate_histogram(self,
                            frame_img: numpy.ndarray,
                            bins: int = 256,
                            normalize: bool = True) -> numpy.ndarray:
        """
        Calculates and optionally normalizes the histogram of the luma (Y) channel of an image converted from BGR to YUV color space.
        
        This function extracts the Y channel from the given BGR image, computes its histogram with the specified number of bins, 
        and optionally normalizes this histogram to have a sum of one across all bins.

        Args:
        -----
        frame_img : np.ndarray
            The input image in BGR color space, assumed to have shape (height, width, 3) 
            where the last dimension represents the BGR channels.
        bins : int, optional (default=256)
            The number of bins to use for the histogram.
        normalize : bool, optional (default=True)
            A boolean flag that determines whether the histogram should be normalized 
            such that the sum of all histogram bins equals 1.

        Returns:
        --------
        np.ndarray
            A 1D numpy array of length equal to `bins`, representing the histogram of the luma channel. 
            Each element in the array represents the count (or frequency) of a particular luma value in the image. 
            If normalized, these values represent the relative frequency.

        Examples:
        ---------
        >>> img = cv2.imread('path_to_image.jpg')
        >>> hist = calculate_histogram(img, bins=256, normalize=True)
        >>> print(hist.shape)
        (256,)
        """
        # Extract Luma channel from the frame image
        y, _, _ = cv2.split(cv2.cvtColor(frame_img, cv2.COLOR_BGR2YUV))

        # Create the histogram with a bin for every rgb value
        hist = cv2.calcHist([y], [0], None, [bins], [0, 256])

        if normalize:
            # Normalize the histogram
            hist = cv2.normalize(hist, hist).flatten()

        return hist

    def is_processing_required(self, frame_num: int) -> bool:
        return True

    def get_metrics(self) -> List[str]:
        return HistogramDetector.METRIC_KEYS
