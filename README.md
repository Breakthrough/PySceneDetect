      
PySceneDetect
==========================================================
Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

[![Documentation Status](https://readthedocs.org/projects/pyscenedetect/badge/?version=latest)](http://pyscenedetect.readthedocs.org/en/latest/?badge=latest)

### New Release: v0.3-beta (Jan. 8, 2016)!

PySceneDetect is finally out of alpha, and is finally in the first beta release ([get it here!](https://github.com/Breakthrough/PySceneDetect/releases)).  This release brings a number of major changes, including the much awaited content-aware detection mode (see [`CHANGELOG.md`](https://github.com/Breakthrough/PySceneDetect/blob/master/CHANGELOG.md) or [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) for details.).  Also see [the new `USAGE.md` file](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) for details on the new detection modes, default values/thresholds to try, and how to effectively choose the optimal detection parameters.

----------------------------------------------------------

PySceneDetect is a command-line tool, written in Python and using OpenCV, which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with another tool (e.g. `mkvmerge`, `ffmpeg`) to split the video into individual clips.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.  See [the `USAGE.md` file](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) for details.

There are two main detection methods PySceneDetect uses: threshold (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and content (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

In general, use `threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.

Note that PySceneDetect is currently in beta; see Current Features & Roadmap below for details.  For help or other issues, you can contact me on [my website](http://www.bcastell.com/about/), or we can chat in #pyscenedetect on Freenode.  Feel free to submit any bugs or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues) here on Github.


Download & Requirements
----------------------------------------------------------

The latest version of PySceneDetect (`v0.3-beta`) can be [downloaded here](https://github.com/Breakthrough/PySceneDetect/releases); to run it, you will need:

 - [Python 2 / 3](https://www.python.org/) (tested on 2.7.X, untested but should work on 3.X)
 - OpenCV Python Module (usually found in Linux package repos as `python-opencv`, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://sourceforge.net/projects/numpy/)

To ensure you have all the requirements, open a `python` interpreter, and ensure you can `import numpy` and `import cv2` without any errors.  You can download a test video and view the expected output [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests) (see the end of the Usage section below for details).


Usage
----------------------------------------------------------

**There is now a dedicated [`USAGE.md` file (here)](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) containing more detailed usage instructions.**  To run PySceneDetect, you can invoke `python scenedetect.py` or `./scenedetect.py` directly.  To display the help file, detailing usage parameters:

    ./scenedetect.py --help

To perform threshold-based analysis with the default parameters, on a video named `myvideo.mp4`, saving a list of scenes to `myvideo_scenes.csv` (they are also printed to the terminal):

    ./scenedetect.py --input myvideo.mp4 --output myvideo_scenes.csv

To perform content-based analysis, with a threshold intensity of 30:

    ./scenedetect.py --input myvideo.mp4 --detector content --threshold 16

To perform threshold-based analysis, with a threshold intensity of 16 and a match percent of 90:

    ./scenedetect.py --input myvideo.mp4 --detector threshold --threshold 16 --min-percent 90

Detailed descriptions of the above parameters, as well as their default values, can be obtained by using the `--help` flag.

Below is a visual example of the parameters used in threshold mode (click for full-view):

[<img src="https://github.com/Breakthrough/PySceneDetect/raw/resources/images/threshold-param-example.png" alt="parameters in threshold mode" width="360" />](https://github.com/Breakthrough/PySceneDetect/raw/resources/images/threshold-param-example.png)

You can download the file `testvideo.mp4`, as well as the expected output `testvideo-results.txt`, [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests), for testing the operation of the program.  Data for the above graph was obtained by running PySceneDetect on `testvideo.mp4` in statistics mode (by specifying the `-s` argument).


Current Features & Roadmap
----------------------------------------------------------

See [`CHANGELOG.md`](https://github.com/Breakthrough/PySceneDetect/blob/master/CHANGELOG.md) for a list of changes in each version, or visit [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) to download a specific version.  Feel free to submit any bugs/issues or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues).

### Current Features

 - content-aware scene detection based on changes between frames in the HSV color space 
 - output-suppression (quiet) mode for better automation with external scripts/programs
 - threshold scene detection analyzes video for changes in average frame intensity/brightness
 - detects fade-in and fade-out based on user-defined threshold
 - exports list of scenes to .CSV file (both timecodes and frame numbers) (`-o`)
 - exports timecodes in `mkvmerge` format: `HH:MM:SS.nnnnn`, comma-separated
 - statistics/analysis mode to export frame-by-frame video metrics (`-s`)

### In Progress

 - adaptive or user-defined bias for fade in/out interpolation
 - additional timecode formats

### Planned Features

 - export scenes in chapter/XML format
 - improve robustness of content-aware detection by combining with edge detection (similar to [MATLAB-based scene change detector](http://www.mathworks.com/help/vision/examples/scene-change-detection.html))
 - interactive/guided mode, eventually moving to a graphical interface

Additional features being planned or in development can be found [here (tagged as `feature`) in the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3Afeature).  You can also find additional information about PySceneDetect at [http://www.bcastell.com/projects/pyscenedetect/](http://www.bcastell.com/projects/pyscenedetect/).


----------------------------------------------------------

Licensed under BSD 2-Clause (see the `LICENSE` file for details).

Copyright (C) 2013-2016 Brandon Castellano.
All rights reserved.

