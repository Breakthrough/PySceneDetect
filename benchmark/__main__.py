import argparse
import time
import os

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


def _make_detector(detector_name: str):
    if detector_name == "detect-adaptive":
        return AdaptiveDetector()
    if detector_name == "detect-content":
        return ContentDetector()
    if detector_name == "detect-hash":
        return HashDetector()
    if detector_name == "detect-hist":
        return HistogramDetector()
    if detector_name == "detect-threshold":
        return ThresholdDetector()
    raise RuntimeError(f"Unknown detector: {detector_name}")


_DATASETS = {
    "BBC": BBCDataset("benchmark/BBC"),
    "AutoShot": AutoShotDataset("benchmark/AutoShot"),
}

_RESULT_PRINT_FORMAT = (
    "Recall: {recall:.2f}, Precision: {precision:.2f}, F1: {f1:.2f} Elapsed time: {elapsed:.2f}\n"
)


def _detect_scenes(detector_type: str, dataset):
    pred_scenes = {}
    for video_file, scene_file in tqdm(dataset):
        start = time.time()
        detector = _make_detector(detector_type)
        pred_scene_list = detect(video_file, detector)
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
        print(f"\n{filename} results:")
        print(_RESULT_PRINT_FORMAT.format(**result) + "\n")
        pred_scenes.update(scenes)

    return pred_scenes


def main(args):
    print(f"Evaluating {args.detector} on dataset {args.dataset}...\n")
    pred_scenes = _detect_scenes(detector_type=args.detector, dataset=_DATASETS[args.dataset])
    result = Evaluator().evaluate_performance(pred_scenes)
    print(f"\nOverall Results for {args.detector} on dataset {args.dataset}:")
    print(_RESULT_PRINT_FORMAT.format(**result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmarking PySceneDetect performance.")
    parser.add_argument(
        "--dataset",
        type=str,
        choices=[
            "BBC",
            "AutoShot",
        ],
        default="BBC",
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
        default="detect-content",
        help="Detector name. Implemented detectors are listed: https://www.scenedetect.com/docs/latest/cli.html",
    )
    args = parser.parse_args()
    main(args)
