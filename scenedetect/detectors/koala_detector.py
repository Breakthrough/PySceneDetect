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
""":class:`KoalaDetector` detects cuts using the transition scoring method from Koala-36M [1].

Original paper and code: https://github.com/KwaiVGI/Koala-36M

Adjacent frames are scored by a fixed linear model over the correlation of their per-channel
BGR histograms and the structural similarity (SSIM) of their edge maps. A frame is flagged when
its score is below a threshold, or (optionally) when a short moving average of the score falls well
below the trimmed statistics of the preceding window. Consecutive flagged frames form a single
transition, and one cut is emitted at the first frame of it.

This detector is experimental and is available from the command-line as the `detect-koala` command.

[1] Wang, Q., Shi, Y., Ou, J., Chen, R., Lin, K., Wang, J., Jiang, B., Yang, H., Zheng, M.,
    Tao, X., Yang, F., Wan, P., and Zhang, D. (2024). Koala-36M: A Large-scale Video Dataset
    Improving Consistency between Fine-grained Conditions and Video Content.
    arXiv:2410.08260. https://arxiv.org/abs/2410.08260
"""

import collections
import typing as ty

import cv2
import numpy as np

from scenedetect.common import FrameTimecode, TimecodeLike
from scenedetect.detector import SceneDetector

# Linear model weights from the reference implementation (VideoTransitionAnalyzer.py).
_HIST_WEIGHT = 4.61480465
_SSIM_WEIGHT = 3.75211168
_BIAS = -5.485968377115124


# SSIM parameters matching the scikit-image defaults used by the reference implementation.
_SSIM_WINDOW = 7
_SSIM_DATA_RANGE = 255.0


def _ssim(left: np.ndarray, right: np.ndarray) -> float:
    """Mean structural similarity of two 2D 8-bit images of the same size.

    Equivalent to ``skimage.metrics.structural_similarity`` with its defaults (uniform 7x7
    window, K1=0.01, K2=0.03, unbiased sample covariance, border cropped).
    """
    # Inputs are always the 128x128 uint8 edge maps produced by `process_frame`.
    win, data_range = _SSIM_WINDOW, _SSIM_DATA_RANGE

    def window_mean(img: np.ndarray) -> np.ndarray:
        return cv2.boxFilter(img, -1, (win, win), normalize=True, borderType=cv2.BORDER_CONSTANT)

    a, b = left.astype(np.float64), right.astype(np.float64)
    ux, uy = window_mean(a), window_mean(b)
    cov_norm = (win * win) / (win * win - 1.0)  # Sample covariance, as in scikit-image.
    vx = cov_norm * (window_mean(a * a) - ux * ux)
    vy = cov_norm * (window_mean(b * b) - uy * uy)
    vxy = cov_norm * (window_mean(a * b) - ux * uy)
    c1, c2 = (0.01 * data_range) ** 2, (0.03 * data_range) ** 2
    ssim = ((2 * ux * uy + c1) * (2 * vxy + c2)) / ((ux * ux + uy * uy + c1) * (vx + vy + c2))
    pad = (win - 1) // 2
    return float(ssim[pad:-pad, pad:-pad].mean())


class KoalaDetector(SceneDetector):
    """Detects cuts by scoring adjacent frames with the Koala-36M transition model. This detector
    is experimental; its defaults and output may change in future releases.

    Each frame is compared to the previous one by the correlation of their per-channel BGR
    histograms (``koala_hist``, 1.0 = identical) and the structural similarity of their Canny edge
    maps (``koala_ssim``). The frame score is the reference implementation's linear model over
    those two values (``koala_score = 4.6148 * hist + 3.7521 * ssim - 5.4860``). Scores can range
    from about -10.1 to +2.9, and are typically between -4 (very different) and +3 (near
    identical). Frames scoring below `threshold` are flagged as part of a transition, and a run of
    consecutive flagged frames yields a single cut at the first frame of the run, so that the new
    scene begins at the first frame that differs from its predecessor (the same convention as
    :class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`). The
    official code instead starts the next clip after the last frame of the run, which places the
    cut one or more frames later for multi-frame transitions.

    The paper's adaptive rule (flag a frame whose smoothed score drops far below the trimmed mean
    of the preceding window) is available via `adaptive`, but is off by default: on the AutoShot
    benchmark it lowered F1 by roughly 5 points compared to the fixed threshold alone. Enable it
    for results matching the reference implementation. With `adaptive` on, the smoothing
    look-ahead delays each decision by ``(filter_size - 1) // 2`` frames; when a run begins with
    a frame flagged only by the adaptive rule, the cut is placed on the first frame within that
    look-ahead whose raw score is below `threshold`, if any, so that the moving average smearing
    a large drop onto the preceding frame does not move the cut earlier.

    Scores are computed after resizing each frame to 256x256, so they depend on the resolution
    handed to the detector. :class:`SceneManager <scenedetect.scene_manager.SceneManager>`
    downscales frames before detection by default; set ``auto_downscale = False`` and
    ``downscale = 1`` for scores matching the reference implementation (at some cost).

    The method was designed to split videos into clips for dataset curation, and only reacts to
    abrupt frame-to-frame changes: dissolves and other gradual transitions are not detected.
    Frames whose histograms have zero variance (e.g. pure black or white frames) yield a histogram
    correlation of 1.0, so the SSIM term alone decides transitions to/from such frames.
    """

    METRIC_KEYS: ty.ClassVar[list[str]] = ["koala_hist", "koala_ssim", "koala_score"]
    """Statsfile keys recorded per frame: histogram correlation, edge-map SSIM, and the resulting
    frame score. Metrics are written only; detection always recomputes them from frames."""

    def __init__(
        self,
        threshold: float = 0.0,
        min_scene_len: TimecodeLike = 15,
        adaptive: bool = False,
        window_size: int = 8,
        filter_size: int = 3,
        deviation: float = 3.0,
        std_floor: float = 0.2,
        cutoff: float = 0.75,
    ):
        """
        Arguments:
            threshold: A frame is flagged as part of a transition when its score is below this
                value. Scores are typically between -4 and +3; lower values are less sensitive.
            min_scene_len: Once a cut is detected, this much time must pass before a new one can
                be added to the scene list. Accepts an int (frames), float (seconds), or
                str (e.g. ``"0.6s"``, ``"00:00:00.600"``).
            adaptive: Also flag frames whose `filter_size`-frame mean score is below `cutoff` and
                more than `deviation` standard deviations (at least `std_floor`) below the
                trimmed mean of the preceding `window_size` smoothed scores. The first and last
                ``(filter_size - 1) // 2`` frames keep their raw scores, as in the reference
                implementation. Off by default; see the class description.
            window_size: Number of preceding smoothed scores used by the adaptive rule. Must be
                at least 5 so the 20% trim leaves a non-empty window, and at least `filter_size`.
            filter_size: Odd width of the moving average used by the adaptive rule. With
                `adaptive` on, cuts are emitted up to ``(filter_size - 1) // 2`` frames behind
                the current frame.
            deviation: Number of standard deviations below the window mean to flag a frame.
            std_floor: Minimum standard deviation assumed for the window.
            cutoff: Smoothed scores at or above this value are never flagged adaptively.

        Raises:
            ValueError: `filter_size` is not an odd integer >= 1, `window_size` is less than 5,
                or `filter_size` exceeds `window_size`.
        """
        if filter_size < 1 or filter_size % 2 == 0:
            raise ValueError("filter_size must be an odd integer >= 1")
        if window_size < 5:
            raise ValueError("window_size must be at least 5")
        if filter_size > window_size:
            raise ValueError("filter_size must not exceed window_size")
        super().__init__()
        self._threshold = threshold
        self._min_scene_len = min_scene_len
        self._adaptive = adaptive
        self._window_size = window_size
        self._half_filter = (filter_size - 1) // 2
        self._filter_weights = np.full(filter_size, 1.0 / filter_size)
        self._deviation = deviation
        self._std_floor = std_floor
        self._cutoff = cutoff

        self._last_hist: np.ndarray | None = None
        self._last_edges: np.ndarray | None = None
        self._last_cut: FrameTimecode | None = None
        self._num_scores = 0
        # Raw scores around the frame being decided, and scores awaiting a decision (both only
        # used when `adaptive` is set; otherwise every frame is decided as soon as it is scored).
        self._raw: collections.deque[float] = collections.deque(maxlen=filter_size)
        self._pending: collections.deque[tuple[FrameTimecode, float]] = collections.deque()
        # Smoothed scores of already-decided frames (the adaptive rule's window).
        self._smoothed: collections.deque[float] = collections.deque(maxlen=window_size)
        # Whether the previous frame was flagged (i.e. a transition is in progress), and whether
        # that transition's cut is waiting for a raw score below `threshold` within the look-ahead.
        self._in_run = False
        self._cut_deferred = False

    @property
    def event_buffer_length(self) -> int:
        return self._half_filter if self._adaptive else 0

    def get_metrics(self) -> list[str]:
        return list(KoalaDetector.METRIC_KEYS)

    def process_frame(self, timecode: FrameTimecode, frame_img: np.ndarray) -> list[FrameTimecode]:
        if frame_img.dtype != np.uint8:
            raise ValueError("Image must be 8-bit rgb for KoalaDetector")
        if frame_img.ndim != 3 or frame_img.shape[2] != 3:
            raise ValueError("Image must have three color channels for KoalaDetector")
        frame_img = cv2.resize(frame_img, (256, 256))
        hist = np.asarray(
            [cv2.calcHist([c], [0], None, [254], [1, 255]) for c in cv2.split(frame_img)]
        )
        gray = cv2.resize(cv2.cvtColor(frame_img, cv2.COLOR_BGR2GRAY), (128, 128))
        edges = np.maximum(gray, cv2.Canny(gray, 100, 200))
        cuts: list[FrameTimecode] = []
        if self._last_hist is not None and self._last_edges is not None:
            hist_corr = cv2.compareHist(self._last_hist, hist, cv2.HISTCMP_CORREL)
            ssim = _ssim(self._last_edges, edges)
            score = _HIST_WEIGHT * hist_corr + _SSIM_WEIGHT * ssim + _BIAS
            if self.stats_manager is not None:
                self.stats_manager.set_metrics(
                    timecode, {"koala_hist": hist_corr, "koala_ssim": ssim, "koala_score": score}
                )
            cuts = self._score_frame(timecode, score)
        else:
            # First frame: seed `min_scene_len` from the start of detection, as AdaptiveDetector
            # does, so the first cut must also be at least `min_scene_len` after the first frame.
            self._last_cut = timecode
        self._last_hist, self._last_edges = hist, edges
        return cuts

    def post_process(self, timecode: FrameTimecode) -> list[FrameTimecode]:
        """Decide the frames still held back by the smoothing look-ahead (`adaptive` only).

        These frames have no look-ahead of their own, so they are decided on their raw scores,
        as in the reference implementation. A transition beginning within them still yields a
        cut. Note that cuts returned from here bypass the `callback` passed to
        :meth:`SceneManager.detect_scenes <scenedetect.scene_manager.SceneManager.detect_scenes>`,
        which is only invoked for cuts returned by :meth:`process_frame`.
        """
        cuts: list[FrameTimecode] = []
        while self._pending:
            timecode, score = self._pending.popleft()
            cuts += self._decide(timecode, score, [pending for _, pending in self._pending])
        return cuts

    def _score_frame(self, timecode: FrameTimecode, score: float) -> list[FrameTimecode]:
        """Decide `timecode` from `score` (its similarity to the previous frame), or queue it
        until its moving average is complete when `adaptive` is set. Frames at the start of the
        video are decided on their raw score, as in the reference implementation."""
        if not self._adaptive:
            return self._decide(timecode, score, [])
        index, self._num_scores = self._num_scores, self._num_scores + 1
        self._raw.append(score)
        self._pending.append((timecode, score))
        if index < self._half_filter:
            self._pending.popleft()
            return self._decide(timecode, score, [])
        if index >= 2 * self._half_filter:
            # Dot product with uniform weights reproduces `np.convolve(x, ones(n) / n)` bit-for-bit;
            # `np.mean` can differ by 1 ulp, which matters at the `cutoff` gate.
            smoothed = float(np.dot(self._raw, self._filter_weights))
            timecode, score = self._pending.popleft()
            look_ahead = [pending for _, pending in self._pending]
            return self._decide(timecode, score, look_ahead, smoothed)
        return []

    def _decide(
        self,
        timecode: FrameTimecode,
        score: float,
        look_ahead: list[float],
        smoothed: float | None = None,
    ) -> list[FrameTimecode]:
        """Flag `timecode` if it is part of a transition, emitting a cut when one begins.

        `look_ahead` holds the raw scores of the frames following `timecode` that have already
        been scored (empty unless `adaptive` is set)."""
        raw_flagged = score < self._threshold
        flagged = raw_flagged
        if self._adaptive:
            smoothed = score if smoothed is None else smoothed
            window_full = len(self._smoothed) == self._window_size
            if not flagged and window_full and smoothed < self._cutoff:
                window = np.sort(np.asarray(self._smoothed))
                trimmed = window[int(0.2 * len(window)) : int(0.8 * len(window))]
                std = max(self._std_floor, float(trimmed.std()))
                flagged = smoothed < float(trimmed.mean()) - self._deviation * std
            self._smoothed.append(smoothed)
        if not flagged:
            self._in_run = self._cut_deferred = False
            return []
        if self._in_run:
            # A later frame of the same transition: only emit if its cut was deferred to here.
            if not (self._cut_deferred and raw_flagged):
                return []
            self._cut_deferred = False
        else:
            self._in_run = True
            if not raw_flagged and any(later < self._threshold for later in look_ahead):
                # Flagged only by the adaptive rule, with the raw drop still to come.
                self._cut_deferred = True
                return []
        assert self._last_cut is not None
        if (timecode - self._last_cut) < self._min_scene_len:
            return []
        self._last_cut = timecode
        return [timecode]
