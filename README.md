
![PySceneDetect](https://raw.githubusercontent.com/Breakthrough/PySceneDetect/master/docs/img/pyscenedetect_logo_small.png)
==========================================================
Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

[![Build Status](https://img.shields.io/github/actions/workflow/status/Breakthrough/PySceneDetect/build-linux.yml)](https://github.com/Breakthrough/PySceneDetect/actions)
[![PyPI Status](https://img.shields.io/pypi/status/scenedetect.svg)](https://pypi.python.org/pypi/scenedetect/)
[![PyPI Version](https://img.shields.io/pypi/v/scenedetect?color=blue)](https://pypi.python.org/pypi/scenedetect/)
[![PyPI License](https://img.shields.io/pypi/l/scenedetect.svg)](http://pyscenedetect.readthedocs.org/en/latest/copyright/)

----------------------------------------------------------

### Latest Release: v0.6.1 (November 28, 2022)

**Website**:  [scenedetect.com](http://www.scenedetect.com)

**Getting Started**: [Usage Example](https://scenedetect.com/en/latest/examples/usage-example/)

**Documentation**:  [manual.scenedetect.com](http://manual.scenedetect.com)

**Discord**: https://discord.gg/H83HbJngk7

----------------------------------------------------------

**Quick Install**:

    pip install scenedetect[opencv] --upgrade

Requires ffmpeg/mkvmerge for video splitting support. Windows builds (MSI installer/portable ZIP) can be found on [the download page](http://scenedetect.com/en/latest/download/).

----------------------------------------------------------

**Quick Start (Command Line)**:

Split the input video wherever a new scene is detected:

    scenedetect -i video.mp4 detect-adaptive split-video

Skip the first 10 seconds of the input video, and output a list of scenes to the terminal:

    scenedetect -i video.mp4 time -s 10s detect-adaptive list-scenes

Help:

    scenedetect help

You can find more examples [on the website](https://scenedetect.com/en/latest/examples/usage-example/) or [in the manual](https://scenedetect.com/projects/Manual/en/latest/cli/global_options.html).

**Quick Start (Python API)**:

To get started, there is a high level function in the library that performs content-aware scene detection on a video (try it from a Python prompt):

```python
from scenedetect import detect, ContentDetector
scene_list = detect('my_video.mp4', ContentDetector())
```

`scene_list` will now be a list containing the start/end times of all scenes found in the video.  There also exists a two-pass version `AdaptiveDetector` which handles fast camera movement better, and `ThresholdDetector` for handling fade out/fade in events.

Try calling `print(scene_list)`, or iterating over each scene:

```python
from scenedetect import detect, ContentDetector
scene_list = detect('my_video.mp4', ContentDetector())
for i, scene in enumerate(scene_list):
    print('    Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
        i+1,
        scene[0].get_timecode(), scene[0].get_frames(),
        scene[1].get_timecode(), scene[1].get_frames(),))
```

We can also split the video into each scene if `ffmpeg` is installed (`mkvmerge` is also supported):

```python
from scenedetect import detect, ContentDetector, split_video_ffmpeg
scene_list = detect('my_video.mp4', ContentDetector())
split_video_ffmpeg('my_video.mp4', scene_list)
```

For more advanced usage, the API is highly configurable, and can easily integrate with any pipeline. This includes using different detection algorithms, splitting the input video, and much more. The following example shows how to implement a function similar to the above, but using [the `scenedetect` API](https://scenedetect.com/projects/Manual/en/latest/api.html):

```python
from scenedetect import open_video, SceneManager, split_video_ffmpeg
from scenedetect.detectors import ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg

def split_video_into_scenes(video_path, threshold=27.0):
    # Open our video, create a scene manager, and add a detector.
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(threshold=threshold))
    scene_manager.detect_scenes(video, show_progress=True)
    scene_list = scene_manager.get_scene_list()
    split_video_ffmpeg(video_path, scene_list, show_progress=True)
```

See [the manual](https://scenedetect.com/projects/Manual/en/latest/api.html) for the
full PySceneDetect API documentation.

----------------------------------------------------------

PySceneDetect is a command-line tool and Python library, which uses OpenCV to analyze a video to find each shot change (or "cut"/"scene").  If `ffmpeg` or `mkvmerge` is installed, the video can also be split into scenes automatically.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.  See [the Usage documentation](https://scenedetect.com/en/latest/examples/usage/) for details.

There are two main detection methods PySceneDetect uses: `detect-threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `detect-adaptive` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

In general, use `detect-threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `detect-adaptive` or `detect-content` modes.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.

For help or other issues, you can join [the official PySceneDetect Discord Server](https://discord.gg/H83HbJngk7), submit an issue/bug report [here on Github](https://github.com/Breakthrough/PySceneDetect/issues), or contact me via [my website](http://www.bcastell.com/about/).


## Usage

 - [Basic Usage](https://scenedetect.com/en/latest/examples/usage/)
 - [PySceneDetect Manual](https://manual.scenedetect.com/), covers `scenedetect` command and Python API
 - [Example: Detecting and Splitting Scenes in Movie Clip](https://scenedetect.com/en/latest/examples/usage-example/)


## Features & Roadmap

You can [view the latest features and version roadmap on Readthedocs](http://pyscenedetect.readthedocs.org/en/latest/features/).
See [`docs/changelog.md`](https://github.com/Breakthrough/PySceneDetect/blob/master/docs/changelog.md) for a list of changes in each version, or visit [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) to download a specific version.  Feel free to submit any bugs/issues or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues).

Additional features being planned or in development can be found [here (tagged as `feature`) in the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3Afeature).  You can also find additional information about PySceneDetect at [http://www.bcastell.com/projects/PySceneDetect/](http://www.bcastell.com/projects/PySceneDetect/).


## Code Signing

This program uses free code signing provided by [SignPath.io](https://signpath.io?utm_source=foundation&utm_medium=github&utm_campaign=PySceneDetect), and a free code signing certificate by the [SignPath Foundation](https://signpath.org?utm_source=foundation&utm_medium=github&utm_campaign=PySceneDetect)


## License

Licensed under BSD 3-Clause (see the `LICENSE` file for details).

Copyright (C) 2014-2022 Brandon Castellano.
All rights reserved.
