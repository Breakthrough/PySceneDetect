
## Overview of Features

<div class="warning">
<h3><span class="fa fa-eye wy-text-neutral"></span>&nbsp; Content-Aware Scene Detection</h3>
&nbsp;<span class="fa fa-info-circle wy-text-info"></span>&nbsp;&nbsp; Detects breaks in-between <i>content</i>, not only when the video fades to black (although a threshold mode is available as well for those cases).
</div>

<div class="important">
<h3><span class="fa fa-desktop wy-text-info"></span>&nbsp; Compatible With Many External Tools</h3>
&nbsp;<span class="fa fa-info-circle wy-text-info"></span>&nbsp;&nbsp; The detected scene boundaries/cuts can be exported in a variety of formats, with the default type (comma-separated HH:MM:SS.nnn values) being ready to copy-and-paste directly into other tools (such as ffmpeg, mkvmerge, etc...) for splitting and/or re-encoding the video.
</div>

<div class="danger">
<h3><span class="fa fa-bar-chart-o wy-text-warning"></span>&nbsp; Statistical Video Analysis</h3>
&nbsp;<span class="fa fa-info-circle wy-text-info"></span>&nbsp;&nbsp; Can output a spreadsheet-compatible file for analyzing trends in a particular video file, to determine the optimal threshold values to use with specific scene detection methods/algorithms. 
</div>

<div class="warning">
<h3><span class="fa fa-code wy-text-danger"></span>&nbsp; Extendible and Embeddable</h3>
&nbsp;<span class="fa fa-info-circle wy-text-info"></span>&nbsp;&nbsp; Written in Python, and designed with an easy-to-use and extendable API, PySceneDetect is ideal for embedding into other programs, or to implement custom methods/algorithms of scene detection for specific applications (e.g. analyzing security camera footage).
</div>


----------------


### Features in Current Release

 - exports list of scenes to .CSV file and terminal (both timecodes and frame numbers) with `list-scenes` command
 - exports timecodes in standard format (HH:MM:SS.nnn), comma-separated for easy copy-and-paste into external tools and analysis with spreadsheet software
 - statistics/analysis mode to export frame-by-frame video metrics (`--stats/-s statsfile.csv`)
 - output-suppression (quiet) mode for better automation with external scripts/programs (`-v quiet`)
 - user-selectable subsampling for improved performance (`-d/--downscale`)
 - user-selectable frame skipping for improved performance (`-fs`, not recommended)
 - save an image of the first and last frame of each detected scene via the `save-images` command
 - ability to specify starting/ending times via `time` command (`--start/-s` and `--end/-e`), and/or set duration for processing (`--duration/-d`)
 - user-definable fade bias to shift scenes between fade in/out points (threshold mode only)

### List of Scene Detection Methods

 - **threshold scene detection** (`detect-threshold`): analyzes video for changes in average frame intensity/brightness
 - **content-aware scene detection** (`detect-content`): based on changes between frames in the HSV color space

For a detailed explanation of how a particular scene detection method/algorithm works, see the [Scene Detection Method Details Section](reference/detection-methods.md) in the Documentation & Reference.


----------------


## Version Roadmap

<h3>Features in Development for Next Version</h3>

The following are features being planned or developed after the release of v0.5:

 - additional timecode formats
 - adaptive bias for fade in/out interpolation
 - multithreaded implementation of detection algorithms for improved performance

<h3>Planned Features for Future Releases</h3>

The following are features being planned or developed for future releases of PySceneDetect (v0.4 and onwards):

 - export scenes in chapter/XML format
 - improve robustness of content-aware detection by combining with edge detection (similar to MATLAB-based scene change detector)
 - automatic threshold detection for the current scene detection methods (can be done in pre-pass if necessary)
 - GUI for easier previewing and threshold setting (will be GTK+ 3 based via PyGObject)

