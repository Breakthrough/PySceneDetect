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
""":class:`TransnetV2Detector` uses a pretrained neural network.

This detector is available from the command-line as the `detect-transnetv2` command.
"""

import typing as ty
import warnings
from enum import Enum
from logging import getLogger
from pathlib import Path

import cv2
import numpy as np

from scenedetect.common import FrameTimecode, Timecode
from scenedetect.detector import FlashFilter, SceneDetector

logger = getLogger("pyscenedetect")


class Detector:
    def __init__(self, threshold: float, flash_filter: FlashFilter):
        self.i = 0
        self.y_prev = 0
        self.threshold = threshold
        self.flash_filter = flash_filter

    def push(self, ys: np.ndarray, ts: np.ndarray):
        predictions = (ys > self.threshold).astype(np.uint8)

        cuts = []
        for y, t in zip(predictions, ts, strict=True):
            if self.y_prev == 0 and y == 1 and self.i > 0:
                cuts.append(t)
            self.y_prev = y
            self.i += 1

        return cuts


class Predictor:
    def __init__(
        self,
        model_path: ty.Union[str, Path],
        flash_filter: FlashFilter,
        onnx_providers: ty.Union[ty.List[str], None],
        threshold,
    ):
        import onnxruntime as ort

        ort.set_default_logger_severity(3)

        if onnx_providers is None:
            onnx_providers = ort.get_available_providers()

        sess_opt = ort.SessionOptions()
        sess_opt.log_severity_level = 3

        self.session = ort.InferenceSession(model_path, sess_opt=sess_opt, providers=onnx_providers)

        self.pixels = None
        self.time = None

        self.det = Detector(threshold, flash_filter)

    def _inference(self, pixels: np.ndarray, time: np.ndarray):
        pred = np.array(self.session.run(["output"], {"input": pixels}))[0]

        cuts = []
        for i in range(pred.shape[0]):
            cuts.extend(self.det.push(pred[i, 25:75, 0], time[i, 25:75]))
        return cuts

    def push(self, pixels: np.ndarray, time: np.ndarray):
        if self.pixels is None:
            self.pixels = pixels
            self.time = time

            return self._inference(
                np.stack(
                    (
                        np.tile(np.expand_dims(pixels[0], axis=0), (100, 1, 1, 1)),
                        np.concatenate(
                            (
                                np.tile(np.expand_dims(pixels[0], axis=0), (25, 1, 1, 1)),
                                pixels[:75],
                            ),
                            0,
                        ),
                    )
                ),
                np.stack(
                    (
                        np.tile(np.expand_dims(time[0], axis=0), (100,)),
                        np.concatenate(
                            (np.tile(np.expand_dims(time[0], axis=0), (25,)), time[:75]), 0
                        ),
                    )
                ),
            )
        else:
            c1 = self.pixels
            c2 = pixels

            t1 = self.time
            t2 = time

            self.pixels = pixels
            self.time = time

            return self._inference(
                np.stack(
                    (np.concatenate((c1[25:], c2[:25]), 0), np.concatenate((c1[75:], c2[:75]), 0))
                ),
                np.stack(
                    (np.concatenate((t1[25:], t2[:25]), 0), np.concatenate((t1[75:], t2[:75]), 0))
                ),
            )


class TransnetV2Detector(SceneDetector):
    def __init__(
        self,
        model_path: ty.Union[str, Path] = "tests/resources/transnetv2.onnx",
        onnx_providers: ty.Union[ty.List[str], None] = None,
        threshold: float = 0.5,
        min_scene_len: int = 15,
        filter_mode: FlashFilter.Mode = FlashFilter.Mode.MERGE,
    ):
        super().__init__()

        self.px = np.zeros((2, 100, 27, 48, 3), dtype=np.uint8)
        self.time = np.zeros((2, 100), dtype=np.int64)

        self.blank = np.zeros(self.px.shape[2:], dtype=np.uint8)

        self.i = 0
        self.j = 0

        self.predictor = Predictor(
            model_path=model_path,
            flash_filter=FlashFilter(mode=filter_mode, length=min_scene_len),
            onnx_providers=onnx_providers,
            threshold=threshold,
        )
        # TODO(https://scenedetect.com/issue/168): Figure out a better long term plan for handling
        # `min_scene_len` which should be specified in seconds, not frames.
        self._flash_filter = FlashFilter(mode=filter_mode, length=min_scene_len)

    def mk_ft(self, pts: int):
        # t = Timecode(pts=pts, time_base=self.time_base)
        t = float(pts * self.time_base)
        return FrameTimecode(t, fps=self._fps)

    def process_frame(
        self, timecode: FrameTimecode, frame_img: np.ndarray
    ) -> ty.List[FrameTimecode]:
        """Process the next frame."""

        self.time_base = timecode.time_base
        self._fps = timecode._rate

        pixels = cv2.resize(frame_img, (48, 27), interpolation=cv2.INTER_AREA)

        self.px[self.j, self.i] = pixels
        self.time[self.j, self.i] = timecode.pts
        self.i += 1

        if self.i >= 100:
            cuts = self.predictor.push(self.px[self.j], self.time[self.j])
            self.j = 1 - self.j
            self.i = 0

            filtered_cuts = []
            for cut in cuts:
                filtered_cuts += self._flash_filter.filter(self.mk_ft(cut), True)
            return filtered_cuts
        else:
            return []

    def post_process(self, timecode: FrameTimecode) -> ty.List[FrameTimecode]:
        """Writes a final scene cut if the last detected fade was a fade-out."""

        cuts = []

        last_time = timecode.pts
        blank_frame = self.blank[:]

        self.px[self.j, self.i :] = blank_frame
        self.time[self.j, self.i :] = last_time
        cuts.extend(self.predictor.push(self.px[self.j], self.time[self.j]))

        self.j = 1 - self.j

        self.px[self.j, :] = blank_frame
        self.time[self.j, :] = last_time
        cuts.extend(self.predictor.push(self.px[self.j], self.time[self.j]))

        filtered_cuts = []
        for cut in cuts:
            filtered_cuts += self._flash_filter.filter(self.mk_ft(cut), True)
        return filtered_cuts
