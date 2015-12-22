

PySceneDetect
==========================================================
Video Scene Detection and Analysis Tool
----------------------------------------------------------

PySceneDetect is a command-line tool, written in Python and using OpenCV, which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with another tool (e.g. `mkvmerge`, `ffmpeg`) to split the video into individual clips.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.

Note that PySceneDetect is currently in alpha; see Current Features & Roadmap below for details.  For help or other issues, you can visit #pyscenedetect on Freenode, or contact me on [my website](http://www.bcastell.com/about/).  Feel free to submit any bugs or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues) here on Github.  Development right now is a tad slow as I'm nearing the completion of my thesis, but should resume to a normal pace early in the new year (January 2016).


Download & Requirements
----------------------------------------------------------

The latest version of PySceneDetect (`v0.2.4-alpha`) can be [downloaded here](https://github.com/Breakthrough/PySceneDetect/releases); to run it, you will need:

 - [Python 2 / 3](https://www.python.org/) (tested on 2.7.X, untested but should work on 3.X)
 - OpenCV Python Module (usually found in Linux package repos as `python-opencv`, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://sourceforge.net/projects/numpy/)

To ensure you have all the requirements, open a `python` interpreter, and ensure you can `import numpy` and `import cv2` without any errors.  You can download a test video and view the expected output [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests) (see the end of the Usage section below for details).


Usage
----------------------------------------------------------

To run PySceneDetect, you can invoke `python scenedetect.py` or `./scenedetect.py` directly.  To display the help file, detailing usage parameters:

    ./scenedetect.py --help

To perform threshold-based analysis with the default parameters, on a video named `myvideo.mp4`, saving a list of scenes to `myvideo_scenes.csv` (they are also printed to the terminal):

    ./scenedetect.py --input myvideo.mp4 --output myvideo_scenes.csv

To perform threshold-based analysis, with a threshold intensity of 16, and a match percent of 90:

    ./scenedetect.py --input myvideo.mp4 --threshold 16 --minpercent 90

Detailed descriptions of the above parameters, as well as their default values, can be obtained by using the `--help` flag.

Below is a visual example of the parameters used in threshold mode (click for full-view):

[<img src="https://github.com/Breakthrough/PySceneDetect/raw/resources/images/threshold-param-example.png" alt="parameters in threshold mode" width="360" />](https://github.com/Breakthrough/PySceneDetect/raw/resources/images/threshold-param-example.png)

You can download the file `testvideo.mp4`, as well as the expected output `testvideo-results.txt`, [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests), for testing the operation of the program.  Data for the above graph was obtained by running PySceneDetect on `testvideo.mp4` in statistics mode (by specifying the `-s` argument).


Current Features & Roadmap
----------------------------------------------------------

See [`CHANGELOG.md`](https://github.com/Breakthrough/PySceneDetect/blob/master/CHANGELOG.md) for a list of changes in each version, or visit [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) to download a specific version.  Feel free to submit any bugs/issues or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues).

### Current Features

 - analyzes passed video file for changes in intensity/content (currently based on mean pixel value/brightness)
 - detects fade-in and fade-out based on user-defined threshold
 - exports list of scenes to .CSV file (both timecodes and frame numbers) (`-o`)
 - exports timecodes in `mkvmerge` format: `HH:MM:SS.nnnnn`, comma-separated
 - statistics/analysis mode to export frame-by-frame video metrics (`-s`)

### In Progress

 - add output-suppression mode for better automation with external scripts/programs
 - content-aware scene detection based on changes in the HSV color space 
 - adaptive or user-defined bias for fade in/out interpolation

### Planned Features

 - export scenes in chapter/XML format
 - improve robustness of content-aware detection by combining with edge detection (similar to [MATLAB-based scene change detector](http://www.mathworks.com/help/vision/examples/scene-change-detection.html))
 - additional timecode formats
 - interactive/guided mode, eventually moving to a graphical interface


You can find additional information regarding PySceneDetect at the following URL:
http://www.bcastell.com/projects/pyscenedetect/


----------------------------------------------------------

Licensed under BSD 2-Clause (see the `LICENSE` file for details).

Copyright (C) 2013-2014 Brandon Castellano.
All rights reserved.

