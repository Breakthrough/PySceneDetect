

PySceneDetect &nbsp;<span class="fa fa-film"></span>
==========================================================

<div class="important">
<h3><span class="fa fa-info-circle"></span>&nbsp; Latest Release: <b>v0.3-beta</b></h3>
&nbsp;<a href="download/" alt="Download PySceneDetect"><span class="fa fa-download"></span>&nbsp; Download</a> &nbsp;&nbsp;|&nbsp;&nbsp; <a href="changelog/" alt="PySceneDetect Changelog"><span class="fa fa-reorder"></span>&nbsp; Changelog</a> &nbsp;&nbsp;|&nbsp;&nbsp; <span class="fa fa-calendar"></span>&nbsp; Release Date: January 8, 2016
</div>

**PySceneDetect** is a command-line *application* and a Python *library* for **automatically detecting scene changes in video files**.  Not only is it free and open-source software (FOSS), but there are several detection methods available, from simple threshold-based fade in/out detection, to advanced content aware fast-cut detection.

PySceneDetect can be used on it's own as a stand-alone executable, with other applications as part of a video processing pipeline, or integrated directly into other programs/scripts via the Python API.  PySceneDetect is written in Python, and requires the OpenCV and Numpy software libraries.


### Examples and Use Cases

Here are some of the things people are using PySceneDetect for:

 - splitting home videos or other source footage into individual scenes
 - automated detection and removal of commercials from PVR-saved video sources
 - processing and splitting surveillance camera footage
 - statistical analysis of videos to find suitable "loops" for looping GIFs/cinemagraphs
 - academic analysis of film and video (e.g. finding mean shot length)

Of course, this is just a small slice of what you can do with PySceneDetect, so why not <a href="download/" alt="Download PySceneDetect">try it out for yourself</a>!  The timecode format used by default (`HH:MM:SS.nnnn`) is compatible with most popular video tools, so in most cases the output scene list from PySceneDetect can be directly copied and pasted into another tool of your choice (e.g. `ffmpeg`, `avconv` or the `mkvtoolnix` suite).


### About & Features

Video statistics can be generated and analyzed to find the optimal detection parameters, and an API is available for creating customized scene detection algorithms/filters if required.  Currently, PySceneDetect can only process video files, but future versions will include the ability to analyze a live video source (e.g. webcam) for scene changes.  Thumbnail generation is also being planned for the following version.

PySceneDetect is a command-line tool, written in Python and using OpenCV, which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with another tool (e.g. `mkvmerge`, `ffmpeg`) to split the video into individual clips.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.  See [the `USAGE.md` file](https://github.com/Breakthrough/PySceneDetect/blob/master/USAGE.md) for details.

#### Current Features

 - content-aware scene detection based on changes between frames in the HSV color space 
 - output-suppression (quiet) mode for better automation with external scripts/programs
 - threshold scene detection analyzes video for changes in average frame intensity/brightness
 - detects fade-in and fade-out based on user-defined threshold
 - exports list of scenes to .CSV file (both timecodes and frame numbers) (`-o`)
 - exports timecodes in `mkvmerge` format: `HH:MM:SS.nnnnn`, comma-separated
 - statistics/analysis mode to export frame-by-frame video metrics (`-s`)

#### In Progress

 - adaptive or user-defined bias for fade in/out interpolation
 - additional timecode formats

#### Planned Features

 - export scenes in chapter/XML format
 - improve robustness of content-aware detection by combining with edge detection (similar to [MATLAB-based scene change detector](http://www.mathworks.com/help/vision/examples/scene-change-detection.html))
 - interactive/guided mode, eventually moving to a graphical interface

 

### Getting Started

The latest version of PySceneDetect (`v0.3-beta`) can be [downloaded here](https://github.com/Breakthrough/PySceneDetect/releases); to run it, you will need:

 - [Python 2 / 3](https://www.python.org/) (tested on 2.7.X, untested but should work on 3.X)
 - OpenCV Python Module (usually found in Linux package repos as `python-opencv`, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://sourceforge.net/projects/numpy/)

To ensure you have all the requirements, open a `python` interpreter, and ensure you can `import numpy` and `import cv2` without any errors.  You can download a test video and view the expected output [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests) (see the end of the Usage section below for details).



### License & Copyright Information

PySceneDetect is licensed under the BSD 2-Clause license; see the <a href="copyright/" alt="PySceneDetect Copyright Info">License & Copyright Information page</a> for details, and a list of third-party components.


