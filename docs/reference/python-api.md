


<div class="warning">
<h3><span class="fa wy-text-warning"></span>&nbsp; Note that the Python API is undergoing major changes.</h3>
This documentation refers to the API as of PySceneDetect v0.3.x and before (corresponding to the older version on pip).  You can also see the Github releases page to download a specific version of PySceneDetect.  The next major release (v0.5) will include a stable API with a much more intuitive workflow for Python users while retaining full command-line usability as a front-end program.
</div>



Overview
----------------------------------------------------------

PySceneDetect can also be used from within other Python programs, or even the Python REPL itself.  PySceneDetect allows you to perform scene detection on a video file, yielding a list of scene cuts/breaks at the exact frame number where the scene boundaries occur.  Note: currently PySceneDetect requires the passed video stream to terminate, but support for live video stream segmentation is planned for the following version.

The general usage workflow is to determine which detection method and threshold to use (this can even be done iteratively), using these values to create a `SceneDetector` object, the type of which depends on the detection method you want to use (e.g. `ThresholdDetector`, `ContentDetector`).  A list of `SceneDetector` objects is then passed with an open `VideoCapture` object and an empty list to the `scenedetect.detect_scenes()` function, which appends the frame numbers of any detected scene boundaries to the list (the function itself returns the number of frames read from the video file).


Quick Example
----------------------------------------------------------

The below code sample is incomplete, but shows the general usage style:

```python
import scenedetect

scene_list = []        # Scenes will be added to this list in detect_scenes().
path = 'my_video.mp4'  # Path to video file.

# Usually use one detector, but multiple can be used.
detector_list = [
    scenedetect.detectors.ThresholdDetector(threshold = 16, min_percent = 0.9)
]

video_framerate, frames_read = scenedetect.detect_scenes_file(
    path, scene_list, detector_list)

# scene_list now contains the frame numbers of scene boundaries.
print scene_list

# create new list with scene boundaries in milliseconds instead of frame #.
scene_list_msec = [(1000.0 * x) / float(video_fps) for x in scene_list]

# create new list with scene boundaries in timecode strings ("HH:MM:SS.nnn").
scene_list_tc = [scenedetect.timecodes.get_string(x) for x in scene_list_msec]
```


API Reference
----------------------------------------------------------

Coming soon.

