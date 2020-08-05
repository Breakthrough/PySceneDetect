

API Reference
----------------------------------------------------------

The complete PySceneDetect Python API reference can be found in the [PySceneDetect Manual](http://pyscenedetect-manual.readthedocs.io/) which is located at:

[http://pyscenedetect-manual.readthedocs.io/](http://pyscenedetect-manual.readthedocs.io/)


API Overview
==========================================================

There are three main modules:

 - `scenedetect` - main functionality, has imports for commonly used classes and detection algorithms
 - `scenedetect.detectors` - scene detection algorithms
 - `scenedetect.cli` - command-line specific functionality

Classes from main `scenedetect` module:

 - `FrameTimecode` - used to store timecodes as well as perform arithmetic on timecode values (addition/subtraction/comparison) with frame-accurate precision
 - `SceneManager` - high-level manager to coordinate SceneDetector, VideoManager, and optionally, StatsManager objects
 - `VideoManager` - used to load video(s) and provide seeking
 - `StatsManager` - used to store/cache frame metrics to speed up subsequent scene detection runs on the same video, and optionally, save/load to/from a CSV file
 - `SceneDetector` - base class used to implement detection algorithms (e.g. `ContentDetector`, `ThresholdDetector`)

SceneDetector objects available in the `scenedetect.detectors` module:

 - `ThresholdDetector` - detects fade-outs/fade-ins to/from black by looking at the intensity/brightness of the video
 - `ContentDetector` - detects scene cuts/content changes by converting the video to the HSV colourspace

 All functions are well documented with complete docstrs, and documentation can be found by calling help() from a Python REPL or browsing the complete PySceneDetect v0.5 API Reference below.  Also note that auto-generated documentation (via the `pydoc` command/module) can be generated.

The complete PySceneDetect Python API reference [can be found *here* (link).](https://pyscenedetect-manual.readthedocs.io/).

