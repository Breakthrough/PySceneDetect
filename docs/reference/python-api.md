

API Reference
----------------------------------------------------------

<div class="important">
The complete Python API Reference <span class="fa fa-book"> for the <tt>scenedetect</tt> module can be found in the <a href="http://pyscenedetect-manual.readthedocs.io/" alt="Manual Link">PySceneDetect Manual</a>, located at <a href="http://pyscenedetect-manual.readthedocs.io/" alt="Manual Link">pyscenedetect-manual.readthedocs.io/</a>.
</div>

API Overview
==========================================================

See [the API Overview](https://pyscenedetect.readthedocs.io/projects/Manual/en/latest/api.html) page of the manual for an overview of PySceneDetect's module & class layout.  There are three main modules:

 - `scenedetect` - main functionality, has imports for commonly used classes and detection algorithms
 - `scenedetect.detectors` - scene detection algorithms
 - `scenedetect.cli` - command-line specific functionality

Classes from main `scenedetect` module:

 - `FrameTimecode` - used to store timecodes as well as perform arithmetic on timecode values (addition/subtraction/comparison) with frame-accurate precision
 - `SceneManager` - high-level manager to coordinate SceneDetector, VideoManager, and optionally, StatsManager objects
 - `VideoManager` - used to load video(s) and provide seeking
 - `StatsManager` - used to store/cache frame metrics to speed up subsequent scene detection runs on the same video, and optionally, save/load to/from a CSV file
 - `SceneDetector` - base class used to implement detection algorithms (e.g. `ContentDetector`, `ThresholdDetector`)

SceneDetector objects available in the `scenedetect.detectors` module:

 - `ThresholdDetector` - detects fade-outs/fade-ins to/from black by looking at the intensity/brightness of the video
 - `ContentDetector` - detects scene cuts/content changes by converting the video to the HSV colourspace

 All functions are well documented with complete docstrs, and documentation can be found by calling help() from a Python REPL or browsing the complete PySceneDetect v0.5 API Reference below.  Also note that auto-generated documentation (via the `pydoc` command/module) can be generated.

The complete PySceneDetect Python API reference [can be found *here* (link).](https://pyscenedetect-manual.readthedocs.io/).


Using PySceneDetect from Python
----------------------------------------------------------

PySceneDetect can also be used from within other Python programs, or even the Python REPL itself.  PySceneDetect allows you to perform scene detection on a video file, yielding a list of scene cuts/breaks at the exact frame number where the scene boundaries occur.

The general usage workflow is to determine which detection method and threshold to use (this can even be done iteratively), using these values to create a `SceneDetector` object, the type of which depends on the detection method you want to use (e.g. `ThresholdDetector`, `ContentDetector`).  A list of `SceneDetector` objects is then passed with an open `VideoCapture` object and an empty list to the `scenedetect.detect_scenes()` function, which appends the frame numbers of any detected scene boundaries to the list (the function itself returns the number of frames read from the video file).


### Example


In the code example below, we create a function `find_scenes()` which will
load a video, detect the scenes, and return a list of tuples containing the
(start, end) timecodes of each detected scene.  Note that you can modify
the `threshold` argument to modify the sensitivity of the scene detection.

```python
# Standard PySceneDetect imports:
from scenedetect import VideoManager
from scenedetect import SceneManager

# For content-aware scene detection:
from scenedetect.detectors import ContentDetector

def find_scenes(video_path, threshold=30.0):
    # Create our video & scene managers, then add the detector.
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(threshold=threshold))

    # Improve processing speed by downscaling before processing.
    scene_manager.auto_downscale = True

    # Start the video manager and perform the scene detection.
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    # Each returned scene is a tuple of the (start, end) timecode.
    return scene_manager.get_scene_list()
```


The scene list returned by the `SceneManager.get_scene_list()` method consists of the start and (one past) the end frame of each scene, in the form of a `FrameTimecode` object.  Each `FrameTimecode` can be converted to the appropriate working/output format via the `get_timecode()`, `get_frames()`, or `get_seconds()` methods as shown above; see the API documentation for `FrameTimecode` objects for details.


For a more advanced example, see [the `api_test.py` file in the `tests` folder](https://github.com/Breakthrough/PySceneDetect/blob/master/tests/api_test.py) which illustrates the general workflow and usage of the `scenedetect` module to perform scene detection programmatically.  It provides a good example as to the general usage of the PySceneDetect Python API for detecting the scenes on an input video and printing the scenes to the terminal/console.
