
# PySceneDetect Python Interface

In addition to being used from the command line, or through the GUI, PySceneDetect can be used in Python directly - allowing easy integration into other applications/scripts, or interactive use through a Python REPL/notebook.

<div class="important">
The complete Python API Reference <span class="fa fa-book"> for the <tt>scenedetect</tt> module can be found in the <a href="http://pyscenedetect-manual.readthedocs.io/" alt="Manual Link">PySceneDetect Manual</a>, located at <a href="http://pyscenedetect-manual.readthedocs.io/" alt="Manual Link">pyscenedetect-manual.readthedocs.io/</a>.
</div>

## Quickstart

To get started, the `scenedetect.detect_scenes` function will perform content-aware scene detection and return the resulting scene list:


```python
from scenedetect import detect, ContentDetector
# Set show_progress=True when calling `detect` to display remaining time.
scene_list = detect('my_video.mp4', ContentDetector())
print(scene_list)
```

You can also split the video into scenes automatically using `ffmpeg` (or `mkvmerge`):

```python
from scenedetect import detect, ContentDetector, split_video_ffmpeg
scene_list = detect('my_video.mp4', ContentDetector())
split_video_ffmpeg('my_video.mp4', scene_list)
```

Note that you can modify the `threshold` argument when constructing the`ContentDetector`
to modify the detection sensitivity, or use other kinds of detection algorithms
(`ThresholdDetector`, `AdaptiveDetector`, etc...).

The next example shows how we can write our own function to do the same thing using the
various library components. This allows better control and integration with more complex
workflows.

## Detailed Example

In the following example, we create a function `find_scenes()` which loads a video,
uses `ContentDetector` to find all scenes, and return a list of tuples containing the
(start, end) timecodes of each detected scene.  Note that you can modify the `threshold`
argument to modify the sensitivity of the `ContentDetector`, or try other detector types
(e.g. `ThresholdDetector`, `AdaptiveDetector`).

```python
from scenedetect import SceneManager, open_video, ContentDetector

def find_scenes(video_path, threshold=27.0):
    # Create our video & scene managers, then add the detector.
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(threshold=threshold))
    # Detect all scenes in video from current position to end.
    scene_manager.detect_scenes(video)
    # `get_scene_list` returns a list of start/end timecode pairs
    # for each scene that was found.
    return scene_manager.get_scene_list()
```

To get started, try printing the return value of `find_scenes` on a small video clip:

```python
scenes = find_scenes('video.mp4')
print(scenes)
```

A more advanced usage example can be found in [the API reference manual](https://pyscenedetect.readthedocs.io/projects/Manual/en/latest/api/scene_manager.html#scenemanager-example).


## Scene Detection in a Python REPL

PySceneDetect can be used interactively as well in a Python environment. Some functions (e.g. `detect_scenes`) also allow you to specify `show_progress=True` to provide an update for long-running operations.

In the future, functions may be added to preview the scene boundaries graphically using OpenCV's GUI functionality, to allow interactive use of PySceneDetect from the command-line without launching the full GUI.
