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
"""Command-line entrypoint for the PySceneDetect benchmark harness.

Runs one detector against a single dataset using default parameters, and calculates TRECVID-SBD
metrics using the given frame tolerance (usually 0 or 1). Hard-cut precision/recall/F1, mean
absolute frame offset on matches, and per-video elapsed wall-clock are calculated. If a dataset
advertises typed fade ground truth, a second table reports fade precision/recall/F1.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

from tqdm import tqdm

from benchmark.dataset import DATASETS, Dataset, resolve_dataset
from benchmark.evaluator import BenchmarkResult, Frames, Prediction, evaluate
from scenedetect import (
    AVAILABLE_BACKENDS,
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
    detect,
)

_DEFAULT_BACKEND = "opencv"

_DETECTORS: dict[str, type] = {
    "detect-adaptive": AdaptiveDetector,
    "detect-content": ContentDetector,
    "detect-hash": HashDetector,
    "detect-hist": HistogramDetector,
    "detect-threshold": ThresholdDetector,
}


def _parse_tolerances(spec: str) -> tuple[Frames, ...]:
    """Parse ``"0,1,5"`` into ``(0, 1, 5)``. Blank entries (e.g. trailing comma) are dropped."""
    return tuple(int(x.strip()) for x in spec.split(",") if x.strip())


def _run_predictions(
    dataset: Dataset,
    detector_name: str,
    backend: str,
) -> dict[Path, Prediction]:
    """Detect cuts for every video in ``dataset`` and return predictions keyed by path."""
    detector_cls = _DETECTORS[detector_name]
    predictions: dict[Path, Prediction] = {}
    for sample in tqdm(dataset, desc=detector_name):
        start = time.time()
        pred_scene_list = detect(str(sample.video_file), detector_cls(), backend=backend)
        elapsed = time.time() - start
        predictions[sample.video_file] = Prediction(
            predicted_cuts=[scene[1].frame_num for scene in pred_scene_list],
            ground_truth=sample.ground_truth,
            elapsed=elapsed,
        )
    return predictions


# --------------------------------------------------------------------- #
# Output formatting
# --------------------------------------------------------------------- #


def _fmt_pct(value: float, count: int) -> str:
    """Percentage, or ``n/a`` when the underlying class has zero events."""
    return "n/a" if count == 0 else f"{value * 100:.2f}"


def _fmt_offset(value: float) -> str:
    return "n/a" if math.isnan(value) else f"{value:.3f}"


def _render_table(header: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(len(header))]
    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(header, widths, strict=True)) + " |"
    body = [
        "| " + " | ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)) + " |" for r in rows
    ]
    return "\n".join([header_line, sep, *body])


_HARD_HEADER = ["Tolerance", "Precision", "Recall", "F1", "Offset", "Elapsed"]
_FADE_HEADER = ["Tolerance", "Precision", "Recall", "F1"]


def _hard_row(result: BenchmarkResult) -> list[str]:
    hard = result.hard_cuts
    hard_predictions = hard.matched + hard.false_positives
    hard_events = hard.matched + hard.missed
    return [
        str(result.tolerance),
        _fmt_pct(hard.precision, hard_predictions),
        _fmt_pct(hard.recall, hard_events),
        _fmt_pct(hard.f1, hard_events),
        _fmt_offset(result.mean_abs_offset_hard_cuts),
        f"{result.elapsed_mean:.2f}",
    ]


def _fade_row(result: BenchmarkResult) -> list[str]:
    fades = result.fades
    fade_predictions = fades.matched + fades.false_positives
    fade_events = fades.matched + fades.missed
    return [
        str(result.tolerance),
        _fmt_pct(fades.precision, fade_predictions),
        _fmt_pct(fades.recall, fade_events),
        _fmt_pct(fades.f1, fade_events),
    ]


def _print_results(
    detector: str,
    dataset_name: str,
    dataset: Dataset,
    results: list[BenchmarkResult],
) -> None:
    print(f"\n## {detector} on {dataset_name} (hard cuts)\n")
    print(_render_table(_HARD_HEADER, [_hard_row(r) for r in results]))
    if "fade" in dataset.event_types:
        print(f"\n## {detector} on {dataset_name} (fades)\n")
        print(_render_table(_FADE_HEADER, [_fade_row(r) for r in results]))


def _write_json(out_path: str, payload: dict[str, Any]) -> None:
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\nWrote results to {out_path}")


# --------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------- #


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmarking PySceneDetect performance.")
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=list(DATASETS.keys()),
        help=f"Dataset name. One of: {', '.join(DATASETS.keys())}.",
    )
    parser.add_argument(
        "--detector",
        type=str,
        required=True,
        choices=list(_DETECTORS.keys()),
        help=f"Detector name. One of: {', '.join(_DETECTORS.keys())}.",
    )
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=None,
        help=(
            "Base directory containing per-dataset subfolders. Defaults to 'benchmark' "
            "(the in-repo location). Use this to read videos from an external location, "
            "e.g. --dataset-root D:/path/to/benchmark."
        ),
    )
    parser.add_argument(
        "--backend",
        type=str,
        default=_DEFAULT_BACKEND,
        choices=sorted(AVAILABLE_BACKENDS.keys()),
        help=(
            f"Video decoding backend (default: {_DEFAULT_BACKEND}). Override to compare "
            "detector output across backends, e.g. opencv vs pyav."
        ),
    )
    parser.add_argument(
        "--tolerance",
        type=str,
        default="0,1",
        help=(
            "Comma-separated list of frame tolerances for hard-cut matching (default: 0,1). "
            "+/-0 is the literature-strict number; +/-1 masks single-frame encoder artifacts."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Path to write a machine-readable JSON results file (includes per-video stats).",
    )
    parser.add_argument(
        "--quick",
        type=int,
        nargs="?",
        const=10,
        default=None,
        metavar="N",
        help=(
            "Score only the first N samples from the dataset (default N=10) for fast "
            "iteration. Use this to smoke-test config changes; published numbers should "
            "always come from the full corpus."
        ),
    )
    return parser


def main() -> None:
    args = create_parser().parse_args()
    tolerances = _parse_tolerances(args.tolerance)
    dataset = resolve_dataset(args.dataset, args.dataset_root)
    if len(dataset) == 0:
        raise SystemExit(
            f"Dataset {args.dataset!r} at {args.dataset_root or 'benchmark'} is empty - "
            "check that videos and annotations are present."
        )
    if args.quick is not None:
        dataset._samples = dataset._samples[: args.quick]
        print(f"--quick: limited to first {len(dataset)} samples")
    print(f"Evaluating {args.detector} on {args.dataset} (backend={args.backend})")

    payloads = _run_predictions(dataset, args.detector, args.backend)
    results = [evaluate(payloads, tolerance=t) for t in tolerances]

    _print_results(args.detector, args.dataset, dataset, results)
    if args.out:
        _write_json(
            args.out,
            {
                "detector": args.detector,
                "dataset": args.dataset,
                "backend": args.backend,
                "results": [r.to_dict() for r in results],
            },
        )


if __name__ == "__main__":
    main()
