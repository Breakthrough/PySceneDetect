#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""":class:`KoalaDetector` uses the detection method described by Koala-36M.
See https://koala36m.github.io/ for details.

TODO: Cite correctly.

This detector requires the optional `scikit-image` package to be installed.

This detector is available from the command-line as the `detect-koala` command.
"""

import cv2
import numpy as np

from scenedetect.common import FrameTimecode, TimecodeLike
from scenedetect.detector import SceneDetector

try:
    from skimage.metrics import structural_similarity
except ImportError:  # pragma: no cover
    structural_similarity = None


class KoalaDetector(SceneDetector):
    """Detects cuts by scoring adjacent frames using per-channel histogram correlation combined
    with the structural similarity of their edge maps, similar to the method described by
    Koala-36M. Cuts are found using an adaptive threshold calculated over a window of preceding
    scores, so all cuts are emitted from :meth:`post_process` once the whole video has been
    processed."""

    def __init__(self, min_scene_len: TimecodeLike = 15):
        """
        Arguments:
            min_scene_len: Accepted for consistency with other detectors, but not currently used
                by this detector (TODO).
        """
        if structural_similarity is None:
            raise ImportError(
                "KoalaDetector requires the `scikit-image` package (pip install scikit-image)."
            )
        super().__init__()
        self._start_timecode: FrameTimecode | None = None
        self._min_scene_len: TimecodeLike = min_scene_len
        self._last_histogram: np.ndarray | None = None
        self._last_edges: np.ndarray | None = None
        self._scores: list[float] = []

        # Tunables (TODO: Make these config params):

        # Boxcar filter size (should be <= window size)
        self._filter_size: int = 3
        # Window to use for calculating threshold (should be >= filter size).
        self._window_size: int = 8
        # Multiplier for standard deviations when calculating threshold.
        self._deviation: float = 3.0

    def process_frame(self, timecode: FrameTimecode, frame_img: np.ndarray) -> list[FrameTimecode]:
        assert structural_similarity is not None
        # TODO: frame_img is already downscaled here. The same problem exists in HashDetector.
        # For now we can just set downscale factor to 1 in SceneManager to work around the issue.
        frame_img = cv2.resize(frame_img, (256, 256))
        histogram = np.asarray(
            [cv2.calcHist([c], [0], None, [254], [1, 255]) for c in cv2.split(frame_img)]
        )
        # TODO: Make the parameters below tunable.
        frame_gray = cv2.resize(cv2.cvtColor(frame_img, cv2.COLOR_BGR2GRAY), (128, 128))
        edges = np.maximum(frame_gray, cv2.Canny(frame_gray, 100, 200))
        if self._start_timecode is None:
            self._start_timecode = timecode
        else:
            delta_histogram = cv2.compareHist(self._last_histogram, histogram, cv2.HISTCMP_CORREL)
            delta_edges = structural_similarity(self._last_edges, edges, data_range=255)
            score = 4.61480465 * delta_histogram + 3.75211168 * delta_edges - 5.485968377115124
            self._scores.append(score)
        self._last_histogram = histogram
        self._last_edges = edges
        return []

    def post_process(self, timecode: FrameTimecode) -> list[FrameTimecode]:
        if self._start_timecode is None or not self._scores:
            return []
        cut_found = [score < 0.0 for score in self._scores]
        cut_found.append(True)
        boxcar = [1] * self._filter_size
        cutoff = float(self._filter_size) / float(self._filter_size + 1)
        filtered = np.convolve(self._scores, boxcar, mode="same")
        for i in range(len(self._scores)):
            if i >= self._window_size and filtered[i] < cutoff:
                # TODO: Should we discard the N most extreme values before calculating threshold?
                window = filtered[i - self._window_size : i]
                threshold = window.mean() - (self._deviation * window.std())
                if filtered[i] < threshold:
                    cut_found[i] = True

        cuts = []
        last_cut = 0
        for i in range(len(cut_found)):
            if cut_found[i]:
                if (i - last_cut) > self._window_size:
                    cuts.append(last_cut)
                last_cut = i + 1
        return [self._start_timecode + cut for cut in cuts][1:]
