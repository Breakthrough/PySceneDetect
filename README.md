
PySceneDetect
==========================================================
Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

[![Documentation Status](https://readthedocs.org/projects/pyscenedetect/badge/?version=latest)](http://pyscenedetect.readthedocs.org/en/latest/?badge=latest) [![PyPI Status](https://img.shields.io/pypi/status/PySceneDetect.svg)](https://pypi.python.org/pypi/PySceneDetect/) [![PyPI Version](https://img.shields.io/pypi/v/PySceneDetect.svg)](https://pypi.python.org/pypi/PySceneDetect/)  [![PyPI License](https://img.shields.io/pypi/l/PySceneDetect.svg)](http://pyscenedetect.readthedocs.org/en/latest/copyright/)


### Latest Release: v0.4 (January 14, 2017)

**New**: The latest version integrates with `mkvmerge` to automatically split the input video into individual clips.

There is also now an installer for Windows that automatically installs all dependencies and the `scenedetect` command system wide (64-bit only currently).  This is the recommended installation method for Windows users now, and it can be found on [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases).  The Windows builds do not require an existing Python environment, nor any other prerequisites.  There is also a portable .zip version available.

It is still recommended that both Linux and Mac users download the source distribution, following the installation instructions below.  

--------

Quick install; requires `numpy` and Python OpenCV `cv2` module, see [getting started guide](http://pyscenedetect.readthedocs.org/en/latest/examples/usage/) after install.  After installing the prerequisites, download the latest source distribution from [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases), extract the archive, and in a terminal/command prompt in the location of the extracted files, run:

    sudo python setup.py install

To test if you have the required prerequisites, open a `python` prompt, and run the following:

    import numpy
    import cv2

If both of those commands execute without any problems, you should be able to install PySceneDetect without any issues.  See [the new `USAGE.md` file](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) for details on the new detection modes, default values/thresholds to try, and how to effectively choose the optimal detection parameters.  Full documentation for PySceneDetect can be found on Readthedocs at http://pyscenedetect.readthedocs.org/

----------------------------------------------------------

PySceneDetect is a command-line tool, written in Python and using OpenCV, which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with another tool (e.g. `mkvmerge`, `ffmpeg`) to split the video into individual clips.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.  See [the `USAGE.md` file](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) for details.

There are two main detection methods PySceneDetect uses: `threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `content` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

In general, use `threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.

Note that PySceneDetect is currently in beta; see Current Features & Roadmap below for details.  For help or other issues, you can contact me on [my website](http://www.bcastell.com/about/), or we can chat in #pyscenedetect on Freenode.  Feel free to submit any bugs or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues) here on Github.


Download & Installation
----------------------------------------------------------

**Downloading:** The latest version of PySceneDetect (`v0.4`) can be [downloaded here](https://github.com/Breakthrough/PySceneDetect/releases); to run it, you will need:

 - [Python 2 / 3](https://www.python.org/) (tested on 2.7.X, untested but should work on 3.X)
 - OpenCV Python Module (usually found in Linux package repos as `python-opencv`, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://sourceforge.net/projects/numpy/)
 - [mkvmerge](https://mkvtoolnix.download/downloads.html) (usually found in package managers, part of mkvtoolnix)
 - [ffmpeg](https://www.ffmpeg.org/download.html)(optional, in case you want more precision when splitting videos)

More complete documentation and installation instructions can be [found on Readthedocs](http://pyscenedetect.readthedocs.org/en/latest/download/), including a detailed guide on how to install the above dependencies.  Note that in some cases the Windows version may require an additional `opencv_ffmpeg.dll` file for the specific version of OpenCV installed.

To ensure you have all the system requirements installed, open a `python` interpreter/REPL, and ensure you can `import numpy` and `import cv2` without any errors.  You can download a test video and view the expected output [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests) (see the end of the Usage section below for details).

**Installing:** Once you have all the system requirements, go to where you [downloaded PySceneDetect](https://github.com/Breakthrough/PySceneDetect/releases) and extract the archive.  To install PySceneDetect, run the following command in the folder containing the extracted files (the one containing `setup.py`):

    python setup.py install

After installation, you can use PySceneDetect as the `scenedetect` command from any terminal/command prompt.  To verify the installation, run the following command to display what version of PySceneDetect you have installed:

    scenedetect --version


Usage
----------------------------------------------------------

**There is now a dedicated [`USAGE.md` file (here)](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) containing more detailed usage instructions.  Documentation is also being [added to Readthedocs](http://pyscenedetect.readthedocs.org/), which will eventually replace the content of this file (see the [PySceneDetect Quickstart Section](http://pyscenedetect.readthedocs.org/en/latest/examples/usage/) for details)..**

To run PySceneDetect, use the `scenedetect` command if you have it installed to your system.  Otherwise, if you are running from source, you can invoke `python scenedetect.py` or `./scenedetect.py` (instead of `scenedetect` in the examples shown below and elsewhere).  To display the help file, detailing the command line parameters:

    scenedetect --help

To perform threshold-based analysis with the default parameters, on a video named `myvideo.mp4`, saving a list of scenes to `myvideo_scenes.csv` (they are also printed to the terminal):

    scenedetect --input myvideo.mp4 --csv-output myvideo_scenes.csv

To perform content-based analysis, with a threshold intensity of 30:

    scenedetect --input myvideo.mp4 --detector content --threshold 30

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

Copyright (C) 2012-2017 Brandon Castellano.
All rights reserved.
