

PySceneDetect
==========================================================
Video Scene Detection and Analysis Tool
----------------------------------------------------------

PySceneDetect is a command-line tool, written in Python and using OpenCV, which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with another tool (e.g. `ffmpeg`, `mkvmerge`) to split the video into individual clips.  A frame-by-frame analysis can also be generated, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.

Note that PySceneDetect is currently in alpha (see Current Status below for details).


Download & Requirements
----------------------------------------------------------

You can download [PySceneDetect from here](https://github.com/Breakthrough/PySceneDetect/releases); to run it, you will need:

 - [Python 2 / 3](https://www.python.org/) (tested on 2.7.X, untested but should work on 3.X)
 - OpenCV Python Module (can usually be found in Linux package repos already, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://sourceforge.net/projects/numpy/)

To ensure you have all the requirements, open a `python` interpreter, and ensure you can `import numpy` and `import cv2` without any errors.


Usage
----------------------------------------------------------

To run PySceneDetect, you can invoke `python scenedetect.py` or `./scenedetect.py` directly.  To display the help file, detailing usage parameters:

    ./scenedetect.py --help

To perform threshold-based analysis with the default parameters, on a video named `myvideo.mp4`, saving a list of scenes to `myvideo_scenes.csv` (they are also printed to the terminal):

    ./scenedetect.py --input myvideo.mp4 --output myvideo_scenes.csv

To perform threshold-based analysis, with a threshold intensity of 16, and a match percent of 90:

    ./scenedetect.py --input myvideo.mp4 --threshold 16 --minpercent 90

Detailed descriptions of the above parameters, as well as their default values, can be obtained by using the `--help` flag.  Visual example of the parameters used in threshold mode:

![parameters in threshold mode](https://github.com/Breakthrough/PySceneDetect/raw/resources/images/threshold-param-example.png)

You can download the file `testvideo.mp4` as well as the expected output `testvideo-results.txt` [from here](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests).


Current Status
----------------------------------------------------------

See [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) for a list of all versions, changes, and download links.  The latest stable release of PySceneDetect is `v0.2.0-alpha`.

### Current Features

 - analyzes passed video file for changes in intensity/content (currently based on mean pixel value/brightness)
 - detects fade-in and fade-out based on user-defined threshold
 - exports list of scenes to .CSV file (both timecodes and frame numbers)

### In Process

 - export timecodes in multiple formats to match popular applications
     - `mkvmerge` format: `HH:MM:SS.nnnnn`, comma-separated
 - adaptive or user-defined bias for fade in/out interpolation

### Planned Features

 - export scenes in chapter/XML format
 - content-aware scene detection


You can find additional information regarding PySceneDetect at the following URL:
http://www.bcastell.com/projects/pyscenedetect/


----------------------------------------------------------

Licensed under BSD 2-Clause (see the `LICENSE` file for details).

Copyright (C) 2013-2014 Brandon Castellano.
All rights reserved.

