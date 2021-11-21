
![PySceneDetect](https://raw.githubusercontent.com/Breakthrough/PySceneDetect/master/docs/img/pyscenedetect_logo_small.png)
==========================================================
Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

[![Build Status](https://img.shields.io/travis/com/Breakthrough/PySceneDetect/master)](https://travis-ci.com/github/Breakthrough/PySceneDetect) [![PyPI Status](https://img.shields.io/pypi/status/scenedetect.svg)](https://pypi.python.org/pypi/scenedetect/) [![LGTM Analysis](https://img.shields.io/lgtm/grade/python/github/Breakthrough/PySceneDetect.svg)](https://lgtm.com/projects/g/Breakthrough/PySceneDetect) [![PyPI Version](https://img.shields.io/pypi/v/scenedetect?color=blue)](https://pypi.python.org/pypi/scenedetect/)  [![PyPI License](https://img.shields.io/pypi/l/scenedetect.svg)](http://pyscenedetect.readthedocs.org/en/latest/copyright/)


### Latest Release: v0.5.6.1 (October 11, 2021)

**Main Webpage**:  [py.scenedetect.com](http://py.scenedetect.com)

**Documentation**:  [manual.scenedetect.com](http://manual.scenedetect.com)

**Discord**: https://discord.gg/H83HbJngk7

----------------------------------------------------------

**Quick Install**: To install PySceneDetect via `pip` with all dependencies:

    pip install scenedetect[opencv]

For servers, you can use the headless (non-GUI) version of OpenCV by installing `scenedetect[opencv-headless]`.  To enable video splitting support, you will also need to have `mkvmerge` or `ffmpeg` installed - see the documentation on [Video Splitting Support](https://pyscenedetect.readthedocs.io/en/latest/examples/video-splitting/) for details.

Requires Python modules `click`, `numpy`, OpenCV `cv2`, and (optional) `tqdm` for displaying progress.  For details, see the [dependencies on the downloads page](https://pyscenedetect.readthedocs.io/en/latest/download/#dependencies).

----------------------------------------------------------

**Quick Start (Command Line)**:

Split the input video wherever a new scene is detected:

    scenedetect -i video.mp4 detect-content split-video

Skip the first 10 seconds of the input video, and output a list of scenes to the terminal:

    scenedetect -i video.mp4 time -s 10s detect-content list-scenes

To show a summary of all other options and commands:

    scenedetect help

You can find more examples [on the website](https://pyscenedetect.readthedocs.io/en/latest/examples/usage-example/) or [in the manual](https://pyscenedetect.readthedocs.io/projects/Manual/en/latest/cli/global_options.html).

**Quick Start (Python API)**:

In the code example below, we create a function `find_scenes()` which will
load a video, detect the scenes, and return a list of tuples containing the
(start, end) timecodes of each detected scene.  Note that you can modify
the `threshold` argument to modify the sensitivity of the scene detection.

```python
# Standard PySceneDetect imports:
from scenedetect import VideoManager
from scenedetect import SceneManager

# For content-aware scene detection:
from scenedetect.detectors import ContentDetector

def find_scenes(video_path, threshold=30.0):
    # Create our video & scene managers, then add the detector.
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(threshold=threshold))

    # Improve processing speed by downscaling before processing.
    video_manager.set_downscale_factor()

    # Start the video manager and perform the scene detection.
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    # Each returned scene is a tuple of the (start, end) timecode.
    return scene_manager.get_scene_list()
```

To get started, try printing the result from calling `find_scenes` on a small video clip:

```python
    scenes = find_scenes('video.mp4')
    print(scenes)
```

See [the manual](https://pyscenedetect.readthedocs.io/projects/Manual/en/latest/api.html) for the full PySceneDetect API documentation.

----------------------------------------------------------

PySceneDetect is a command-line tool and Python library, which uses OpenCV to analyze a video to find each shot change (or "cut"/"scene").  If `ffmpeg` or `mkvmerge` is installed, the video can also be split into scenes automatically.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.  See [the Usage documentation](https://pyscenedetect.readthedocs.io/en/latest/examples/usage/) for details.

There are two main detection methods PySceneDetect uses: `detect-threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `detect-content` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

In general, use `detect-threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `detect-content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.

Note that PySceneDetect is currently in beta; see Current Features & Roadmap below for details.  For help or other issues, you can join [the official PySceneDetect Discord Server](https://discord.gg/H83HbJngk7), submit an issue/bug report [here on Github](https://github.com/Breakthrough/PySceneDetect/issues), or contact me via [my website](http://www.bcastell.com/about/).


Usage
----------------------------------------------------------

 - [Basic Usage](https://pyscenedetect.readthedocs.io/en/latest/examples/usage/)
 - [PySceneDetect Manual](https://pyscenedetect-manual.readthedocs.io/en/latest/), covers `scenedetect` command and Python API
 - [Example: Detecting and Splitting Scenes in Movie Clip](https://pyscenedetect.readthedocs.io/en/latest/examples/usage-example/)


Current Features & Roadmap
----------------------------------------------------------

You can [view the latest features and version roadmap on Readthedocs](http://pyscenedetect.readthedocs.org/en/latest/features/).
See [`docs/changelog.md`](https://github.com/Breakthrough/PySceneDetect/blob/master/docs/changelog.md) for a list of changes in each version, or visit [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) to download a specific version.  Feel free to submit any bugs/issues or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues).

Additional features being planned or in development can be found [here (tagged as `feature`) in the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3Afeature).  You can also find additional information about PySceneDetect at [http://www.bcastell.com/projects/PySceneDetect/](http://www.bcastell.com/projects/PySceneDetect/).


----------------------------------------------------------

Licensed under BSD 3-Clause (see the `LICENSE` file for details).

Copyright (C) 2014-2021 Brandon Castellano.
All rights reserved.

