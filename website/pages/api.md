
# API Reference

The Python API is documented using Sphinx and [can be found here](docs.md).

# Scene Detection Algorithms

This page discusses the scene detection methods/algorithms available for use in PySceneDetect, including details describing the operation of the detection method, as well as relevant command-line arguments and recommended values.

## Content-Aware Detector

The content-aware scene detector (`detect-content`) detects [jump cuts](https://en.wikipedia.org/wiki/Jump_cut) in the input video.  This is typically what people think of as "cuts" between scenes in a movie - given two adjacent frames, do they belong to the same scene?  The content-aware scene detector finds areas where the *difference* between two subsequent frames exceeds the threshold value that is set (a good value to start with is `--threshold 27`).

Internally, this detector functions by converting the colorspace of each decoded frame from [RGB](https://en.wikipedia.org/wiki/RGB_color_space) into [HSV](https://en.wikipedia.org/wiki/HSL_and_HSV).  It then takes the average difference across all channels (or optionally just the *value* channel) from frame to frame.  When this exceeds a set threshold, a scene change is triggered.

`detect-content` also has edge detection, which can be enabled by providing a set of 4 numbers in the form (*delta_hue*, *delta_sat*, *delta_lum*, *delta_edges*). Changes in edges are typically larger than the other components, so threshold may need to be increased accordingly.  For example, `-w 1.0 0.5 1.0 0.2 -t 32` is a good starting point to use with edge detection.  The default weights are `--weights 1.0 1.0 1.0 0.0` which does not include edges, but this may change in the future.

See [the documentation for detect-content](https://www.scenedetect.com/docs/latest/cli.html#detect-content) for details.

## Adaptive Content Detector

The adaptive content detector (`detect-adaptive`) compares the difference in content between adjacent frames similar to `detect-content` but instead using a rolling average of adjacent frame changes. This helps mitigate false detections where there is fast camera motion.

## Threshold Detector

The threshold-based scene detector (`detect-threshold`) is how most traditional scene detection methods work (e.g. the `ffmpeg blackframe` filter), by comparing the intensity/brightness of the current frame with a set threshold, and triggering a scene cut/break when this value crosses the threshold.  In PySceneDetect, this value is computed by averaging the R, G, and B values for every pixel in the frame, yielding a single floating point number representing the average pixel value (from 0.0 to 255.0).

## Histogram Detector

The scene change detection algorithm uses histograms of the Y channel in the YCbCr color space to detect scene changes, which helps mitigate issues caused by lighting variations. Each frame of the video is converted from its original color space to the YCbCr color space. The Y channel, which represents luminance, is extracted from the YCbCr color space. This helps in focusing on intensity variations rather than color variations. A histogram of the Y channel is computed using the specified number of bins (--bins/-b). The histogram is normalized to ensure that it can be consistently compared with histograms from other frames. The normalized histogram of the current frame is compared with the normalized histogram of the previous frame using the correlation method (cv2.HISTCMP_CORREL). A scene change is detected if the correlation between the histograms of consecutive frames is below the specified threshold (--threshold/-t). This indicates a significant change in luminance, suggesting a scene change.

## Perceptual Hash Detector

The perceptual hash detector (`detect-hash`) calculates a hash for a frame and compares that hash to the previous frame's hash. If the hashes differ by more than the defined threshold, then a scene change is recorded. The hashing algorithm used for this detector is an implementation of `phash` from the [imagehash](https://github.com/JohannesBuchner/imagehash) library. In practice, this detector works similarly to `detect-content` in that it picks up large differences between adjacent frames. One important note is that the hashing algorithm converts the frames to grayscale, so this detector is insensitive to changes in colors if the brightness remains constant. In general, this algorithm is very computationally efficient compared to `detect-content` or `detect-adaptive`, especially if downscaling is not used. See [here](https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html) for an overview of how a perceptual hashing algorithm can be used for detecting similarity (or otherwise) of images and a visual depiction of the algorithm.


# Creating New Detection Algorithms

All scene detection algorithms must inherit from [the base `SceneDetector` class](https://www.scenedetect.com/docs/latest/api/detector.html). Note that the current SceneDetector API is under development and expected to change somewhat before v1.0 is released, so make sure to pin your `scenedetect` dependency to the correct API version (e.g. `scenedetect < 0.6`, `scenedetect < 0.7`, etc...).

Creating a new scene detection method can be as simple as implementing the `process_frame` function, and optionally `post_process`:

```python
import typing as ty
import numpy as np
from scenedetect import FramePosition, SceneDetector


class CustomDetector(SceneDetector):
    """CustomDetector class to implement a scene detection algorithm."""

    def process_frame(
        self,
        position: FramePosition,
        frame_img: np.ndarray,
    ) -> ty.List[FramePosition]:
        # Return positions where we found cuts (either on this frame or previously).
        return []

    def post_process(self, position: FramePosition) -> ty.List[FramePosition]:
        # Called after the last frame has been read to handle pending events.
        return []
```

`post_process` is called after frame processing ends. This may be useful for multi-pass algorithms, or detectors which are waiting on some condition but still wish to output an event on the final frame.

For example, a detector may return cuts from `process_frame`, save pending cuts for `post_process`, or use both. `post_process` runs only after detection stops. See the [API documentation for the `SceneDetector` class](https://www.scenedetect.com/docs/latest/api/detector.html#scenedetect.detector.SceneDetector) for details. Alternatively, you can call `help(SceneDetector)` from a Python REPL. For examples of actual detection algorithm implementations, see the source files in the `scenedetect/detectors/` directory (e.g. `threshold_detector.py`, `content_detector.py`).

Processing is done by calling the `process_frame(...)` function for each processed frame, followed by `post_process(...)` (optional) after the final frame. Each method returns a list of detected frame positions.

`process_frame(...)` is called for each frame in sequence, passing the following arguments:

- `position`: a `FramePosition` containing the current frame's `frame_number` and `timecode`. The `Timecode` stores its presentation timestamp (`pts`) and timestamp unit (`time_base`).
- `frame_img`: frame returned by the video file or stream (accessible as a NumPy array)

`post_process(...)` is called **after** the final frame has been processed, to allow for any stored scene cuts to be written *if required* (e.g. in the case of the `ThresholdDetector`).

You may also want to look into the implementation of current detectors to understand how frame metrics are saved/loaded to/from a [`StatsManager`](https://www.scenedetect.com/docs/latest/api/stats_manager.html) for caching and allowing values to be written to a stats file for users to graph and find trends in to tweak detector options.  Also see the documentation for the [`SceneManager`](https://www.scenedetect.com/docs/latest/api/scene_manager.html) for details.

