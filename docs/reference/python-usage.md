
Using PySceneDetect in Python
----------------------------------------------------------

PySceneDetect can also be used from within other Python programs, or even the Python REPL itself.  PySceneDetect allows you to perform scene detection on a video file, yielding a list of scene cuts/breaks at the exact frame number where the scene boundaries occur.

The general usage workflow is to determine which detection method and threshold to use (this can even be done iteratively), using these values to create a `SceneDetector` object, the type of which depends on the detection method you want to use (e.g. `ThresholdDetector`, `ContentDetector`).  A list of `SceneDetector` objects is then passed with an open `VideoCapture` object and an empty list to the `scenedetect.detect_scenes()` function, which appends the frame numbers of any detected scene boundaries to the list (the function itself returns the number of frames read from the video file).

Note that the complete PySceneDetect Python API reference [can be found *here* [PySceneDetect Manual].](http://pyscenedetect-manual.readthedocs.io/)



### Example

The following short program/code sample ([the `api_test.py` file in the `tests` folder]((https://github.com/Breakthrough/PySceneDetect/blob/master/tests/api_test.py))) illustrates the general workflow and usage of the `scenedetect` module to perform scene detection programmatically.  It provides a good example as to the general usage of the PySceneDetect Python API for detecting the scenes on an input video and printing the scenes to the terminal/console.


```python
from __future__ import print_function
import os

import scenedetect
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.stats_manager import StatsManager
from scenedetect.detectors import ContentDetector

STATS_FILE_PATH = 'testvideo.stats.csv'

def main():
    # Create a video_manager point to video file testvideo.mp4. Note that multiple
    # videos can be appended by simply specifying more file paths in the list
    # passed to the VideoManager constructor. Note that appending multiple videos
    # requires that they all have the same frame size, and optionally, framerate.
    video_manager = VideoManager(['testvideo.mp4'])
    stats_manager = StatsManager()
    scene_manager = SceneManager(stats_manager)
    # Add ContentDetector algorithm (constructor takes detector options like threshold).
    scene_manager.add_detector(ContentDetector())
    base_timecode = video_manager.get_base_timecode()

    try:
        # If stats file exists, load it.
        if os.path.exists(STATS_FILE_PATH):
            # Read stats from CSV file opened in read mode:
            with open(STATS_FILE_PATH, 'r') as stats_file:
                stats_manager.load_from_csv(stats_file, base_timecode)

        start_time = base_timecode + 20     # 00:00:00.667
        end_time = base_timecode + 20.0     # 00:00:20.000
        # Set video_manager duration to read frames from 00:00:00 to 00:00:20.
        video_manager.set_duration(start_time=start_time, end_time=end_time)

        # Set downscale factor to improve processing speed.
        video_manager.set_downscale_factor()

        # Start video_manager.
        video_manager.start()

        # Perform scene detection on video_manager.
        scene_manager.detect_scenes(frame_source=video_manager)

        # Obtain list of detected scenes.
        scene_list = scene_manager.get_scene_list(base_timecode)
        # Like FrameTimecodes, each scene in the scene_list can be sorted if the
        # list of scenes becomes unsorted.

        print('List of scenes obtained:')
        for i, scene in enumerate(scene_list):
            print('    Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
                i+1,
                scene[0].get_timecode(), scene[0].get_frames(),
                scene[1].get_timecode(), scene[1].get_frames(),))

        # We only write to the stats file if a save is required:
        if stats_manager.is_save_required():
            with open(STATS_FILE_PATH, 'w') as stats_file:
                stats_manager.save_to_csv(stats_file, base_timecode)

    finally:
        video_manager.release()

if __name__ == "__main__":
    main()
```


The scene list returned by the `SceneManager.get_scene_list(...)` method consists of the start and (one past) the end frame of each scene, in the form of a `FrameTimecode` object.  Each `FrameTimecode` can be converted to the appropriate working/output format via the `get_timecode()`, `get_frames()`, or `get_sceonds()` methods as shown above; see the API documentation for `FrameTimecode` objects for details.

