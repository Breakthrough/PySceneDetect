

The complete PySceneDetect Python API reference [can be found *here* (link).](http://pyscenedetect-api.readthedocs.io/)

-------------------------------



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

`post_process(...)` is called ***after** the final frame has been processed, to allow for any stored scene cuts to be written *if required* (e.g. in the case of the `ThresholdDetector`).

You may also want to look into the implementation of current detectors to understand how frame metrics are saved/loaded to/from a StatsManager for caching and allowing values to be written to a stats file for users to graph and find trends in to tweak detector options.  Also see the section on the `SceneManager` in the [Python API Reference](python-api.md) for details.

