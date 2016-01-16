
<h1>PySceneDetect &nbsp;<span class="fa fa-film"></span></h1>

<div class="important">
<h3><span class="fa fa-info-circle"></span>&nbsp; Latest Release: <b>v0.3-beta</b></h3>
&nbsp;<a href="download/" alt="Download PySceneDetect"><span class="fa fa-download"></span>&nbsp; Download</a> &nbsp;&nbsp;|&nbsp;&nbsp; <a href="changelog/" alt="PySceneDetect Changelog"><span class="fa fa-reorder"></span>&nbsp; Changelog</a> &nbsp;&nbsp;|&nbsp;&nbsp; <span class="fa fa-calendar"></span>&nbsp; Release Date: January 8, 2016
</div>

**PySceneDetect** is a command-line application and a Python library for **automatically detecting scene changes in video files**.  Not only is it free and open-source software (FOSS), but there are several detection methods available ([see Features](features.md)), from simple threshold-based fade in/out detection, to advanced content aware fast-cut detection.

PySceneDetect can be used on its own as a stand-alone executable, with other applications as part of a video processing pipeline, or integrated directly into other programs/scripts via the Python API.  PySceneDetect is written in Python, and requires the OpenCV and Numpy software libraries.


<h3>Examples and Use Cases</h3>

Here are some of the things people are using PySceneDetect for:

 - splitting home videos or other source footage into individual scenes
 - automated detection and removal of commercials from PVR-saved video sources
 - processing and splitting surveillance camera footage
 - statistical analysis of videos to find suitable "loops" for looping GIFs/cinemagraphs
 - academic analysis of film and video (e.g. finding mean shot length)

Of course, this is just a small slice of what you can do with PySceneDetect, so why not <a href="download/" alt="Download PySceneDetect">try it out for yourself</a>!  The timecode format used by default (`HH:MM:SS.nnnn`) is compatible with most popular video tools, so in most cases the output scene list from PySceneDetect can be directly copied and pasted into another tool of your choice (e.g. `ffmpeg`, `avconv` or the `mkvtoolnix` suite).




<meta name="google-site-verification" content="KQZZzUYeED_aSqqDqS4vGj4V7X5pyDtcTgJEZSyuDxY" />

