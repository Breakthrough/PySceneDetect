#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""":class:`TransnetV2Detector` uses a pretrained neural network.

This detector is available from the command-line as the `detect-transnetv2` command.
"""

from logging import getLogger
from pathlib import Path

import cv2
import numpy as np

from scenedetect.common import FramePosition, TimecodeLike
from scenedetect.detector import FlashFilter, SceneDetector

logger = getLogger("pyscenedetect")


class Detector:
    def __init__(self, threshold: float, flash_filter: FlashFilter):
        self.i = 0
        self.y_prev = 0
        self.threshold = threshold
        self.flash_filter = flash_filter

    def push(self, ys: np.ndarray, positions: np.ndarray) -> list[FramePosition]:
        predictions = (ys > self.threshold).astype(np.uint8)

        cuts = []
        for y, position in zip(predictions, positions, strict=True):
            if position is None:
                continue

            is_cut = self.y_prev == 0 and y == 1 and self.i > 0
            cuts.extend(self.flash_filter.filter(position, is_cut))
            self.y_prev = y
            self.i += 1

        return cuts


class Predictor:
    def __init__(
        self,
        model_path: str | Path,
        flash_filter: FlashFilter,
        onnx_providers: list[str] | None,
        threshold,
    ):
        import onnxruntime as ort  # pyright: ignore[reportMissingImports]

        ort.set_default_logger_severity(3)

        if onnx_providers is None:
            onnx_providers = ort.get_available_providers()

        sess_opt = ort.SessionOptions()
        sess_opt.log_severity_level = 3

        self.session = ort.InferenceSession(model_path, sess_opt=sess_opt, providers=onnx_providers)

        self.pixels = None
        self.positions: np.ndarray | None = None

        self.det = Detector(threshold, flash_filter)

    def _inference(self, pixels: np.ndarray, positions: np.ndarray) -> list[FramePosition]:
        pred = np.array(self.session.run(["output"], {"input": pixels}))[0]

        cuts = []
        for i in range(pred.shape[0]):
            cuts.extend(self.det.push(pred[i, 25:75, 0], positions[i, 25:75]))
        return cuts

    def push(self, pixels: np.ndarray, positions: np.ndarray) -> list[FramePosition]:
        if self.pixels is None:
            self.pixels = pixels
            self.positions = positions

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
                        np.full(100, None, dtype=object),
                        np.concatenate(
                            (
                                np.full(25, None, dtype=object),
                                positions[:75]
                            ),
                            0
                        ),
                    )
                ),
            )
        else:
            # `self.positions` is set in lockstep with `self.pixels` above, so it is non-None here.
            assert self.positions is not None
            c1 = self.pixels
            c2 = pixels

            p1 = self.positions
            p2 = positions

            self.pixels = pixels
            self.positions = positions

            return self._inference(
                np.stack(
                    (np.concatenate((c1[25:], c2[:25]), 0), np.concatenate((c1[75:], c2[:75]), 0))
                ),
                np.stack(
                    (np.concatenate((p1[25:], p2[:25]), 0), np.concatenate((p1[75:], p2[:75]), 0))
                ),
            )


class TransnetV2Detector(SceneDetector):
    def __init__(
        self,
        model_path: str | Path = "tests/resources/transnetv2.onnx",
        onnx_providers: list[str] | None = None,
        threshold: float = 0.5,
        min_scene_len: TimecodeLike = 15,
        filter_mode: FlashFilter.Mode = FlashFilter.Mode.MERGE,
    ):
        super().__init__()

        self.px = np.zeros((2, 100, 27, 48, 3), dtype=np.uint8)
        self.positions = np.full((2, 100), None, dtype=object)

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

    def process_frame(self, position: FramePosition, frame_img: np.ndarray) -> list[FramePosition]:
        """Process the next frame."""

        pixels = cv2.resize(frame_img, (48, 27), interpolation=cv2.INTER_AREA)

        self.px[self.j, self.i] = pixels
        self.positions[self.j, self.i] = position
        self.i += 1

        if self.i >= 100:
            cuts = self.predictor.push(self.px[self.j], self.positions[self.j])
            self.j = 1 - self.j
            self.i = 0

            return cuts
        else:
            return []

    def post_process(self, position: FramePosition) -> list[FramePosition]:
        """Flush buffered model predictions."""

        cuts = []
        blank_frame = self.blank[:]

        self.px[self.j, self.i :] = blank_frame
        self.positions[self.j, self.i :] = None
        cuts.extend(self.predictor.push(self.px[self.j], self.positions[self.j]))

        self.j = 1 - self.j

        self.px[self.j, :] = blank_frame
        self.positions[self.j, :] = None
        cuts.extend(self.predictor.push(self.px[self.j], self.positions[self.j]))

        return cuts
