      
PySceneDetect
==========================================================
Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

[![Documentation Status](https://readthedocs.org/projects/pyscenedetect/badge/?version=latest)](http://pyscenedetect.readthedocs.org/en/latest/?badge=latest)

### New Release: v0.3-beta (Jan. 8, 2016)!

PySceneDetect is finally out of alpha, and is finally in the first beta release ([get it here!](https://github.com/Breakthrough/PySceneDetect/releases)).  This release brings a number of major changes, including the much awaited content-aware detection mode (see [`docs/changelog.md`](https://github.com/Breakthrough/PySceneDetect/blob/master/docs/changelog.md) or [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) for details.).  Also see [the new `USAGE.md` file](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) for details on the new detection modes, default values/thresholds to try, and how to effectively choose the optimal detection parameters.

More complete documentation, as well as a new main page for PySceneDetect can be found on Readthedocs at:

http://pyscenedetect.readthedocs.org/

----------------------------------------------------------

PySceneDetect is a command-line tool, written in Python and using OpenCV, which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with another tool (e.g. `mkvmerge`, `ffmpeg`) to split the video into individual clips.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.  See [the `USAGE.md` file](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) for details.

There are two main detection methods PySceneDetect uses: `threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `content` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

In general, use `threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.

Note that PySceneDetect is currently in beta; see Current Features & Roadmap below for details.  For help or other issues, you can contact me on [my website](http://www.bcastell.com/about/), or we can chat in #pyscenedetect on Freenode.  Feel free to submit any bugs or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues) here on Github.


Download & Requirements
----------------------------------------------------------

The latest version of PySceneDetect (`v0.3-beta`) can be [downloaded here](https://github.com/Breakthrough/PySceneDetect/releases); to run it, you will need:

 - [Python 2 / 3](https://www.python.org/) (tested on 2.7.X, untested but should work on 3.X)
 - OpenCV Python Module (usually found in Linux package repos as `python-opencv`, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://sourceforge.net/projects/numpy/)

To ensure you have all the requirements, open a `python` interpreter, and ensure you can `import numpy` and `import cv2` without any errors.  You can download a test video and view the expected output [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests) (see the end of the Usage section below for details).

Once this is done, [downloaded](https://github.com/Breakthrough/PySceneDetect/releases) and extract PySceneDetect.  To install PySceneDetect and allow you to use it system wide, use the following command (may require root/`sudo`):

    python setup.py install

After installation, you can use PySceneDetect as the `scenedetect` command from any command line.  To verify the installation, run the following command to display what version of PySceneDetect you have installed:

    scenedetect --version


Usage
----------------------------------------------------------

**There is now a dedicated [`USAGE.md` file (here)](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) containing more detailed usage instructions.**  To run PySceneDetect, use the `scenedetect` command if you have it installed to your system.  Otherwise, if you are running from source, you can invoke `python scenedetect.py` or `./scenedetect.py` (instead of `scenedetect` in the examples shown below and elsewhere).  To display the help file, detailing the command line parameters:

    scenedetect --help

To perform threshold-based analysis with the default parameters, on a video named `myvideo.mp4`, saving a list of scenes to `myvideo_scenes.csv` (they are also printed to the terminal):

    scenedetect --input myvideo.mp4 --output myvideo_scenes.csv

To perform content-based analysis, with a threshold intensity of 30:

    scenedetect --input myvideo.mp4 --detector content --threshold 16

To perform threshold-based analysis, with a threshold intensity of 16 and a match percent of 90:

    scenedetect --input myvideo.mp4 --detector threshold --threshold 16 --min-percent 90

Detailed descriptions of the above parameters, as well as their default values, can be obtained by using the `--help` flag.

Below is a visual example of the parameters used in threshold mode (click for full-view):

[<img src="https://github.com/Breakthrough/PySceneDetect/raw/resources/images/threshold-param-example.png" alt="parameters in threshold mode" width="360" />](https://github.com/Breakthrough/PySceneDetect/raw/resources/images/threshold-param-example.png)

You can download the file `testvideo.mp4`, as well as the expected output `testvideo-results.txt`, [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests), for testing the operation of the program.  Data for the above graph was obtained by running PySceneDetect on `testvideo.mp4` in statistics mode (by specifying the `-s` argument).


Current Features & Roadmap
----------------------------------------------------------

You can [view the latest features and version roadmap on Readthedocs](http://pyscenedetect.readthedocs.org/en/latest/features/).
See [`docs/changelog.md`](https://github.com/Breakthrough/PySceneDetect/blob/master/docs/changelog.md) for a list of changes in each version, or visit [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) to download a specific version.  Feel free to submit any bugs/issues or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues).

Additional features being planned or in development can be found [here (tagged as `feature`) in the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3Afeature).  You can also find additional information about PySceneDetect at [http://www.bcastell.com/projects/pyscenedetect/](http://www.bcastell.com/projects/pyscenedetect/).


----------------------------------------------------------

Licensed under BSD 2-Clause (see the `LICENSE` file for details).

Copyright (C) 2012-2016 Brandon Castellano.
All rights reserved.

