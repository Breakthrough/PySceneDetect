# Python API

The complete Python API reference is in the [Reference Manual](/docs/latest/api.html). See [Documentation Versions](docs.md) for older releases.

## Scene Detection Algorithms

This page describes how each built-in detector works, along with its key CLI options and default values.

### Adaptive Content Detector

The adaptive detector (`AdaptiveDetector` / `detect-adaptive`, default in the CLI) scores adjacent frames the same way as `ContentDetector`, then compares each frame's score against a rolling average of nearby frames. This reduces false cuts during fast camera movement.

Default settings: `--threshold 3.0`, `--frame-window 2`, `--min-content-val 15.0`. See [`detect-adaptive`](/docs/latest/cli.html#detect-adaptive) and [`AdaptiveDetector`](/docs/latest/api/detectors.html#adaptivedetector) for details.

### Content-Aware Detector

The content detector (`ContentDetector` / `detect-content`) finds fast cuts between scenes. It converts each frame from [RGB](https://en.wikipedia.org/wiki/RGB_color_space) to [HSV](https://en.wikipedia.org/wiki/HSL_and_HSV), computes the average difference across hue, saturation, and value (brightness) between adjacent frames, and records a cut when that score exceeds `--threshold` (default: `27.0`).

You can also enable edge detection by passing four weights (`delta_hue`, `delta_sat`, `delta_lum`, `delta_edges`). Edge differences are usually larger than color differences, so raise the threshold when enabling edges (for example, `-w 1.0 0.5 1.0 0.2 -t 32`). The default weights are `--weights 1.0 1.0 1.0 0.0` (edges disabled).

See [`detect-content`](/docs/latest/cli.html#detect-content) and [`ContentDetector`](/docs/latest/api/detectors.html#contentdetector) for details.

### Threshold Detector

The threshold detector (`ThresholdDetector` / `detect-threshold`) finds fades to and from black, similar to the `ffmpeg blackframe` filter. It averages the R, G, and B values of every pixel in each frame to get a brightness score from `0.0` to `255.0`, and records fade events when that score crosses `--threshold` (default: `12.0`).

See [`detect-threshold`](/docs/latest/cli.html#detect-threshold) and [`ThresholdDetector`](/docs/latest/api/detectors.html#thresholddetector) for details.

### Histogram Detector

The histogram detector (`HistogramDetector` / `detect-hist`) finds fast cuts using brightness histograms. It converts each frame to the YUV color space, extracts the Y (luminance) channel, and builds a normalized histogram with `--bins` bins (default: `128`).

Adjacent frame histograms are compared using correlation (`cv2.HISTCMP_CORREL`). When the difference exceeds `--threshold` (default: `0.20`), the detector records a cut. Focusing on luminance makes this detector less sensitive to pure color shifts.

See [`detect-hist`](/docs/latest/cli.html#detect-hist) and [`HistogramDetector`](/docs/latest/api/detectors.html#histogramdetector) for details.

### Perceptual Hash Detector

The perceptual hash detector (`HashDetector` / `detect-hash`) computes a perceptual hash (`phash`, based on [imagehash](https://github.com/JohannesBuchner/imagehash)) for each frame and compares adjacent hashes using normalized Hamming distance. When the distance exceeds `--threshold` (default: `0.35`, with `--size 8` and `--lowpass 2`), it records a cut.

Because `phash` converts frames to grayscale first, `HashDetector` ignores color changes when brightness stays constant. It is fast even without downscaling. See [Looks Like It](https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html) for a visual explanation of perceptual hashing.

See [`detect-hash`](/docs/latest/cli.html#detect-hash) and [`HashDetector`](/docs/latest/api/detectors.html#hashdetector) for details.

## Creating New Detection Algorithms

Custom detectors must inherit from [`SceneDetector`](/docs/latest/api/detector.html). Because the `SceneDetector` interface may change before v1.0, pin your dependency to a minor version (for example, `scenedetect~=0.7`).

To create a detector, implement `process_frame` and, if needed, `post_process`:

```python
import numpy as np
from scenedetect import FrameTimecode, SceneDetector


class CustomDetector(SceneDetector):
    """Example custom scene detector."""

    def process_frame(
        self,
        timecode: FrameTimecode,
        frame_img: np.ndarray,
    ) -> list[FrameTimecode]:
        # Return a list of cut timecodes found on this frame or earlier.
        return []

    def post_process(self, timecode: FrameTimecode) -> list[FrameTimecode]:
        # Called after the last frame to emit any pending cuts.
        return []
```

PySceneDetect calls `process_frame(timecode, frame_img)` for every frame in sequence:

- `timecode`: `FrameTimecode` of the current frame.
- `frame_img`: decoded video frame as a NumPy `ndarray`.

After the final frame, PySceneDetect calls `post_process(timecode)` so multi-pass detectors or detectors waiting on an end condition (such as `ThresholdDetector`) can emit remaining cuts. Both methods return a list of `FrameTimecode` cut locations. Note that detectors that emit cuts only in `post_process` will not report cuts live on continuous streams.

To save or reuse frame metrics in a CSV stats file, integrate with [`StatsManager`](/docs/latest/api/stats_manager.html). See the built-in detectors in [`scenedetect/detectors/`](https://github.com/Breakthrough/PySceneDetect/tree/main/scenedetect/detectors), [`SceneDetector`](/docs/latest/api/detector.html#scenedetect.detector.SceneDetector), and [`SceneManager`](/docs/latest/api/scene_manager.html) for working examples.
