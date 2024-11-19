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
""":class:`KoalaDetector` uses the detection method described by Koala-36M.
See https://koala36m.github.io/ for details.

TODO: Cite correctly.

This detector is available from the command-line as the `detect-koala` command.
"""

import typing as ty

import cv2
import numpy as np
from skimage.metrics import structural_similarity

from scenedetect.scene_detector import SceneDetector


class KoalaDetector(SceneDetector):
    def __init__(self, min_scene_len: int = None):
        self._start_frame_num: int = None
        self._min_scene_len: int = min_scene_len if min_scene_len else 0
        self._last_histogram: np.ndarray = None
        self._last_edges: np.ndarray = None
        self._scores: ty.List[ty.List[int]] = []

        # Tunables (TODO: Make these config params):

        # Boxcar filter size (should be <= window size)
        self._filter_size: int = 3
        # Window to use for calculating threshold (should be >= filter size).
        self._window_size: int = 8
        # Multiplier for standard deviations when calculating threshold.
        self._deviation: float = 3.0

    def process_frame(self, frame_num: int, frame_img: np.ndarray) -> ty.List[int]:
        # TODO: frame_img is already downscaled here. The same problem exists in HashDetector.
        # For now we can just set downscale factor to 1 in SceneManager to work around the issue.
        frame_img = cv2.resize(frame_img, (256, 256))
        histogram = np.asarray(
            [cv2.calcHist([c], [0], None, [254], [1, 255]) for c in cv2.split(frame_img)]
        )
        # TODO: Make the parameters below tunable.
        frame_gray = cv2.resize(cv2.cvtColor(frame_img, cv2.COLOR_BGR2GRAY), (128, 128))
        edges = np.maximum(frame_gray, cv2.Canny(frame_gray, 100, 200))
        if self._start_frame_num is not None:
            delta_histogram = cv2.compareHist(self._last_histogram, histogram, cv2.HISTCMP_CORREL)
            delta_edges = structural_similarity(self._last_edges, edges, data_range=255)
            score = 4.61480465 * delta_histogram + 3.75211168 * delta_edges - 5.485968377115124
            self._scores.append(score)
        if self._start_frame_num is None:
            self._start_frame_num = frame_num
        self._last_histogram = histogram
        self._last_edges = edges
        return []

    def post_process(self, frame_num: int) -> ty.List[int]:
        cut_found = [score < 0.0 for score in self._scores]
        cut_found.append(True)
        filter = [1] * self._filter_size
        cutoff = float(self._filter_size) / float(self._filter_size + 1)
        filtered = np.convolve(self._scores, filter, mode="same")
        for frame_num in range(len(self._scores)):
            if frame_num >= self._window_size and filtered[frame_num] < cutoff:
                # TODO: Should we discard the N most extreme values before calculating threshold?
                window = filtered[frame_num - self._window_size : frame_num]
                threshold = window.mean() - (self._deviation * window.std())
                if filtered[frame_num] < threshold:
                    cut_found[frame_num] = True

        cuts = []
        last_cut = 0
        for frame_num in range(len(cut_found)):
            if cut_found[frame_num]:
                if (frame_num - last_cut) > self._window_size:
                    cuts.append(last_cut)
                last_cut = frame_num + 1
        return [cut + self._start_frame_num for cut in cuts][1:]
