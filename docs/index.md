<h1 class="wy-text-neutral">PySceneDetect &nbsp;<span class="fa fa-film wy-text-info"></span></h1>
<h4 class="wy-text-info">Intelligent scene cut detection and video splitting tool.</h4>

<div class="important">
<h3 class="wy-text-neutral"><span class="fa fa-info-circle wy-text-info"></span>&nbsp; Latest Release: <b>v0.4</b> (January 14, 2017)</h3>
<a href="download/" class="btn btn-success" style="margin-bottom:8px;" role="button"><span class="fa fa-download"></span>&nbsp; <b>Download</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="changelog/" class="btn btn-info" style="margin-bottom:8px;" role="button"><span class="fa fa-reorder"></span>&nbsp; <b>Changelog</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="download/#installation" class="btn btn-warning" style="margin-bottom:8px;" role="button"><span class="fa fa-gear"></span>&nbsp; <b>Installation</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="examples/usage/" class="btn btn-danger" style="margin-bottom:8px;" role="button"><span class="fa fa-book"></span>&nbsp; <b>Getting Started</b></a>
</div>


**PySceneDetect** is a command-line application and a Python library for **detecting scene changes in videos**, and **automatically splitting the video into separate clips**.  Not only is it free and open-source software (FOSS), but there are several detection methods available ([see Features](features.md)), from simple threshold-based fade in/out detection, to advanced content aware fast-cut detection.

PySceneDetect can be used on its own as a stand-alone executable, with other applications as part of a video processing pipeline, or integrated directly into other programs/scripts via the Python API.  PySceneDetect is written in Python, and requires the OpenCV and Numpy software libraries.


<h3>Examples and Use Cases</h3>

Here are some of the things people are using PySceneDetect for:

 - splitting home videos or other source footage into individual scenes
 - automated detection and removal of commercials from PVR-saved video sources
 - processing and splitting surveillance camera footage
 - statistical analysis of videos to find suitable "loops" for looping GIFs/cinemagraphs
 - academic analysis of film and video (e.g. finding mean shot length)

Of course, this is just a small slice of what you can do with PySceneDetect, so why not <a href="download/" alt="Download PySceneDetect">try it out for yourself</a>!  The timecode format used by default (`HH:MM:SS.nnnn`) is compatible with most popular video tools, so in most cases the output scene list from PySceneDetect can be directly copied and pasted into another tool of your choice (e.g. `ffmpeg`, `avconv` or the `mkvtoolnix` suite).

