
# PySceneDetect Python Interface

In addition to being used from the command line, or through the GUI, PySceneDetect can be used in Python directly - allowing easy integration into other applications/scripts, or interactive use through a Python REPL/notebook.


## PySceneDetect API Reference

**The complete PySceneDetect Python API reference [can be found *here* (link).](http://pyscenedetect-api.readthedocs.io/)**


## Example

The following short Python program shows the general usage style of how to detect scenes using PySceneDetect.  This shows how to open a video (or videos), save/load stats to/from a statsfile (CSV), perform scene detection (using the `ContentDetector`), and print a list of detected scenes to the terminal/console.  

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

        # Set downscale factor to improve processing speed (no args means default).
        video_manager.set_downscale_factor()

        # Start video_manager.
        video_manager.start()

        # Perform scene detection on video_manager.
        scene_manager.detect_scenes(frame_source=video_manager,
                                    start_time=start_time)

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


## Scene Detection in a Python REPL

PySceneDetect can be used interactively as well.  One way to get familiar with this is to type the above example into a Python REPL line by line, viewing the output as you run through the code and making sure you understand the output/results.  In the future, functions may be added to preview the scene boundaries graphically using OpenCV's GUI functionality, to allow interactive use of PySceneDetect from the command-line without launching the full GUI.

