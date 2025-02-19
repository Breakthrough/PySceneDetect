import glob
import os

class AutoShotDataset:
    """
    The AutoShot Dataset (test splits) proposed by Zhu et al. in AutoShot: A Short Video Dataset and State-of-the-Art Shot Boundary Detection
    Link: https://openaccess.thecvf.com/content/CVPR2023W/NAS/html/Zhu_AutoShot_A_Short_Video_Dataset_and_State-of-the-Art_Shot_Boundary_Detection_CVPRW_2023_paper.html
    The original test set consists of 200 videos, but 36 videos are missing (AutoShot/videos/<video_id>.mp4).
    The annotated scenes are provided in corresponding files (AutoShot/annotations/<video_id>.txt)
    """

    def __init__(self, dataset_dir: str):
        self._video_files = [
            file for file in sorted(glob.glob(os.path.join(dataset_dir, "videos", "*.mp4")))
        ]
        self._scene_files = [
            file for file in sorted(glob.glob(os.path.join(dataset_dir, "annotations", "*.txt")))
        ]
        for video_file, scene_file in zip(self._video_files, self._scene_files):
            video_id = os.path.basename(video_file).split(".")[0]
            scene_id = os.path.basename(scene_file).split(".")[0]
            assert video_id == scene_id

    def __getitem__(self, index):
        video_file = self._video_files[index]
        scene_file = self._scene_files[index]
        return video_file, scene_file

    def __len__(self):
        return len(self._video_files)
