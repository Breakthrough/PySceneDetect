
Creating a new scene detection method should be intuitive if you are familiar with Python and OpenCV already.  A `SceneDetector` is an object implementing the following class & methods:

```python
class SceneDetector(object):
    """Base SceneDetector class to implement a scene detection algorithm."""
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

Processing is done by calling the `process_frame(...)` function for all frames in the video, followed by `post_process(...)` (optional) after the final frame.  Scene cuts are detected and added to the passed list object in both cases.

`process_frame(...)` is called for each frame in sequence, passing the following arguments:

- `frame_num`: the number of the current frame being processed
- `frame_img`: frame returned video file or stream (accessible as NumPy array)
- `frame_metrics`: dictionary for memoizing results of detection algorithm calculations for quicker subsequent analyses (if possible)
- `scene_list`: List containing the frame numbers where all scene cuts/breaks occur in the video.

`post_process(...)` is called ***after** the final frame has been processed, to allow for any stored scene cuts to be written *if required* (e.g. in the case of the `ThresholdDetector`).
