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
"""Generates golden cut-lists in JSON format for the release test suite."""

import argparse
import json
import os

from scenedetect import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    SceneManager,
    ThresholdDetector,
    open_video,
)

VIDEOS = [
    "tests/resources/testvideo.mp4",
    "tests/resources/goldeneye.mp4",
    "tests/resources/goldeneye-vfr.mp4",
    "tests/resources/goldeneye-vfr-drop3.mp4",
    "tests/resources/fades.mp4",
    "tests/resources/counter.mp4",
]

# (DetectorClass, params, name_suffix)
DETECTORS = [
    (ContentDetector, {}, "default"),
    (ContentDetector, {"threshold": 30.0}, "t30"),
    (AdaptiveDetector, {}, "default"),
    (AdaptiveDetector, {"adaptive_threshold": 5.0}, "t5"),
    (ThresholdDetector, {}, "default"),
    (HistogramDetector, {}, "default"),
    (HashDetector, {}, "default"),
]


def generate_golden(video_path: str, detector_class, params: dict) -> list[int]:
    video = open_video(video_path, backend="pyav")
    scene_manager = SceneManager()
    scene_manager.add_detector(detector_class(**params))
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    # Return start frame of each scene except the first one (which is 0)
    return [scene[0].get_frames() for scene in scene_list[1:]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="tests/resources/goldens")
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    for video_path in VIDEOS:
        if not os.path.exists(video_path):
            print(f"Skipping {video_path}, not found.")
            continue

        video_name = os.path.basename(video_path)
        for detector_class, params, suffix in DETECTORS:
            detector_name = detector_class.__name__
            print(f"Generating golden for {video_name} with {detector_name} ({suffix})...")
            try:
                cuts = generate_golden(video_path, detector_class, params)
                output_filename = f"{video_name}.{detector_name}.{suffix}.json"
                output_path = os.path.join(args.output_dir, output_filename)
                with open(output_path, "w") as f:
                    json.dump({"cuts": cuts}, f)
            except Exception as e:
                print(f"Failed to generate golden for {video_name} with {detector_name}: {e}")


if __name__ == "__main__":
    main()
