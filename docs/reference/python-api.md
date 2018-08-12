
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

 All functions are well documented with complete docstrs, and documentation can be found by calling help() from a Python REPL or browsing the complete PySceneDetect v0.5 API Reference (coming soon).


API Reference
----------------------------------------------------------


The current API reference is incomplete, however, full docstrs (e.g. the `help` command in a Python REPL), or auto-generated documentation (via the `pydoc` command/module) can be generated.

To get started in the meantime, however, [see the `api_test.py` file](https://github.com/Breakthrough/PySceneDetect/blob/v0.5-beta-1/tests/api_test.py) for a complete example of performing scene detection using the PySceneDetect Python API.  Also use the built-in `help` command in the Python REPL on the various `scenedetect` module members to view the appropriate docstrs.

This page serves as a sort of stop-gap in the meantime, until the manual and automated processes can be bridged (if anyone has any suggestions on the best way to generate the Python documentation from the documentation string available, please feel free to suggest it by raising an issue).



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

TODO...



