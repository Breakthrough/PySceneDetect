from statistics import mean

class Evaluator:
    def __init__(self):
        pass
    
    def _load_scenes(self, scene_filename):
        with open(scene_filename) as f:
            gt_scene_list = [x.strip().split('\t')[1] for x in f.readlines()]
            gt_scene_list = [int(x) + 1 for x in gt_scene_list]
        return gt_scene_list

    def evaluate_performance(self, pred_scenes):
        total_correct = 0
        total_pred = 0
        total_gt = 0

        for scene_file, pred in pred_scenes.items():
            gt_scene_list = self._load_scenes(scene_file)
            pred_list = pred['pred_scenes']
            total_correct += len(set(pred_list) & set(gt_scene_list))
            total_pred += len(pred_list)
            total_gt += len(gt_scene_list)

        recall = total_correct / total_gt
        precision = total_correct / total_pred
        f1 = 2 * recall * precision / (recall + precision) if (recall + precision) != 0 else 0
        avg_elapsed = mean([x['elapsed'] for x in pred_scenes.values()])
        result = {
            'recall': recall * 100,
            'precision': precision * 100,
            'f1': f1 * 100,
            'elapsed': avg_elapsed
        }
        return result