
API Overview
----------------------------------------------------------


There are three main modules:

 - scenedetect
 - scenedetect.detectors
 - scenedetect.cli

Classes from main `scenedetect` module:

 - FrameTimecode - used to store timecodes as well as perform arithmetic on timecode values (addition/subtraction/comparison) with frame-accurate precision
 - SceneManager - high-level manager to coordinate SceneDetector, VideoManager, and optionally, StatsManager objects
 - VideoManager - used to load video(s) and provide seeking
 - StatsManager - used to store/cache frame metrics to speed up subsequent scene detection runs on the same video, and optionally, save/load to/from a CSV file

SceneDetector objects available in the `scenedetect.detectors` module:

 - ThresholdDetector - detects fade-outs/fade-ins to/from black by looking at the intensity/brightness of the video 
 - ContentDetector - detects scene cuts/content changes by converting the video to the HSV colourspace 

 All functions are well documented with complete docstrs, and documentation can be found by calling help() from a Python REPL or browsing the complete PySceneDetect v0.5 API Reference below.  Also note that auto-generated documentation (via the `pydoc` command/module) can be generated.
 
 To get started with development and integration, also make sure to [see the `api_test.py` file](https://github.com/Breakthrough/PySceneDetect/blob/master/tests/api_test.py) for a complete example of performing scene detection using the PySceneDetect Python API.  Also as mentioned, use the built-in `help` command in the Python REPL on the various `scenedetect` module members to view the appropriate docstrs, view the API reference below, or generate a copy locally via `pydoc`.

Below are quick descriptions of the essential classes/objects that make up a part of the PySceneDetect API.

FrameTimecode
==========================================================

A `FrameTimecode` represents a point in time in a video with a known, fixed framerate, and is accurate to a given frame.  A `FrameTimecode` object is created with a frame number/timecode/seconds value, as well as the video's framerate, or a another timecode already containing the framerate.

In most use-cases, a `FrameTimecode` object is normally created from another `FrameTimecode` called the *base timecode*, returned by the video source (e.g. a `VideoManager`).  For example, given a `VideoManager` instance `video_manager`, we can create a new timecode `new_timecode` representing the frame 1 minute and 30 seconds in the source video by:

    video_manager = VideoManager(...)
    base_timecode = video_manager.get_base_timecode()
    new_timecode = FrameTimecode(base_timecode, new_time='00:01:30')

The FrameTimecode constructor prototype is:

    FrameTimecode(timecode, fps=None)

Where the arguments are:

 - `timecode` (*str, float, int, or FrameTimecode*) Timecode string, float number of seconds, int number of frames, or FrameTimecode to set new FrameTimecode object time/framerate to.
 - `fps` (*Conditional float*) Framerate of the video the timecodes represent. If `timecode` is a `FrameTimecode`, the `fps` argument does not need to be provided, and is taken from the passed timecode instead.

A FrameTimecode object has the following methods which are useful to inspect `FrameTimecode` objects and their properties (default values are shown for optional arguments):

 - `.get_frames()` (*int*) Get the frame number the FrameTimecode represents.
 - `.get_framerate()` (*float*) Get the framerate the FrameTimecode has.
 - `.get_timecode(precision: int=3, use_rounding: bool=True)` (*str*) Get the timecode in format  `'HH:MM:SS.NNN'`, where precision is the number of digits N (default 3), and  use_rounding specifies if rounding or truncation should be used.
 - `.equal_framerate(fps: float)` Returns True if fps is equal to the FrameTimecode's framerate.
 - `.get_seconds()` (*float*) Returns the number of seconds the FrameTimecode represents.

`FrameTimecode` objects can also be created by integer frame number or by a float representing the number of seconds:
    
    # Create a base timecode (frame 0) at 10 FPS.
    base_timecode = FrameTimecode(0, fps=10)
    # The following are all equivalent (00:01:30, or 1m30s,
    # is 90 seconds, or 900 frames at 10 FPS).
    new_timecode = FrameTimecode('00:01:30', base_timecode)
    new_timecode = FrameTimecode(90.0, base_timecode)
    new_timecode = FrameTimecode(900, base_timecode)

We can also perform math with `FrameTimecode` objects as well as comparison:

    other_timecode = FrameTimecode(new_time='00:02:00', base_timecode)
    print(other_timecode > new_timecode)
    other_timecode += new_timecode
    print(new_timecode)

The reason we need a base timecode is because FrameTimecodes have frame-accurate precision, which means they can only store time values if the framerate of the video is known.  Alternatively, a FrameTimecode can be created manually by the framerate (thus also allowing use of native OpenCV methods instead of the VideoManager):

    video_fps = video_manager.get_framerate()
    new_timecode = FrameTimecode('00:01:30', fps=video_fps)

`FrameTimecode` objects also support addition/subtraction of integers (with no negatives allowed, stopping at frame `0`, or `00:00:00` on all videos with all framerates), where the integer represents the number of *frames*, or floats, which represent the number of *seconds*.  Thus, all timecodes in the following example (except `base_timecode` which is at frame 0) are equal at a time of 90 seconds, or 00:01:30 (assuming a video framerate of 10 FPS for simplicity):

    base_timecode = FrameTimecode('00:00:00', fps=10)
    # 90 seconds at 10 FPS = 900 frames
    timecode_a = base_timecode + 900
    timecode_b = base_timecode + 90.0
    timecode_c = FrameTimecode('00:01:30', base_timecode)
    timecode_d = FrameTimecode('00:01:30', fps=10)
    # Don't try this in C!
    print(timecode_a == timecode_b == timecode_c == timecode_d)


VideoManager
==========================================================

A `VideoManager` is used to load one or more videos with an interface similar to the OpenCV `VideoCapture` object, but with extended capabilities required for use with the `SceneManager`.  This includes downscaling, seeking, and intuitive interfaces to retrive the video(s) resolution and base timecode (or framerate).

SceneManager
==========================================================

A `SceneManager` is used to coordinate scene detection between `SceneDetector` objects and a `VideoManager`, optionally storing the computed frame metrics in a `StatsManager`.  The `SceneManager` method `detect_scenes(...)` performs scene detection using all added detectors on the passed frame source, until exhausted.

Implementations that wish to view the scene list frame-by-frame, or event-driven/asynchronously, can do so by either adding hooks into the `SceneManager` `_process_frame(...)` and `_post_process(...)` methods, or alternatively, by overriding the implementation of the `detect_scenes(...)` method.



-------------------------------------

<h1 id="api_ref">API Reference</h1>

The following is the complete Python API reference for PySceneDetect v0.5.


# `scenedetect` Module

PySceneDetect scenedetect Module

This is the main PySceneDetect module, containing imports of all classes
so they can be directly accessed from the scenedetect module in addition
to being directly imported (e.g. `from scenedetect import FrameTimecode`
is the same as `from scenedetect.frame_timecode import FrameTimecode`).

This file also contains the PySceneDetect version string (displayed when calling
'scenedetect version'), the about string for license/copyright information
(when calling 'scenedetect about').

# `scenedetect.scene_detector` (`SceneDetector`)

PySceneDetect scenedetect.scene_detector Module

This module implements the base SceneDetector class, from which all scene
detectors in the scenedetect.dectectors module are derived from.

The SceneDetector class represents the interface which detection algorithms
are expected to provide in order to be compatible with PySceneDetect.

<h2 id="scenedetect.scene_detector.SceneDetector">SceneDetector</h2>

```python
SceneDetector(self)
```
Base class to inheret from when implementing a scene detection algorithm.

Also see the implemented scene detectors in the scenedetect.detectors module
to get an idea of how a particular detector can be created.

<h3 id="scenedetect.scene_detector.SceneDetector.is_processing_required">is_processing_required</h3>

```python
SceneDetector.is_processing_required(self, frame_num)
```
Is Processing Required: Test if all calculations for a given frame are already done.

Returns:
    (bool) True if the SceneDetector's stats_manager property is set to a valid
    StatsManager object, which contains all of the required frame metrics/calculations
    for the given frame (and thus, does not require decoding it). Returns False
    otherwise (i.e. the frame_img passed to process_frame is required).

<h3 id="scenedetect.scene_detector.SceneDetector.get_metrics">get_metrics</h3>

```python
SceneDetector.get_metrics(self)
```
Get Metrics:  Get a list of all metric names/keys used by the detector.

Returns:
    A List[str] of the frame metric key names that will be used by
    the detector when a StatsManager is passed to process_frame.

<h3 id="scenedetect.scene_detector.SceneDetector.process_frame">process_frame</h3>

```python
SceneDetector.process_frame(self, frame_num, frame_img)
```
Process Frame: Computes/stores metrics and detects any scene changes.

Prototype method, no actual detection.

Returns:
    List of frame numbers of cuts to be added to the cutting list.

<h3 id="scenedetect.scene_detector.SceneDetector.post_process">post_process</h3>

```python
SceneDetector.post_process(self, frame_num)
```
Post Process: Performs any processing after the last frame has been read.

Prototype method, no actual detection.

Returns:
    List of frame numbers of cuts to be added to the cutting list.

# `scenedetect.detectors` Module

PySceneDetect scenedetect.detectors Module

This module contains implementations of scene detection algorithms by inhereting
from the base SceneDetector class (in scenedetect.scene_detector) and implementing
the required methods. This allows implementation of other generic algorithms as
well as custom scenario-specific algorithms.

Individual detectors are imported in this file for easy access from other
modules (i.e. from scenedetect.detectors import ContentDetector).


# `scenedetect.detectors.content_detector` (`ContentDetector`)

PySceneDetect scenedetect.detectors.content_detector Module

This module implements the ContentDetector, which compares the difference
in content between adjacent frames against a set threshold/score, which if
exceeded, triggers a scene cut.

<h2 id="scenedetect.detectors.content_detector.ContentDetector">ContentDetector</h2>

```python
ContentDetector(self, threshold=30.0, min_scene_len=15)
```
Detects fast cuts using changes in colour and intensity between frames.

Since the difference between frames is used, unlike the ThresholdDetector,
only fast cuts are detected with this method.  To detect slow fades between
content scenes still using HSV information, use the DissolveDetector.


# `scenedetect.detectors.threshold_detector` (`ThresholdDetector`)

PySceneDetect scenedetect.detectors.threshold_detector Module

This module implements the ThresholdDetector, which uses a set intensity level
to detect scene cuts when the average frame intensity passes the set threshold.

<h2 id="scenedetect.detectors.threshold_detector.compute_frame_average">compute_frame_average</h2>

```python
compute_frame_average(frame)
```
Computes the average pixel value/intensity for all pixels in a frame.

The value is computed by adding up the 8-bit R, G, and B values for
each pixel, and dividing by the number of pixels multiplied by 3.

Returns:
    Floating point value representing average pixel intensity.

<h2 id="scenedetect.detectors.threshold_detector.ThresholdDetector">ThresholdDetector</h2>

```python
ThresholdDetector(self, threshold=12, min_percent=0.95, min_scene_len=15, fade_bias=0.0, add_final_scene=False, block_size=8)
```
Detects fast cuts/slow fades in from and out to a given threshold level.

Detects both fast cuts and slow fades so long as an appropriate threshold
is chosen (especially taking into account the minimum grey/black level).

Attributes:
    threshold:  8-bit intensity value that each pixel value (R, G, and B)
        must be <= to in order to trigger a fade in/out.
    min_percent:  Float between 0.0 and 1.0 which represents the minimum
        percent of pixels in a frame that must meet the threshold value in
        order to trigger a fade in/out.
    min_scene_len:  Unsigned integer greater than 0 representing the
        minimum length, in frames, of a scene (or subsequent scene cut).
    fade_bias:  Float between -1.0 and +1.0 representing the percentage of
        timecode skew for the start of a scene (-1.0 causing a cut at the
        fade-to-black, 0.0 in the middle, and +1.0 causing the cut to be
        right at the position where the threshold is passed).
    add_final_scene:  Boolean indicating if the video ends on a fade-out to
        generate an additional scene at this timecode.
    block_size:  Number of rows in the image to sum per iteration (can be
        tuned to increase performance in some cases; should be computed
        programmatically in the future).

<h3 id="scenedetect.detectors.threshold_detector.ThresholdDetector.frame_under_threshold">frame_under_threshold</h3>

```python
ThresholdDetector.frame_under_threshold(self, frame)
```
Check if the frame is below (true) or above (false) the threshold.

Instead of using the average, we check all pixel values (R, G, and B)
meet the given threshold (within the minimum percent).  This ensures
that the threshold is not exceeded while maintaining some tolerance for
compression and noise.

This is the algorithm used for absolute mode of the threshold detector.

Returns:
    Boolean, True if the number of pixels whose R, G, and B values are
    all <= the threshold is within min_percent pixels, or False if not.

<h3 id="scenedetect.detectors.threshold_detector.ThresholdDetector.post_process">post_process</h3>

```python
ThresholdDetector.post_process(self, frame_num)
```
Writes a final scene cut if the last detected fade was a fade-out.

Only writes the scene cut if add_final_scene is true, and the last fade
that was detected was a fade-out.  There is no bias applied to this cut
(since there is no corresponding fade-in) so it will be located at the
exact frame where the fade-out crossed the detection threshold.


# `scenedetect.frame_timecode` (`FrameTimecode`)

PySceneDetect Frame Timecode Module

This module contains the FrameTimecode object, which is used as a way for PySceneDetect
to store frame-accurate timestamps of each cut.  This is done by also specifying the
video framerate with the timecode, allowing a frame number to be converted to/from
a floating-point number of seconds, or string in the form "HH:MM:SS[.nnn]" (where the
"[.nnn]" part is optional).

Example:
    A FrameTimecode can be created by specifying the frame number as an integer, along
    with the framerate:

        $ t = FrameTimecode(timecode = 0, fps = 29.97)

    It can also be created from a floating-point number of seconds.  Note that calling
    t.get_frames() will return 200 in this case (10.0 seconds at 20.0 frames/sec):

        $ t = FrameTimecode(timecode = 10.0, fps = 20.0)

    Timecode can also be specified as a string in "HH:MM:SS[.nnn]" format.  Note that
    calling t.get_frames() will return 600 in this case (1 minute, or 60 seconds, at
    10 frames/sec):

        $ t = FrameTimecode(timecode = "00:01:00.000", fps = 10)

FrameTimecode objects can be added and subtracted.  Note, however, that a negative
timecode is not representable by a FrameTimecode, and subtractions towards zero
will wrap at 0.  For example, calling t.get_frame() in this case will return 0:

    $ t = FrameTimecode(0, 10) - FrameTimecode(10, 10)

 (i.e. calling get_frame() on FrameTimecode)
Unit tests for the FrameTimecode object can be found in tests/test_timecode.py.

<h2 id="scenedetect.frame_timecode.FrameTimecode">FrameTimecode</h2>

```python
FrameTimecode(self, timecode=None, fps=None)
```
Object for frame-based timecodes, using the video framerate
to compute back and forth between frame number and second/timecode formats.

The passed argument is declared valid if it meets one of three valid types:
  1) string: standard timecode HH:MM:SS[.nnn]:
        in string form 'HH:MM:SS' or 'HH:MM:SS.nnn', or
        in list/tuple form [HH, MM, SS] or [HH, MM, SS.nnn]
  2) float: number of seconds S[.SSS], where S >= 0.0:
        in string form 'Ss' or 'S.SSSs' (e.g. '5s', '1.234s'), or
        in integer or floating point form S or S.SSS
  3) int: Exact number of frames N, where N >= 0:
        in either integer or string form N or 'N'

Arguments:
    timecode (str, float, int, or FrameTimecode):  A timecode or frame
        number, given in any of the above valid formats/types.  This
        argument is always required.
    fps (float, or FrameTimecode, conditionally required): The framerate
        to base all frame to time arithmetic on (if FrameTimecode, copied
        from the passed framerate), to allow frame-accurate arithmetic. The
        framerate must be the same when combining FrameTimecode objects
        in operations. This argument is required argument, unless the
        passed timecode is of type FrameTimecode, from which it is copied.
Raises:
    TypeError, ValueError

<h3 id="scenedetect.frame_timecode.FrameTimecode.get_frames">get_frames</h3>

```python
FrameTimecode.get_frames(self)
```
Get the current time/position in number of frames.  This is the
equivalent of accessing the self.frame_num property (which, along
with the specified framerate, forms the base for all of the other
time measurement calculations, e.g. the get_seconds() method).

Returns:
    An integer of the current time/frame number.

<h3 id="scenedetect.frame_timecode.FrameTimecode.get_framerate">get_framerate</h3>

```python
FrameTimecode.get_framerate(self)
```
Get Framerate: Returns the framerate used by the FrameTimecode object.

Returns:
    Framerate (float) of the current FrameTimecode object, in frames per second.

<h3 id="scenedetect.frame_timecode.FrameTimecode.equal_framerate">equal_framerate</h3>

```python
FrameTimecode.equal_framerate(self, fps)
```
Equal Framerate: Determines if the passed framerate is equal to that of the
FrameTimecode object.

Arguments:
    fps:    Framerate (float) to compare against within the precision constant
            MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT defined in this module.

Returns:
    True if passed fps matches the FrameTimecode object's framerate, False otherwise.


<h3 id="scenedetect.frame_timecode.FrameTimecode.get_seconds">get_seconds</h3>

```python
FrameTimecode.get_seconds(self)
```
Get the frame's position in number of seconds.

Returns:
    A float of the current time/position in seconds.

<h3 id="scenedetect.frame_timecode.FrameTimecode.get_timecode">get_timecode</h3>

```python
FrameTimecode.get_timecode(self, precision=3, use_rounding=True)
```
Get a formatted timecode string of the form HH:MM:SS[.nnn].

Args:
    precision:     The number of decimal places to include in the output [.nnn].
    use_rounding:  True (default) to round the output to the desired precision.

Returns:
    A string with a formatted timecode (HH:MM:SS[.nnn]).


# `scenedetect.scene_manager` (`SceneManager`)

PySceneDetect scenedetect.scene_manager Module

This module implements the SceneManager object, which is used to coordinate
SceneDetectors and frame sources (e.g. VideoManagers, VideoCaptures), creating
a SceneResult object for each detected scene.

The SceneManager also facilitates passing a StatsManager, if any is defined,
to the associated SceneDetectors for caching of frame metrics.

<h2 id="scenedetect.scene_manager.write_scene_list">write_scene_list</h2>

```python
write_scene_list(output_csv_file, scene_list, cut_list=None)
```
Writes the given list of scenes to an output file handle in CSV format.

Arguments:
    output_csv_file: Handle to open file in write mode.
    scene_list: List of pairs of FrameTimecodes denoting each scene's start/end FrameTimecode.
    cut_list: Optional list of FrameTimecode objects denoting the cut list (i.e. the frames
        in the video that need to be split to generate individual scenes). If not passed,
        the start times of each scene (besides the 0th scene) is used instead.

<h2 id="scenedetect.scene_manager.SceneManager">SceneManager</h2>

```python
SceneManager(self, stats_manager=None)
```
The SceneManager facilitates detection of scenes via the detect_scenes() method,
given a video source (scenedetect.VideoManager or cv2.VideoCapture), and SceneDetector
algorithms added via the add_detector() method.

Can also optionally take a StatsManager instance during construction to cache intermediate
scene detection calculations, making subsequent calls to detect_scenes() much faster,
allowing the cached values to be saved/loaded to/from disk, and also manually determining
the optimal threshold values or other options for various detection algorithms.

<h3 id="scenedetect.scene_manager.SceneManager.add_detector">add_detector</h3>

```python
SceneManager.add_detector(self, detector)
```
Adds/registers a SceneDetector (e.g. ContentDetector, ThresholdDetector) to
run when detect_scenes is called. The SceneManager owns the detector object,
so a temporary may be passed.

Arguments:
    detector (SceneDetector): Scene detector to add to the SceneManager.

<h3 id="scenedetect.scene_manager.SceneManager.get_num_detectors">get_num_detectors</h3>

```python
SceneManager.get_num_detectors(self)
```
Gets number of registered scene detectors added via add_detector.
<h3 id="scenedetect.scene_manager.SceneManager.clear">clear</h3>

```python
SceneManager.clear(self)
```
Clears all cuts/scenes and resets the SceneManager's position.

Any statistics generated are still saved in the StatsManager object
passed to the SceneManager's constructor, and thus, subsequent
calls to detect_scenes, using the same frame source reset at the
initial time (if it is a VideoManager, use the reset() method),
will use the cached frame metrics that were computed and saved
in the previous call to detect_scenes.

<h3 id="scenedetect.scene_manager.SceneManager.clear_detectors">clear_detectors</h3>

```python
SceneManager.clear_detectors(self)
```
Removes all scene detectors added to the SceneManager via add_detector().
<h3 id="scenedetect.scene_manager.SceneManager.get_scene_list">get_scene_list</h3>

```python
SceneManager.get_scene_list(self, base_timecode)
```
Returns a list of tuples of start/end FrameTimecodes for each scene.

The scene list is generated from the cutting list (get_cut_list), noting that each
scene is contiguous, starting from the first and ending at the last frame of the input.

Returns:
    List of tuples in the form (start_time, end_time), where both start_time and
    end_time are FrameTimecode objects representing the exact time/frame where each
    detected scene in the video begins and ends.

<h3 id="scenedetect.scene_manager.SceneManager.get_cut_list">get_cut_list</h3>

```python
SceneManager.get_cut_list(self, base_timecode)
```
Returns a list of FrameTimecodes of the detected scene changes/cuts.

Unlike get_scene_list, the cutting list returns a list of FrameTimecodes representing
the point in the input video(s) where a new scene was detected, and thus the frame
where the input should be cut/split. The cutting list, in turn, is used to generate
the scene list, noting that each scene is contiguous starting from the first frame
and ending at the last frame detected.

Returns:
    List of FrameTimecode objects denoting the points in time where a scene change
    was detected in the input video(s), which can also be passed to external tools
    for automated splitting of the input into individual scenes.

<h3 id="scenedetect.scene_manager.SceneManager.detect_scenes">detect_scenes</h3>

```python
SceneManager.detect_scenes(self, frame_source, start_time=0, end_time=None, frame_skip=0, show_progress=True)
```
Perform scene detection on the given frame_source using the added SceneDetectors.

Blocks until all frames in the frame_source have been processed. Results
can be obtained by calling the get_scene_list() method afterwards.

Arguments:
    frame_source (scenedetect.VideoManager or cv2.VideoCapture):  A source of
        frames to process (using frame_source.read() as in VideoCapture).
        VideoManager is preferred as it allows concatenation of multiple videos
        as well as seeking, by defining start time and end time/duration.
    start_time (int or FrameTimecode): Time/frame the passed frame_source object
        is currently at in time (i.e. the frame # read() will return next).
        Must be passed if the frame_source has been seeked past frame 0
        (i.e. calling set_duration on a VideoManager or seeking a VideoCapture).
    end_time (int or FrameTimecode): Maximum number of frames to detect
        (set to None to detect all available frames). Only needed for OpenCV
        VideoCapture objects, as VideoManager allows set_duration.
    frame_skip (int): Number of frames to skip (i.e. process every 1 in N+1
        frames, where N is frame_skip, processing only 1/N+1 percent of the
        video, speeding up the detection time at the expense of accuracy).
    show_progress (bool): If True, and the tqdm module is available, displays
        a progress bar with the progress, framerate, and expected time to
        complete processing the video frame source.
Returns:
    Number of frames read and processed from the frame source.
Raises:
    ValueError


# `scenedetect.video_manager` (`VideoManager`)

PySceneDetect scenedetect.video_manager Module

This file contains the VideoManager class, which provides a consistent
interface to reading videos.

This module includes both single-threaded (VideoManager) and asynchronous
(VideoManagerAsync) video manager classes, which can be used to pass a
video (or sequence of videos) and a start and end time/duration to a
SceneManager object for performing scene detection analysis.

The VideoManager class attempts to emulate some methods of the OpenCV
cv2.VideoCapture object, and can be used interchangably with one with
respect to a SceneManager object.

<h2 id="scenedetect.video_manager.VideoOpenFailure">VideoOpenFailure</h2>

```python
VideoOpenFailure(self, file_list=None, message='OpenCV VideoCapture object failed to return True when calling isOpened().')
```
VideoOpenFailure: Raised when an OpenCV VideoCapture object fails to open (i.e. calling
the isOpened() method returns a non True value).
<h2 id="scenedetect.video_manager.VideoFramerateUnavailable">VideoFramerateUnavailable</h2>

```python
VideoFramerateUnavailable(self, file_name=None, file_path=None, message='OpenCV VideoCapture object failed to return framerate when calling get(cv2.CAP_PROP_FPS).')
```
VideoFramerateUnavailable: Raised when the framerate cannot be determined from the video,
and the framerate has not been overriden/forced in the VideoManager.
<h2 id="scenedetect.video_manager.VideoParameterMismatch">VideoParameterMismatch</h2>

```python
VideoParameterMismatch(self, file_list=None, message='OpenCV VideoCapture object parameters do not match.')
```
VideoParameterMismatch: Raised when opening multiple videos with a VideoManager, and some
of the video parameters (frame height, frame width, and framerate/FPS) do not match.
<h2 id="scenedetect.video_manager.VideoDecodingInProgress">VideoDecodingInProgress</h2>

```python
VideoDecodingInProgress(self, /, *args, **kwargs)
```
VideoDecodingInProgress: Raised when attempting to call certain VideoManager methods that
must be called *before* start() has been called.
<h2 id="scenedetect.video_manager.VideoDecoderNotStarted">VideoDecoderNotStarted</h2>

```python
VideoDecoderNotStarted(self, /, *args, **kwargs)
```
VideoDecodingInProgress: Raised when attempting to call certain VideoManager methods that
must be called *after* start() has been called.
<h2 id="scenedetect.video_manager.InvalidDownscaleFactor">InvalidDownscaleFactor</h2>

```python
InvalidDownscaleFactor(self, /, *args, **kwargs)
```
InvalidDownscaleFactor: Raised when trying to set invalid downscale factor,
i.e. the supplied downscale factor was not a positive integer greater than zero.
<h2 id="scenedetect.video_manager.compute_downscale_factor">compute_downscale_factor</h2>

```python
compute_downscale_factor(frame_width)
```
Compute Downscale Factor: Returns the optimal default downscale factor based on
a video's resolution (specifically, the width parameter).

Returns:
    int: The defalt downscale factor to use with a video of frame_height x frame_width.

<h2 id="scenedetect.video_manager.get_video_name">get_video_name</h2>

```python
get_video_name(video_file)
```
Get Video Name: Returns a string representing the video file/device name.

Returns:
    str: Video file name or device ID. In the case of a video, only the file
        name is returned, not the whole path. For a device, the string format
        is 'Device 123', where 123 is the integer ID of the capture device.

<h2 id="scenedetect.video_manager.get_num_frames">get_num_frames</h2>

```python
get_num_frames(cap_list)
```
Get Number of Frames: Returns total number of frames in the cap_list.

Calls get(CAP_PROP_FRAME_COUNT) and returns the sum for all VideoCaptures.

<h2 id="scenedetect.video_manager.open_captures">open_captures</h2>

```python
open_captures(video_files, framerate=None, validate_parameters=True)
```
Open Captures - helper function to open all capture objects, set the framerate,
and ensure that all open captures have been opened and the framerates match on a list
of video file paths, or a list containing a single device ID.

Arguments:
    video_files (list of str(s)/int): A list of one or more paths (str), or a list
        of a single integer device ID, to open as an OpenCV VideoCapture object.
        A ValueError will be raised if the list does not conform to the above.
    framerate (float, optional): Framerate to assume when opening the video_files.
        If not set, the first open video is used for deducing the framerate of
        all videos in the sequence.
    validate_parameters (bool, optional): If true, will ensure that the frame sizes
        (width, height) and frame rate (FPS) of all passed videos is the same.
        A VideoParameterMismatch is raised if the framerates do not match.

Returns:
    A tuple of form (cap_list, framerate, framesize) where cap_list is a list of open
    OpenCV VideoCapture objects in the same order as the video_files list, framerate
    is a float of the video(s) framerate(s), and framesize is a tuple of (width, height)
    where width and height are integers representing the frame size in pixels.

Raises:
    ValueError, IOError, VideoFramerateUnavailable, VideoParameterMismatch

<h2 id="scenedetect.video_manager.release_captures">release_captures</h2>

```python
release_captures(cap_list)
```
Close Captures:  Calls the release() method on every capture in cap_list.
<h2 id="scenedetect.video_manager.close_captures">close_captures</h2>

```python
close_captures(cap_list)
```
Close Captures:  Calls the close() method on every capture in cap_list.
<h2 id="scenedetect.video_manager.validate_capture_framerate">validate_capture_framerate</h2>

```python
validate_capture_framerate(video_names, cap_framerates, framerate=None)
```
Validate Capture Framerate: Ensures that the passed capture framerates are valid and equal.

Raises:
    ValueError, TypeError, VideoFramerateUnavailable

<h2 id="scenedetect.video_manager.validate_capture_parameters">validate_capture_parameters</h2>

```python
validate_capture_parameters(video_names, cap_frame_sizes, check_framerate=False, cap_framerates=None)
```
Validate Capture Parameters: Ensures that all passed capture frame sizes and (optionally)
framerates are equal.  Raises VideoParameterMismatch if there is a mismatch.

Raises:
    VideoParameterMismatch

<h2 id="scenedetect.video_manager.VideoManager">VideoManager</h2>

```python
VideoManager(self, video_files, framerate=None, logger=None)
```
Provides a cv2.VideoCapture-like interface to a set of one or more video files,
or a single device ID. Supports seeking and setting end time/duration.
<h3 id="scenedetect.video_manager.VideoManager.set_downscale_factor">set_downscale_factor</h3>

```python
VideoManager.set_downscale_factor(self, downscale_factor=None)
```
Set Downscale Factor - sets the downscale/subsample factor of returned frames.

If N is the downscale_factor, the size of the frames returned becomes
frame_width/N x frame_height/N via subsampling.

If downscale_factor is None, the downscale factor is computed automatically
based on the current video's resolution.  A downscale_factor of 1 indicates
no downscaling.

<h3 id="scenedetect.video_manager.VideoManager.get_num_videos">get_num_videos</h3>

```python
VideoManager.get_num_videos(self)
```
Get Number of Videos - returns the length of the capture list (self._cap_list),
representing the number of videos the VideoManager has opened.
Returns:
    (int) Number of videos, equal to length of capture list.

<h3 id="scenedetect.video_manager.VideoManager.get_video_paths">get_video_paths</h3>

```python
VideoManager.get_video_paths(self)
```
Get Video Paths - returns list of strings containing paths to the open video(s).
Returns:
    (List[str]) List of paths to the video files opened by the VideoManager.

<h3 id="scenedetect.video_manager.VideoManager.get_framerate">get_framerate</h3>

```python
VideoManager.get_framerate(self)
```
Get Framerate - returns the framerate the VideoManager is assuming for all
open VideoCaptures.  Obtained from either the capture itself, or the passed
framerate parameter when the VideoManager object was constructed.
Returns:
    (float) Framerate, in frames/sec.

<h3 id="scenedetect.video_manager.VideoManager.get_base_timecode">get_base_timecode</h3>

```python
VideoManager.get_base_timecode(self)
```
Get Base Timecode - returns a FrameTimecode object at frame 0 / time 00:00:00.

The timecode returned by this method can be used to perform arithmetic (e.g.
addition), passing the resulting values back to the VideoManager (e.g. for the
set_duration() method), as the framerate of the returned FrameTimecode object
matches that of the VideoManager.

As such, this method is equivalent to creating a FrameTimecode at frame 0 with
the VideoManager framerate, for example, given a VideoManager called obj,
the following expression will evaluate as True:
    obj.get_base_timecode() == FrameTimecode(0, obj.get_framerate())

Furthermore, the base timecode object returned by a particular VideoManager
should not be passed to another one, unless you first verify that their
framerates are the same.

Returns:
    FrameTimecode object set to frame 0/time 00:00:00 with the video(s) framerate.

<h3 id="scenedetect.video_manager.VideoManager.get_current_timecode">get_current_timecode</h3>

```python
VideoManager.get_current_timecode(self)
```
Get Current Timecode - returns a FrameTimecode object at current VideoManager position.

Returns:
    FrameTimecode object at the current VideoManager position with the video(s) framerate.

<h3 id="scenedetect.video_manager.VideoManager.get_framesize">get_framesize</h3>

```python
VideoManager.get_framesize(self)
```
Get Frame Size - returns the frame size of the video(s) open in the
VideoManager's capture objects.

Returns:
    Tuple[int, int]: Video frame size in the form (width, height) where width
        and height represent the size of the video frame in pixels.

<h3 id="scenedetect.video_manager.VideoManager.get_framesize_effective">get_framesize_effective</h3>

```python
VideoManager.get_framesize_effective(self)
```
Get Frame Size - returns the frame size of the video(s) open in the
VideoManager's capture objects, divided by the current downscale factor.

Returns:
    Tuple[int, int]: Video frame size in the form (width, height) where width
        and height represent the size of the video frame in pixels.

<h3 id="scenedetect.video_manager.VideoManager.set_duration">set_duration</h3>

```python
VideoManager.set_duration(self, duration=None, start_time=None, end_time=None)
```
Set Duration - sets the duration/length of the video(s) to decode, as well as
the start/end times.  Must be called before start() is called, otherwise a
VideoDecodingInProgress exception will be thrown.  May be called after reset()
as well.

Arguments:
    duration (Optional[FrameTimecode]): The (maximum) duration in time to
        decode from the opened video(s). Mutually exclusive with end_time
        (i.e. if duration is set, end_time must be None).
    start_time (Optional[FrameTimecode]): The time/first frame at which to
        start decoding frames from. If set, the input video(s) will be
        seeked to when start() is called, at which point the frame at
        start_time can be obtained by calling retrieve().
    end_time (Optional[FrameTimecode]): The time at which to stop decoding
        frames from the opened video(s). Mutually exclusive with duration
        (i.e. if end_time is set, duration must be None).

Raises:
    VideoDecodingInProgress

<h3 id="scenedetect.video_manager.VideoManager.start">start</h3>

```python
VideoManager.start(self)
```
Start - starts video decoding and seeks to start time.  Raises
exception VideoDecodingInProgress if the method is called after the
decoder process has already been started.

Raises:
    VideoDecodingInProgress

<h3 id="scenedetect.video_manager.VideoManager.seek">seek</h3>

```python
VideoManager.seek(self, timecode)
```
Seek - seeks forwards to the passed timecode.

Only supports seeking forwards (i.e. timecode must be greater than the
current VideoManager position).  Can only be used after the start()
method has been called.

Arguments:
    timecode (FrameTimecode): Time in video to seek forwards to.

Returns:
    True if seeking succeeded, False if no more frames / end of video.

Raises:
    VideoDecoderNotStarted

<h3 id="scenedetect.video_manager.VideoManager.release">release</h3>

```python
VideoManager.release(self)
```
Release (cv2.VideoCapture method), releases all open capture(s).
<h3 id="scenedetect.video_manager.VideoManager.reset">reset</h3>

```python
VideoManager.reset(self)
```
Reset - Reopens captures passed to the constructor of the VideoManager.

Can only be called after the release method has been called.

Raises:
    VideoDecodingInProgress

<h3 id="scenedetect.video_manager.VideoManager.get">get</h3>

```python
VideoManager.get(self, capture_prop, index=None)
```
Get (cv2.VideoCapture method) - obtains capture properties from the current
VideoCapture object in use.  Index represents the same index as the original
video_files list passed to the constructor.  Getting/setting the position (POS)
properties has no effect; seeking is implemented using VideoDecoder methods.

Note that getting the property CAP_PROP_FRAME_COUNT will return the integer sum of
the frame count for all VideoCapture objects if index is not specified (or is None),
otherwise the frame count for the given VideoCapture index is returned instead.

Arguments:
    capture_prop: OpenCV VideoCapture property to get (i.e. CAP_PROP_FPS).
    index (optional): Index in file_list of capture to get property from (default
        is zero). Index is not checked and will raise exception if out of bounds.

Returns:
    Return value from calling get(property) on the VideoCapture object.

<h3 id="scenedetect.video_manager.VideoManager.grab">grab</h3>

```python
VideoManager.grab(self)
```
Grab (cv2.VideoCapture method) - retrieves a frame but does not return it.

Returns:
    bool: True if a frame was grabbed, False otherwise.

Raises:
    VideoDecoderNotStarted

<h3 id="scenedetect.video_manager.VideoManager.retrieve">retrieve</h3>

```python
VideoManager.retrieve(self)
```
Retrieve (cv2.VideoCapture method) - retrieves and returns a frame.

Frame returned corresponds to last call to get().

Returns:
    Tuple[bool, Union[None, numpy.ndarray]]: Returns tuple of
        (True, frame_image) if a frame was grabbed during the last call
        to grab(), and where frame_image is a numpy ndarray of the
        decoded frame, otherwise returns (False, None).

Raises:
    VideoDecoderNotStarted

<h3 id="scenedetect.video_manager.VideoManager.read">read</h3>

```python
VideoManager.read(self)
```
Read (cv2.VideoCapture method) - retrieves and returns a frame.

Returns:
    Tuple[bool, Union[None, numpy.ndarray]]: Returns tuple of
        (True, frame_image) if a frame was grabbed, where frame_image
        is a numpy ndarray of the decoded frame, otherwise (False, None).

Raises:
    VideoDecoderNotStarted


# `scenedetect.stats_manager` (`StatsManager`)

PySceneDetect scenedetect.stats_manager Module

This file contains the StatsManager class, which provides a key-value store for
each SceneDetector to read/write the metrics calculated for each frame.
The StatsManager must be registered to a SceneManager by passing it to the
SceneManager's constructor.

The entire StatsManager can be saved to and loaded from a human-readable CSV file,
also allowing both precise determination of the threshold or other optimal values
for video files.

The StatsManager can also be used to cache the calculation results of the scene
detectors being used, speeding up subsequent scene detection runs using the
same pair of SceneManager/StatsManager objects.

<h2 id="scenedetect.stats_manager.FrameMetricRegistered">FrameMetricRegistered</h2>

```python
FrameMetricRegistered(self, metric_key, message='Attempted to re-register frame metric key.')
```
Raised when attempting to register a frame metric key which has
already been registered.
<h2 id="scenedetect.stats_manager.FrameMetricNotRegistered">FrameMetricNotRegistered</h2>

```python
FrameMetricNotRegistered(self, metric_key, message='Attempted to get/set frame metrics for unregistered metric key.')
```
Raised when attempting to call get_metrics(...)/set_metrics(...) with a
frame metric that does not exist, or has not been registered.
<h2 id="scenedetect.stats_manager.StatsFileCorrupt">StatsFileCorrupt</h2>

```python
StatsFileCorrupt(self, message='Could not load frame metric data data from passed CSV file.')
```
Raised when frame metrics/stats could not be loaded from a provided CSV file.
<h2 id="scenedetect.stats_manager.StatsFileFramerateMismatch">StatsFileFramerateMismatch</h2>

```python
StatsFileFramerateMismatch(self, base_timecode_fps, stats_file_fps, message='Framerate differs between stats file and base timecode.')
```
Raised when attempting to load a CSV file with a framerate that differs from
the current base timecode / VideoManager.
<h2 id="scenedetect.stats_manager.NoMetricsRegistered">NoMetricsRegistered</h2>

```python
NoMetricsRegistered(self, /, *args, **kwargs)
```
Raised when attempting to save a CSV file via save_to_csv(...) without any
frame metrics having been registered (i.e. no SceneDetector objects were added
to the owning SceneManager object, if any).
<h2 id="scenedetect.stats_manager.NoMetricsSet">NoMetricsSet</h2>

```python
NoMetricsSet(self, /, *args, **kwargs)
```
Raised if no frame metrics have been set via set_metrics(...) when attempting
to save the stats to a CSV file via save_to_csv(...). This may also indicate that
detect_scenes(...) was not called on the owning SceneManager object, if any.
<h2 id="scenedetect.stats_manager.StatsManager">StatsManager</h2>

```python
StatsManager(self)
```
Provides a key-value store for frame metrics/calculations which can be used
as a cache to speed up subsequent calls to a SceneManager's detect_scenes(...)
method. The statistics can be saved to a CSV file, and loaded from disk.

Analyzing a statistics CSV file is also very useful for finding the optimal
algorithm parameters for certain detection methods. Additionally, the data
may be plotted by a graphing module (e.g. matplotlib) by obtaining the
metric of interest for a series of frames by iteratively calling get_metrics(),
after having called the detect_scenes(...) method on the SceneManager object
which owns the given StatsManager instance.

<h3 id="scenedetect.stats_manager.StatsManager.register_metrics">register_metrics</h3>

```python
StatsManager.register_metrics(self, metric_keys)
```
Register Metrics

Register a list of metric keys that will be used by the detector.
Used to ensure that multiple detector keys don't overlap.

Raises:
    FrameMetricRegistered

<h3 id="scenedetect.stats_manager.StatsManager.get_metrics">get_metrics</h3>

```python
StatsManager.get_metrics(self, frame_number, metric_keys)
```
Get Metrics: Returns the requested statistics/metrics for a given frame.

Arguments:
    frame_number (int): Frame number to retrieve metrics for.
    metric_keys (List[str]): A list of metric keys to look up.

Returns:
    A list containing the requested frame metrics for the given frame number
    in the same order as the input list of metric keys. If a metric could
    not be found, None is returned for that particular metric.

<h3 id="scenedetect.stats_manager.StatsManager.set_metrics">set_metrics</h3>

```python
StatsManager.set_metrics(self, frame_number, metric_kv_dict)
```
Set Metrics: Sets the provided statistics/metrics for a given frame.

Arguments:
    frame_number (int): Frame number to retrieve metrics for.
    metric_kv_dict (Dict[str, metric]): A dict mapping metric keys to the
        respective integer/floating-point metric values to set.

<h3 id="scenedetect.stats_manager.StatsManager.metrics_exist">metrics_exist</h3>

```python
StatsManager.metrics_exist(self, frame_number, metric_keys)
```
Metrics Exist: Checks if the given metrics/stats exist for the given frame.

Returns:
    (bool) True if the given metric keys exist for the frame, False otherwise.

<h3 id="scenedetect.stats_manager.StatsManager.is_save_required">is_save_required</h3>

```python
StatsManager.is_save_required(self)
```
Is Save Required: Checks if the stats have been updated since loading.

Returns:
    (bool) True if there are frame metrics/statistics not yet written to disk,
        False otherwise.

<h3 id="scenedetect.stats_manager.StatsManager.save_to_csv">save_to_csv</h3>

```python
StatsManager.save_to_csv(self, csv_file, base_timecode, force_save=True)
```
Save To CSV: Saves all frame metrics stored in the StatsManager to a CSV file.

Arguments:
    csv_file: A file handle opened in write mode (e.g. open('...', 'w')).
    base_timecode: The base_timecode obtained from the frame source VideoManager.
        If using an OpenCV VideoCapture, create one using the video framerate by
        setting base_timecode=FrameTimecode(0, fps=video_framerate).
    force_save: If True, forcably writes metrics out even if there are no
        registered metrics or frame statistics. If False, a NoMetricsRegistered
        will be thrown if there are no registered metrics, and a NoMetricsSet
        exception will be thrown if is_save_required() returns False.

Raises:
    NoMetricsRegistered, NoMetricsSet

<h3 id="scenedetect.stats_manager.StatsManager.load_from_csv">load_from_csv</h3>

```python
StatsManager.load_from_csv(self, csv_file, base_timecode=None, reset_save_required=True)
```
Load From CSV: Loads all metrics stored in a CSV file into the StatsManager instance.

Arguments:
    csv_file: A file handle opened in read mode (e.g. open('...', 'r')).
    base_timecode: The base_timecode obtained from the frame source VideoManager.
        If using an OpenCV VideoCapture, create one using the video framerate by
        setting base_timecode=FrameTimecode(0, fps=video_framerate).
        If base_timecode is not set (i.e. is None), the framerate is not validated.
    reset_save_required: If True, clears the flag indicating that a save is required.

Returns:
    (Union[int, None]) Number of frames/rows read from the CSV file, or None if the
        input file was blank.

Raises:
    StatsFileCorrupt, StatsFileFramerateMismatch


# `scenedetect.video_splitter`

The `scenedetect.video_splitter` module contains functions to split videos with a scene list using
external tools (e.g. mkvmerge, ffmpeg).


<h2 id="scenedetect.video_splitter.is_mkvmerge_available">is_mkvmerge_available</h2>

```python
is_mkvmerge_available()
```
Is mkvmerge Available: Gracefully checks if mkvmerge command is available.

Returns:
    (bool) True if the mkvmerge command is available, False otherwise.

<h2 id="scenedetect.video_splitter.is_ffmpeg_available">is_ffmpeg_available</h2>

```python
is_ffmpeg_available()
```
Is ffmpeg Available: Gracefully checks if ffmpeg command is available.

Returns:
    (bool) True if the ffmpeg command is available, False otherwise.

<h2 id="scenedetect.video_splitter.split_video_mkvmerge">split_video_mkvmerge</h2>

```python
split_video_mkvmerge(input_video_paths, scene_list, output_file_prefix, video_name, suppress_output=False)
```
Calls the mkvmerge command on the input video(s), splitting it at the
passed timecodes, where each scene is written in sequence from 001.
<h2 id="scenedetect.video_splitter.split_video_ffmpeg">split_video_ffmpeg</h2>

```python
split_video_ffmpeg(input_video_paths, scene_list, output_file_template, video_name, arg_override='-c:v libx264 -preset fast -crf 21 -c:a copy', hide_progress=False, suppress_output=False)
```
Calls the ffmpeg command on the input video(s), generating a new video for
each scene based on the start/end timecodes.


