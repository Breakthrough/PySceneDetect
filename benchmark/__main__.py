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
import time
from pathlib import Path

from tqdm import tqdm

from benchmark._common import (
    DEFAULT_BACKEND,
    DETECTORS,
    FADE_HEADER,
    HARD_HEADER,
    fade_row,
    hard_row,
    parse_tolerances,
    render_table,
    write_json,
)
from benchmark.dataset import DATASETS, Dataset, resolve_dataset
from benchmark.evaluator import BenchmarkResult, Prediction, evaluate
from scenedetect import AVAILABLE_BACKENDS, detect


def _run_predictions(
    dataset: Dataset,
    detector_name: str,
    backend: str,
) -> dict[Path, Prediction]:
    """Detect cuts for every video in ``dataset`` and return predictions keyed by path."""
    detector_cls = DETECTORS[detector_name]
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


def _print_results(
    detector: str,
    dataset_name: str,
    dataset: Dataset,
    results: list[BenchmarkResult],
) -> None:
    print(f"\n## {detector} on {dataset_name} (hard cuts)\n")
    print(render_table(HARD_HEADER, [hard_row(r) for r in results]))
    if "fade" in dataset.event_types:
        print(f"\n## {detector} on {dataset_name} (fades)\n")
        print(render_table(FADE_HEADER, [fade_row(r) for r in results]))


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
        choices=list(DETECTORS.keys()),
        help=f"Detector name. One of: {', '.join(DETECTORS.keys())}.",
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
        default=DEFAULT_BACKEND,
        choices=sorted(AVAILABLE_BACKENDS.keys()),
        help=(
            f"Video decoding backend (default: {DEFAULT_BACKEND}). Override to compare "
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
    tolerances = parse_tolerances(args.tolerance)
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
        write_json(
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
