import glob
import os


class BBCDataset:
    """
    The BBC Dataset, proposed by Baraldi et al. in A deep siamese network for scene detection in broadcast videos
    Link: https://arxiv.org/abs/1510.08893
    The dataset consists of 11 videos (BBC/videos/bbc_01.mp4 to BBC/videos/bbc_11.mp4).
    The annotated scenes are provided in corresponding files (BBC/fixed/[i]-scenes.txt).
    """

    def __init__(self, dataset_dir: str):
        self._video_files = [
            file
            for file in sorted(
                glob.glob(os.path.join("benchmarks", dataset_dir, "videos", "*.mp4"))
            )
        ]
        self._scene_files = [
            file
            for file in sorted(glob.glob(os.path.join("benchmarks", dataset_dir, "fixed", "*.txt")))
        ]
        assert len(self._video_files) == len(self._scene_files)
        for video_file, scene_file in zip(self._video_files, self._scene_files):
            video_id = os.path.basename(video_file).replace("bbc_", "").split(".")[0]
            scene_id = os.path.basename(scene_file).split("-")[0]
            assert video_id == scene_id

    def __getitem__(self, index):
        video_file = self._video_files[index]
        scene_file = self._scene_files[index]
        return video_file, scene_file

    def __len__(self):
        return len(self._video_files)
