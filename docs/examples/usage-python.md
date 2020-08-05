
# PySceneDetect Python Interface

In addition to being used from the command line, or through the GUI, PySceneDetect can be used in Python directly - allowing easy integration into other applications/scripts, or interactive use through a Python REPL/notebook.

<div class="important">
The complete Python API Reference <span class="fa fa-book"> for the <tt>scenedetect</tt> module can be found in the <a href="http://pyscenedetect-manual.readthedocs.io/" alt="Manual Link">PySceneDetect Manual</a>, located at <a href="http://pyscenedetect-manual.readthedocs.io/" alt="Manual Link">pyscenedetect-manual.readthedocs.io/</a>.
</div>


## Quickstart

In the code example below, we create a function `find_scenes()` which will
load a video, detect the scenes, and return a list of tuples containing the
(start, end) timecodes of each detected scene.  Note that you can modify
the `threshold` argument to modify the sensitivity of the `ContentDetector`.

```python
# Standard PySceneDetect imports:
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager

# For content-aware scene detection:
from scenedetect.detectors.content_detector import ContentDetector

def find_scenes(video_path, threshold=30.0):
    # Create our video & scene managers, then add the detector.
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(threshold=threshold))

    # Base timestamp at frame 0 (required to obtain the scene list).
    base_timecode = video_manager.get_base_timecode()

    # Improve processing speed by downscaling before processing.
    video_manager.set_downscale_factor()

    # Start the video manager and perform the scene detection.
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    # Each returned scene is a tuple of the (start, end) timecode.
    return scene_manager.get_scene_list(base_timecode)
```

To get started, try printing the return value of `find_scenes` on a small video clip:

```python
scenes = find_scenes('video.mp4')
print(scenes)
```

A more advanced usage example can be found in [the API reference manual](https://pyscenedetect.readthedocs.io/projects/Manual/en/stable/api/scene_manager.html#scenemanager-example).


## Scene Detection in a Python REPL

PySceneDetect can be used interactively as well.  One way to get familiar with this is to type the above example into a Python REPL line by line, viewing the output as you run through the code and making sure you understand the output/results.  In the future, functions may be added to preview the scene boundaries graphically using OpenCV's GUI functionality, to allow interactive use of PySceneDetect from the command-line without launching the full GUI.
