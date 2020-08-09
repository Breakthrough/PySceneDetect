
# Scene Detection Algorithms

This page discusses the scene detection methods/algorithms available for use in PySceneDetect, including details describing the operation of the detection method, as well as relevant command-line arguments and recommended values.

## Implemented Algorithms


### Content-Aware Detector

The content-aware scene detector (`detect-content`) works the way most people think of "cuts" between scenes in a movie - given two frames, do they belong to the same scene, or different scenes?  The content-aware scene detector finds areas where the *difference* between two subsequent frames exceeds the threshold value that is set (a good value to start with is `--threshold 30`).

This allows you to detect cuts between scenes both containing content, rather than how most traditional scene detection methods work.  With a properly set threshold, this method can even detect minor, abrupt changes, such as [jump cuts](https://en.wikipedia.org/wiki/Jump_cut) in film.


### Threshold Detector

The threshold-based scene detector (`detect-threshold`) is how most traditional scene detection methods work (e.g. the `ffmpeg blackframe` filter), by comparing the intensity/brightness of the current frame with a set threshold, and triggering a scene cut/break when this value crosses the threshold.  In PySceneDetect, this value is computed by averaging the R, G, and B values for every pixel in the frame, yielding a single floating point number representing the average pixel value (from 0.0 to 255.0).

## Creating New Detection Algorithms

All scene detection algorithms must inherit from [the base `SceneDetector` class](https://pyscenedetect.readthedocs.io/projects/Manual/en/stable/api/scene_detector.html).

Creating a new scene detection method is intuitive if you are familiar with Python and OpenCV already.  A `SceneDetector` is an object implementing the following class & methods (only prototypes are shown as an example):

```python
from scenedetect.scene_detector import SceneDetector

class CustomDetector(SceneDetector):
    """CustomDetector class to implement a scene detection algorithm."""
    def __init__(self):
        pass

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        """Computes/stores metrics and detects any scene changes.

        Prototype method, no actual detection.
        """
        return

    def post_process(self, scene_list):
        pass
```

See the actual `scenedetect/scene_detector.py` source file for specific details.  Alternatively, you can call `help(SceneDetector)` from a Python REPL.  For examples of actual detection algorithm implementations, see the source files in the `scenedetect/detectors/` directory (e.g. `threshold_detector.py`, `content_detector.py`).

Processing is done by calling the `process_frame(...)` function for all frames in the video, followed by `post_process(...)` (optional) after the final frame.  Scene cuts are detected and added to the passed list object in both cases.

`process_frame(...)` is called for each frame in sequence, passing the following arguments:

- `frame_num`: the number of the current frame being processed
- `frame_img`: frame returned video file or stream (accessible as NumPy array)
- `frame_metrics`: dictionary for memoizing results of detection algorithm calculations for quicker subsequent analyses (if possible)
- `scene_list`: List containing the frame numbers where all scene cuts/breaks occur in the video.

`post_process(...)` is called **after** the final frame has been processed, to allow for any stored scene cuts to be written *if required* (e.g. in the case of the `ThresholdDetector`).

You may also want to look into the implementation of current detectors to understand how frame metrics are saved/loaded to/from a StatsManager for caching and allowing values to be written to a stats file for users to graph and find trends in to tweak detector options.  Also see the section on the `SceneManager` in the [Python API Reference](python-api.md) for details.

