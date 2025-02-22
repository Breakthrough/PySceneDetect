import argparse
import time
import os
import typing as ty

from tqdm import tqdm

from benchmark.autoshot_dataset import AutoShotDataset
from benchmark.bbc_dataset import BBCDataset
from benchmark.evaluator import Evaluator
from scenedetect import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
    detect,
)

_DETECTORS = {
    "detect-adaptive": AdaptiveDetector,
    "detect-content": ContentDetector,
    "detect-hash": HashDetector,
    "detect-hist": HistogramDetector,
    "detect-threshold": ThresholdDetector,
}


_DATASETS = {
    "BBC": BBCDataset("benchmark/BBC"),
    "AutoShot": AutoShotDataset("benchmark/AutoShot"),
}

_DEFAULT_DETECTOR = "detect-content"
_DEFAULT_DATASET = "BBC"

_RESULT_PRINT_FORMAT = (
    "Recall: {recall:.2f}, Precision: {precision:.2f}, F1: {f1:.2f} Elapsed time: {elapsed:.2f}\n"
)


def _detect_scenes(detector: str, dataset: str, detailed: bool):
    pred_scenes = {}
    for video_file, scene_file in tqdm(_DATASETS[dataset]):
        start = time.time()
        pred_scene_list = detect(video_file, _DETECTORS[detector]())
        elapsed = time.time() - start
        filename = os.path.basename(video_file)
        scenes = {
            scene_file: {
                "video_file": filename,
                "elapsed": elapsed,
                "pred_scenes": [scene[1].frame_num for scene in pred_scene_list],
            }
        }
        result = Evaluator().evaluate_performance(scenes)
        if detailed:
            print(f"\n{filename} results:")
            print(_RESULT_PRINT_FORMAT.format(**result) + "\n")
        pred_scenes.update(scenes)

    return pred_scenes


def run_benchmark(detector: str, dataset: str, detailed: bool):
    print(f"Evaluating {detector} on dataset {dataset}...\n")
    pred_scenes = _detect_scenes(detector=detector, dataset=dataset, detailed=detailed)
    result = Evaluator().evaluate_performance(pred_scenes)
    # Print extra separators in detailed output to identify overall results vs individual videos.
    if detailed:
        print("------------------------------------------------------------")
    print(f"\nOverall Results for {detector} on dataset {dataset}:")
    print(_RESULT_PRINT_FORMAT.format(**result))
    if detailed:
        print("------------------------------------------------------------")


def create_parser():
    parser = argparse.ArgumentParser(description="Benchmarking PySceneDetect performance.")
    parser.add_argument(
        "--dataset",
        type=str,
        choices=[
            "BBC",
            "AutoShot",
        ],
        help="Dataset name. Supported datasets are BBC and AutoShot.",
    )
    parser.add_argument(
        "--detector",
        type=str,
        choices=[
            "detect-adaptive",
            "detect-content",
            "detect-hash",
            "detect-hist",
            "detect-threshold",
        ],
        help="Detector name. Implemented detectors are listed: "
        "https://www.scenedetect.com/docs/latest/cli.html",
    )
    parser.add_argument(
        "--detailed",
        action="store_const",
        const=True,
        help="Print results for each video, in addition to overall summary.",
    )
    parser.add_argument(
        "--all",
        action="store_const",
        const=True,
        help="Benchmark all detectors on all datasets. If --detector or --dataset are specified, "
        "will only run with those.",
    )
    return parser


def run_all_benchmarks(detector: ty.Optional[str], dataset: ty.Optional[str], detailed: bool):
    detectors = {detector: _DETECTORS[detector]} if detector else _DETECTORS
    datasets = {dataset: _DATASETS[dataset]} if dataset else _DATASETS
    print(
        "Running benchmarks for:\n"
        f" - Detectors: {', '.join(detectors.keys())}\n"
        f" - Datasets: {', '.join(datasets.keys())}\n"
    )
    for detector in detectors:
        for dataset in datasets:
            run_benchmark(detector=detector, dataset=dataset, detailed=detailed)


def main():
    parser = create_parser()
    args = parser.parse_args()
    if args.all:
        run_all_benchmarks(
            detector=args.detector, dataset=args.dataset, detailed=bool(args.detailed)
        )
    else:
        run_benchmark(
            detector=args.detector if args.detector else _DEFAULT_DETECTOR,
            dataset=args.dataset if args.dataset else _DEFAULT_DATASET,
            detailed=bool(args.detailed),
        )


if __name__ == "__main__":
    main()
