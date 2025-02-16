import time
import argparse
from bbc_dataset import BBCDataset
from evaluator import Evaluator

from tqdm import tqdm
from scenedetect import detect
from scenedetect import AdaptiveDetector, ContentDetector, HashDetector, HistogramDetector, ThresholdDetector

def _load_detector(detector_name: str):
    detector_map = {
        'detect-adaptive': AdaptiveDetector(),
        'detect-content': ContentDetector(),
        'detect-hash': HashDetector(),
        'detect-hist': HistogramDetector(),
        'detect-threshold': ThresholdDetector(),
    }
    return detector_map[detector_name]

def _detect_scenes(detector, dataset):
    pred_scenes = {}
    for video_file, scene_file in tqdm(dataset):
        start = time.time()
        pred_scene_list = detect(video_file, detector)
        elapsed = time.time() - start

        pred_scenes[scene_file] = {
            'video_file': video_file,
            'elapsed': elapsed,
            'pred_scenes': [scene[1].frame_num for scene in pred_scene_list]
        }

    return pred_scenes

def main(args):
    dataset = BBCDataset('BBC')
    detector = _load_detector(args.detector)
    pred_scenes = _detect_scenes(detector, dataset)
    evaluator = Evaluator()
    result = evaluator.evaluate_performance(pred_scenes)

    print('Detector: {} Recall: {:.2f}, Precision: {:.2f}, F1: {:.2f} Elapsed time: {:.2f}'
          .format(args.detector, result['recall'], result['precision'], result['f1'], result['elapsed']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmarking PySceneDetect performance.')
    parser.add_argument('--detector', type=str, choices=['detect-adaptive', 'detect-content', 'detect-hash', 'detect-hist', 'detect-threshold'], 
                        default='detect-content', help='Detector name. Implemented detectors are listed: https://www.scenedetect.com/docs/latest/cli.html')
    args = parser.parse_args()
    main(args)