
PySceneDetect
==========================================================

Usage (Command Line)
----------------------------------------------------------

In order to effectively use PySceneDetect, you should become familiar with the basic command line options (especially the detection method commands `detect-content` and `detect-threshold`, both of which have an adjustable threshold value option `-t` / `--threshold`).  Descriptions for all command-line arguments/options can be obtained by running PySceneDetect with the `help` command, `help all`, or `help [command]` (e.g. `help detect-content`).

There are two main detection methods PySceneDetect uses: threshold (`detect-threshold`, comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and content (`detect-content`, compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `detect-content` mode.  Use `detect-threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.

Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--stats` flag) in order to determine the correct paramters - specifically, the proper threshold value.  It is always recommended to generate a stats file to speed up subsequent calls to PySceneDetect for the same input video(s).


### Content-Aware Detection Mode

Unlike threshold mode, content-aware mode looks at the *difference* between each pair of adjacent frames, triggering a scene break when this difference exceeds the threshold value.  A good threshold value to try when using content-aware mode (`detect-content`) is `30` (`-t 30`), which is the default, for example the following two commands are equivalent:

```rst
scenedetect -i my_video.mp4 -s my_video.stats.csv detect-content

scenedetect -i my_video.mp4 -s my_video.stats.csv detect-content -t 30
```

The optimal threshold can be determined by generating a statsfile (`-s`) as shown above, opening it with a spreadsheet editor (e.g. Excel), and examining the `content_val` column.  This value should be very small between similar frames, and grow large when a big change in content is noticed (look at the values near frame numbers/times where you know a scene change occurs).  The threshold value should be set so that most scenes fall below the threshold value, and scenes where changes occur should *exceed* the threshold value (thus triggering a scene change).

To automatically split the video based on the detected scenes (will save starting from `my_video-Scene-001.mp4`, call `help split-video` for details on changing the output filename format), we add the `split-video` command at the end:

```rst
scenedetect -i my_video.mp4 -s my_video.stats.csv detect-content -t 30 split-video
```


### Threshold-Based Detection Mode

Threshold-based mode is what most traditional scene detection programs use, which looks at the average intensity of the *current* frame, triggering a scene break when the intensity falls below the threshold (or crosses back upwards).  A good threshold value to try when using threshold mode (`detect-threshold`) is `12` (`-t 12`), with a minimum percentage of at least 90% (`-m 0.9`).  Using values less than `8` may cause problems with some videos (especially those encoded at lower quality bitrates).

The optimal threshold can be determined by generating a statsfile (`-s`), opening it with a spreadsheet editor (e.g. Excel), and examining the `delta_rgb` column.  These values represent the average intensity of the pixels for that particular frame (taken by averaging the R, G, and B values over the whole frame).  The threshold value should be set so that the average intensity of most frames in content scenes lie above the threshold value, and scenes where scene changes/breaks occur should fall *under* the threshold value (thus triggering a scene change).


Usage (Python)
----------------------------------------------------------

PySceneDetect can also be used from within other Python programs.  This allows you to perform scene detection directly in Python code using a `SceneManager`, which allows adding specific `SceneDetector` objects.  You can then perform scene detection on frames obtained from a `VideoManager` object (similar to an OpenCV `VideoCapture` object but with additional features to facilitate scene detection, like frame-accurate seeking support).

The complete PySceneDetect Python API Reference can be found at the following URL:

[http://pyscenedetect-api.readthedocs.io/](http://pyscenedetect-api.readthedocs.io/)

Performing scene detection/segmenting live video streams is only supported by the API currently, not the CLI.  See the API documentation on the parameters a `VideoManager` object constructor takes for details (pass a list containing the device ID instead of a filename, e.g. `[1]` for device 1).

The general usage workflow is to determine which detection method and threshold to use (this can even be done iteratively), using these values to create a `SceneDetector` object, the type of which depends on the detection method you want to use (e.g. `ThresholdDetector`, `ContentDetector`).  These detectors are then added to a `SceneManager` class, with optionally a `StatsManager` to cache frame metrics so subsequent scene detection runs are much faster (and can be saved/loaded to/from disk).  Finally, an open `VideoManager` object can be passed to the `SceneManager.detect_scenes()` method, which returns the number of frames processed.

The following shows the contents of [the `api_test.py` file](https://github.com/Breakthrough/PySceneDetect/blob/master/tests/api_test.py) included with the PySceneDetect source code, which provides an example as to the general usage of the PySceneDetect Python API:


```python
from __future__ import print_function
import os

import scenedetect
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.stats_manager import StatsManager
from scenedetect.detectors import ContentDetector

STATS_FILE_PATH = 'api_test_statsfile.csv'

def main():

    print("Running PySceneDetect API test...")

    print("PySceneDetect version being used: %s" % str(scenedetect.__version__))

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


The scene list returned by the `SceneManager.get_scene_list(...)` method consists of the start and (one past) the end frame of each scene, in the form of a `FrameTimecode` object.  Each `FrameTimecode` can be converted to the appropriate working/output format via the `get_timecode()`, `get_frames()`, or `get_sceonds()` methods as shown above; see the API documentation for `FrameTimecode` objects for details.


----------------------------------------------------------


Licensed under BSD 3-Clause (see the `LICENSE` file for details).

Copyright (C) 2012-2018 Brandon Castellano.
All rights reserved.
