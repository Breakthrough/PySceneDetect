

API Reference
----------------------------------------------------------

The complete PySceneDetect Python API reference can be found at the following URL:

[http://pyscenedetect-api.readthedocs.io/](http://pyscenedetect-api.readthedocs.io/)


API Overview
==========================================================

There are two main modules:

 - scenedetect
 - scenedetect.detectors

Classes from main `scenedetect` module:

 - FrameTimecode - used to store timecodes as well as perform arithmetic on timecode values (addition/subtraction/comparison) with frame-accurate precision
 - SceneManager - high-level manager to coordinate SceneDetector, VideoManager, and optionally, StatsManager objects
 - VideoManager - used to load video(s) and provide seeking
 - StatsManager - used to store/cache frame metrics to speed up subsequent scene detection runs on the same video, and optionally, save/load to/from a CSV file
 - SceneDetector - base class used to implement detection algorithms (e.g. ContentDetector, ThresholdDetector)

SceneDetector objects available in the `scenedetect.detectors` module:

 - ThresholdDetector - detects fade-outs/fade-ins to/from black by looking at the intensity/brightness of the video 
 - ContentDetector - detects scene cuts/content changes by converting the video to the HSV colourspace 

 All functions are well documented with complete docstrs, and documentation can be found by calling help() from a Python REPL or browsing the complete PySceneDetect v0.5 API Reference below.  Also note that auto-generated documentation (via the `pydoc` command/module) can be generated.
 
The complete PySceneDetect Python API reference [can be found *here* (link).](http://breakthrough.github.io/PySceneDetect/)

