
![PySceneDetect](https://raw.githubusercontent.com/Breakthrough/PySceneDetect/master/docs/img/pyscenedetect_logo_small.png)
==========================================================
Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

[![Documentation Status](https://readthedocs.org/projects/pyscenedetect/badge/?version=latest)](http://pyscenedetect.readthedocs.org/en/latest/?badge=latest) [![PyPI Status](https://img.shields.io/pypi/status/scenedetect.svg)](https://pypi.python.org/pypi/scenedetect/) [![PyPI Version](https://img.shields.io/pypi/v/scenedetect.svg)](https://pypi.python.org/pypi/scenedetect/)  [![PyPI License](https://img.shields.io/pypi/l/scenedetect.svg)](http://pyscenedetect.readthedocs.org/en/latest/copyright/)


### Latest Release: v0.5.1 (July 20, 2019)

**Main Webpage**:  [py.scenedetect.com](http://py.scenedetect.com)

**Documentation**:  [manual.scenedetect.com](http://manual.scenedetect.com)

**Download/Install**: https://pyscenedetect.readthedocs.io/en/latest/download/

----------------------------------------------------------

**Quick Install**: Requires Python modules `numpy`, OpenCV `cv2`, and (optional) `tqdm` for displaying progress.  To install PySceneDetect via `pip` with all dependencies:

    pip install scenedetect[opencv,progress_bar]

Or to install just PySceneDetect (OpenCV installation required):

    pip install scenedetect

To test if you have the required prerequisites, open a `python` prompt, and run the following:

    import numpy
    import cv2

If both of those commands execute without any problems, you should be able to run PySceneDetect without any issues. To enable video splitting support, you will also need to have `mkvmerge` or `ffmpeg` installed on your system. See the documentation on [Video Splitting Support](https://pyscenedetect.readthedocs.io/en/latest/examples/video-splitting/) after installation for details.

Full documentation for PySceneDetect can be found [on Readthedocs](http://pyscenedetect.readthedocs.org/), or by visiting [py.scenedetect.com](http://py.scenedetect.com/).  This includes details on detection modes, default values/thresholds to try, and how to effectively choose the optimal detection parameters.

**Install From Source**: To install from source code instead, download the latest release archive, and run `python setup.py install` wherever you extract the archive (see releases tab or [the download page](https://pyscenedetect.readthedocs.io/en/latest/download/) for details).

----------------------------------------------------------

PySceneDetect is a command-line tool, written in Python and using OpenCV, which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with another tool (e.g. `mkvmerge`, `ffmpeg`) to split the video into individual clips.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.  See [the Usage documentation](https://pyscenedetect.readthedocs.io/en/latest/examples/usage/) for details.

There are two main detection methods PySceneDetect uses: `detect-threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `detect-content` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

In general, use `detect-threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `detect-content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.

Note that PySceneDetect is currently in beta; see Current Features & Roadmap below for details.  For help or other issues, you can contact me on [my website](http://www.bcastell.com/about/), or we can chat in #pyscenedetect on Freenode.  Feel free to submit any bugs or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues) here on Github.


Download & Installation
----------------------------------------------------------

See [the Download & Installation page on Readthedocs](http://pyscenedetect.readthedocs.org/en/latest/download/) ([alt. link](https://github.com/Breakthrough/PySceneDetect/blob/master/docs/download.md)) for how to get PySceneDetect, as well as details on which system dependencies are required.

Usage
----------------------------------------------------------

 - [Basic Usage](https://pyscenedetect.readthedocs.io/en/latest/examples/usage/)
 - [PySceneDetect Manual](https://pyscenedetect-manual.readthedocs.io/en/latest/), covers `scenedetect` command and Python API
 - [Example: Detecting and Splitting Scenes in Movie Clip](https://pyscenedetect.readthedocs.io/en/latest/examples/usage-example/)


Current Features & Roadmap
----------------------------------------------------------

You can [view the latest features and version roadmap on Readthedocs](http://pyscenedetect.readthedocs.org/en/latest/features/).
See [`docs/changelog.md`](https://github.com/Breakthrough/PySceneDetect/blob/master/docs/changelog.md) for a list of changes in each version, or visit [the Releases page](https://github.com/Breakthrough/PySceneDetect/releases) to download a specific version.  Feel free to submit any bugs/issues or feature requests to [the Issue Tracker](https://github.com/Breakthrough/PySceneDetect/issues).

Additional features being planned or in development can be found [here (tagged as `feature`) in the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3Afeature).  You can also find additional information about PySceneDetect at [http://www.bcastell.com/projects/pyscenedetect/](http://www.bcastell.com/projects/pyscenedetect/).


----------------------------------------------------------

Licensed under BSD 3-Clause (see the `LICENSE` file for details).

Copyright (C) 2014-2019 Brandon Castellano.
All rights reserved.

