
#
# PySceneDetect v0.5 API Test Script
#
# NOTE: This file can only be used with development versions of PySceneDetect,
#       and gives a high-level overview of how the new API will look and work.
#       This file is for development and testing purposes mostly, although it
#       also serves as a base for further example and test programs.
#

from __future__ import print_function

import scenedetect
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.stats_manager import StatsManager
#from scenedetect.scene_detectors import ContentDetector
from scenedetect.scene_manager import ContentDetectorNew as ContentDetector


def main():

    print("Running PySceneDetect API test...")

    print("PySceneDetect version being used: %s" % str(scenedetect.__version__))

    # Create a video_manager point to video file SOME_VIDEO_FILE.mp4
    # (can append multiple files with the same framerate as well).
    video_manager = VideoManager(['SOME_VIDEO_FILE.mp4'])
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)
    # Add ContentDetector algorithm (constructor takes algorithm options).
    scene_manager.add_detector(ContentDetector())
    base_timecode = video_manager.get_base_timecode()

    try:
        start_time = base_timecode          # 00:00:00
        duration = base_timecode + 20.0     # 00:00:20
        # Set video_manager duration to read frames from 00:00:00 to 00:00:20.
        video_manager.set_duration(start_time=start_time, end_time=duration)
        # Start video_manager.
        video_manager.start()

        # Perform scene detection on video_manager.
        scene_manager.detect_scenes(frame_source=video_manager, start_time=start_time)

        # Obtain scene list:
        scene_manager.get_scene_list()

        # Write stats to CSV file for reading:
        with open('output_stats_file.csv', 'w') as stats_file:
            stats_manager.save_to_csv(stats_file, base_timecode)

    finally:
        video_manager.stop()
        video_manager.release()

if __name__ == "__main__":
    main()

