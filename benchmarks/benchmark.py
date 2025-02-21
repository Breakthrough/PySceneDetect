import argparse
import time

from bbc_dataset import BBCDataset
from autoshot_dataset import AutoShotDataset

from evaluator import Evaluator
from tqdm import tqdm

from scenedetect import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
    detect,
)


def _make_detector(detector_name: str):
    detector_map = {
        "detect-adaptive": AdaptiveDetector(),
        "detect-content": ContentDetector(),
        "detect-hash": HashDetector(),
        "detect-hist": HistogramDetector(),
        "detect-threshold": ThresholdDetector(),
    }
    return detector_map[detector_name]


def _make_dataset(dataset_name: str):
    dataset_map = {
        "BBC": BBCDataset("BBC"),
        "AutoShot": AutoShotDataset("AutoShot"),
    }
    return dataset_map[dataset_name]


def _detect_scenes(detector_type: str, dataset):
    pred_scenes = {}
    for video_file, scene_file in tqdm(dataset):
        start = time.time()
        detector = _make_detector(detector_type)
        pred_scene_list = detect(video_file, detector)
        elapsed = time.time() - start
        scenes = {
            scene_file: {
                "video_file": video_file,
                "elapsed": elapsed,
                "pred_scenes": [scene[1].frame_num for scene in pred_scene_list],
            }
        }
        result = Evaluator().evaluate_performance(scenes)
        print(f"{video_file} results:")
        print(
            "Recall: {:.2f}, Precision: {:.2f}, F1: {:.2f} Elapsed time: {:.2f}\n".format(
                result["recall"], result["precision"], result["f1"], result["elapsed"]
            )
        )
        pred_scenes.update(scenes)

    return pred_scenes


def main(args):
    pred_scenes = _detect_scenes(detector_type=args.detector, dataset=_make_dataset(args.dataset))
    result = Evaluator().evaluate_performance(pred_scenes)
    print("Overall Results:")
    print(
        "Detector: {} Recall: {:.2f}, Precision: {:.2f}, F1: {:.2f} Elapsed time: {:.2f}".format(
            args.detector, result["recall"], result["precision"], result["f1"], result["elapsed"]
        )
    )


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
