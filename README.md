

PySceneDetect
==========================================================
A Python/OpenCV-Based Video Scene Cut Detector
----------------------------------------------------------

PySceneDetect is a command-line tool which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with antoher tool (e.g. `ffmpeg`, `mkvmerge`) to split the video up into individual clips.  Note that PySceneDetect is currently in *alpha* and under heavy development - see the current status section below for details.


Installing & Requirements
----------------------------------------------------------

You can grab the latest release of [PySceneDetect from here](https://github.com/Breakthrough/PySceneDetect/releases).  To run PySceneDetect, you will need:

 - [Python 2/3](https://www.python.org/) (tested on 2.7.X, **untested** on 3.X)
 - OpenCV-Python Bindings (can usually be found in Linux package repos already, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://www.numpy.org/)

To ensure you have all the requirements, open a `python` interpreter, and ensure you can `import numpy` and `import cv2` without any errors.


Usage
----------------------------------------------------------

To run PySceneDetect, you can invoke `python scenedetect.py` or `./scenedetect.py` directly.  To display the help file, detailing usage parameters:

    ./scenedetect.py --help

To perform threshold-based analysis with the default parameters, on a video file named `myvideo.mp4`:

    ./scenedetect.py --input myvideo.mp4

To perform threshold-based analysis, with a threshold intensity of 16, and a match percent of 90:

    ./scenedetect.py --input myvideo.mp4 --threshold 16 --minpercent 90

Detailed descriptions of the above parameters, as well as their default values, can be obtained by using the `--help` flag.


Current Status / Known Issues
-----------------------------

As of version `0.1.0-alpha`, although fade in/outs are detected in videos, they are not interpolated into scenes.  In addition, the results are displayed to `stdout`, and not in any particular timecode format.  These issues will be addressed in the following version, before moving towards content-aware scene detection.

### Immediate Work

 - allow specification of an output file
 - export timecodes in multiple formats to match popular applications
 - interpolate between fade in/outs to determine approximate scene cut time

### Future Plans

 - export scenes in chapter/XML format
 - adaptive or user-defined bias for fade in/out interpolation
 - content-aware scene detection


You can find additional information regarding PySceneDetect at the following URL:
http://www.bcastell.com/projects/pyscenedetect/

----------------------------------------------------------

Licensed under BSD 2-Clause (see the `LICENSE` file for details).

Copyright (C) 2013-2014 Brandon Castellano.
All rights reserved.
