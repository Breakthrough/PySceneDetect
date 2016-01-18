
## PySceneDetect Features

<div class="warning">
<h3><span class="fa fa-eye"></span>&nbsp; Content-Aware Scene Detection</h3>
&nbsp;<span class="fa fa-info-circle"></span>&nbsp;&nbsp; Detects breaks in-between <i>content</i>, not only when the video fades to black (although a threshold mode is available as well for those cases).
</div>

<div class="important">
<h3><span class="fa fa-desktop"></span>&nbsp; Compatible With Many External Tools</h3>
&nbsp;<span class="fa fa-info-circle"></span>&nbsp;&nbsp; The detected scene boundaries/cuts can be exported in a variety of formats, with the default type (comma-separated HH:MM:SS.nnn values) being ready to copy-and-paste directly into other tools (such as ffmpeg, mkvmerge, etc...) for splitting and/or re-encoding the video.
</div>

<div class="danger">
<h3><span class="fa fa-bar-chart-o"></span>&nbsp; Statistical Video Analysis</h3>
&nbsp;<span class="fa fa-info-circle"></span>&nbsp;&nbsp; Can output a spreadsheet-compatible file for analyzing trends in a particular video file, to determine the optimal threshold values to use with specific scene detection methods/algorithms. 
</div>

<div class="warning">
<h3><span class="fa fa-code"></span>&nbsp; Extendible and Embeddable</h3>
&nbsp;<span class="fa fa-info-circle"></span>&nbsp;&nbsp; Written in Python, and designed with an easy-to-use and extendable API, PySceneDetect is ideal for embedding into other programs, or to implement custom methods/algorithms of scene detection for specific applications (e.g. analyzing security camera footage).
</div>


### Current Features List (v0.3-beta)

 - output-suppression (quiet) mode for better automation with external scripts/programs
 - detects fade-in and fade-out based on user-defined threshold
 - exports list of scenes to .CSV file (both timecodes and frame numbers) (-o)
 - exports timecodes in mkvmerge format: HH:MM:SS.nnnnn, comma-separated


#### Available Scene Detection Methods:

 - threshold scene detection analyzes video for changes in average frame intensity/brightness
 - content-aware scene detection based on changes between frames in the HSV color space


----------------


## Version Roadmap


#### Features in Development for Next Version (v0.3.1-beta)

 - allow user-selectable frame skipping for improved performance
 - allow user-selectable subsampling for improved performance
 - add ability to specify start/end time for scene detection
 - additional API functions to remove requirement on passing OpenCV video objects, and allow just a file path instead


#### Features Starting Development for Following Version (v0.3.x-beta)

 - statistics/analysis mode to export frame-by-frame video metrics (-s)
 - adaptive or user-defined bias for fade in/out interpolation
 - additional timecode formats


#### Planned Features for Future Releases (v0.4-beta)

 - export scenes in chapter/XML format
 - improve robustness of content-aware detection by combining with edge detection (similar to MATLAB-based scene change detector)
 - automatic threshold detection for the current scene detection methods (can be done in pre-pass if necessary)
 - standalone distribution/build for Windows (x86/64)
 - GUI for easier previewing and threshold setting (will be GTK+ 3 based via PyGObject)

