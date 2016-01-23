
<h1>PySceneDetect &nbsp;<span class="fa fa-film"></span></h1>

<div class="important">
<h3><span class="fa fa-info-circle"></span>&nbsp; Latest Release: <b>v0.3.1-beta</b> (January 23, 2016)</h3>
<a href="download/" class="btn btn-success" role="button"><span class="fa fa-download"></span>&nbsp; <b>Download</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="changelog/" class="btn btn-info" role="button"><span class="fa fa-reorder"></span>&nbsp; </b>Changelog</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="download/#installation" class="btn btn-warning" role="button"><span class="fa fa-gear"></span>&nbsp; <b>Installation</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="examples/usage/" class="btn btn-danger" role="button"><span class="fa fa-book"></span>&nbsp; <b>Getting Started</b></a>
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


<a href="https://github.com/Breakthrough/PySceneDetect"><img style="position: absolute; top: 0; right: 0; border: 0;" src="https://camo.githubusercontent.com/38ef81f8aca64bb9a64448d0d70f1308ef5341ab/68747470733a2f2f73332e616d617a6f6e6177732e636f6d2f6769746875622f726962626f6e732f666f726b6d655f72696768745f6461726b626c75655f3132313632312e706e67" alt="Fork me on GitHub" data-canonical-src="https://s3.amazonaws.com/github/ribbons/forkme_right_darkblue_121621.png"></a>

