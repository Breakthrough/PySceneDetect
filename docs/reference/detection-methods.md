
# Scene Detection Algorithms

This page discusses the scene detection methods/algorithms available for use in PySceneDetect, including details describing the operation of the detection method, as well as relevant command-line arguments and recommended values.

## Content-Aware Detector

The content-aware scene detector (`detect-content`) detects [jump cuts](https://en.wikipedia.org/wiki/Jump_cut) in the input video.  This is typically what people think of as "cuts" between scenes in a movie - given two adjacent frames, do they belong to the same scene?  The content-aware scene detector finds areas where the *difference* between two subsequent frames exceeds the threshold value that is set (a good value to start with is `--threshold 27`).

Internally, this detector functions by converting the colorspace of each decoded frame from [RGB](https://en.wikipedia.org/wiki/RGB_color_space) into [HSV](https://en.wikipedia.org/wiki/HSL_and_HSV).  It then takes the average difference across all channels (or optionally just the *value* channel) from frame to frame.  When this exceeds a set threshold, a scene change is triggered.

`detect-content` also has edge detection, which can be enabled by providing a set of 4 numbers in the form (*delta_hue*, *delta_sat*, *delta_lum*, *delta_edges*). Changes in edges are typically larger than the other components, so threshold may need to be increased accordingly.  For example, `-w 1.0 0.5 1.0 0.2 -t 32` is a good starting point to use with edge detection.  The default weights are `--weights 1.0 1.0 1.0 0.0` which does not include edges, but this may change in the future.

See [the documentation for detect-content](http://scenedetect.com/projects/Manual/en/latest/cli/detectors.html#detect-content) for details.

## Adaptive Content Detector

The adaptive content detector (`detect-adaptive`) compares the difference in content between adjacent frames similar to `detect-content` but instead using a rolling average of adjacent frame changes. This helps mitigate false detections where there is fast camera motion.

## Threshold Detector

The threshold-based scene detector (`detect-threshold`) is how most traditional scene detection methods work (e.g. the `ffmpeg blackframe` filter), by comparing the intensity/brightness of the current frame with a set threshold, and triggering a scene cut/break when this value crosses the threshold.  In PySceneDetect, this value is computed by averaging the R, G, and B values for every pixel in the frame, yielding a single floating point number representing the average pixel value (from 0.0 to 255.0).

# Creating New Detection Algorithms

All scene detection algorithms must inherit from [the base `SceneDetector` class](https://scenedetect.com/projects/Manual/en/latest/api/scene_detector.html). Note that the current SceneDetector API is under development and expected to change somewhat before v1.0 is released, so make sure to pin your `scenedetect` dependency to the correct API version (e.g. `scenedetect < 0.6`, `scenedetect < 0.7`, etc...).

Creating a new scene detection method can be as simple as implementing the `process_frame` function, and optionally `post_process`:

```python
from scenedetect.scene_detector import SceneDetector

class CustomDetector(SceneDetector):
    """CustomDetector class to implement a scene detection algorithm."""
    def __init__(self):
        pass

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        """Computes/stores metrics and detects any scene changes.

        Returns:
            A list containing 1 or more the frame numbers of any detected scenes.
        """
        return []

    def post_process(self, scene_list):
        pass
```

`process_frame` is called on every frame in the input video, which will be called after the final frame of the video is passed to `process_frame`. This may be useful for multi-pass algorithms, or detectors which are waiting on some condition but still wish to output an event on the final frame.

For example, a detector may output at most 1 cuts for every call to `process_frame`, it may output the entire scene list in `post_process`, or a combination of both.  Note that the latter will not work in cases where a live video stream or camera input device is being used. See the [API documentation for the `SceneDetector` class](https://scenedetect.com/projects/Manual/en/latest/api/scene_detector.html#scenedetect.scene_detector.SceneDetector) for details. Alternatively, you can call `help(SceneDetector)` from a Python REPL. For examples of actual detection algorithm implementations, see the source files in the `scenedetect/detectors/` directory (e.g. `threshold_detector.py`, `content_detector.py`).

Processing is done by calling the `process_frame(...)` function for all frames in the video, followed by `post_process(...)` (optional) after the final frame.  Scene cuts are detected and added to the passed list object in both cases.

`process_frame(...)` is called for each frame in sequence, passing the following arguments:

- `frame_num`: the number of the current frame being processed
- `frame_img`: frame returned video file or stream (accessible as NumPy array)
- `frame_metrics`: dictionary for memoizing results of detection algorithm calculations for quicker subsequent analyses (if possible)
- `scene_list`: List containing the frame numbers where all scene cuts/breaks occur in the video.

`post_process(...)` is called **after** the final frame has been processed, to allow for any stored scene cuts to be written *if required* (e.g. in the case of the `ThresholdDetector`).

You may also want to look into the implementation of current detectors to understand how frame metrics are saved/loaded to/from a [`StatsManager`](https://pyscenedetect.readthedocs.io/projects/Manual/en/stable/api/stats_manager.html) for caching and allowing values to be written to a stats file for users to graph and find trends in to tweak detector options.  Also see the documentation for the [`SceneManager`](https://pyscenedetect.readthedocs.io/projects/Manual/en/stable/api/scene_manager.html) for details.

