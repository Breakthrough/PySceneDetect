
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


------------------------------------------------------------------------


## Features in Current Release

 - exports list of scenes to .CSV file and terminal (both timecodes and frame numbers) with `list-scenes` command
 - exports timecodes in standard format (HH:MM:SS.nnn), comma-separated for easy copy-and-paste into external tools and analysis with spreadsheet software
 - statistics/analysis mode to export frame-by-frame video metrics via the `-s [FILE]`/`--stats [FILE]` argument (e.g. `--stats metrics.csv`)
 - output-suppression (quiet) mode for better automation with external scripts/programs (`-q`/`--quiet`)
 - save an image of the first and last frame of each detected scene via the `save-images` command
 - split the input video automatically if `ffmpeg` or `mkvmerge` is available via the `split-video` command


### Scene Detection Methods

 - **threshold scene detection** (`detect-threshold`): analyzes video for changes in average frame intensity/brightness
 - **content-aware scene detection** (`detect-content`): based on changes between frames in the HSV color space
 - **adaptive content scene detection** (`detect-adaptive`): based on `detect-content` but handles fast camera movement better in some cases

For a detailed explanation of how a particular scene detection method/algorithm works, see the [Scene Detection Method Details Section](reference/detection-methods.md) in the Documentation & Reference.


------------------------------------------------------------------------


## Version Roadmap

Future version roadmaps are now [tracked as milestones (link)](https://github.com/Breakthrough/PySceneDetect/milestones).  Specific issues/features that are queued up for the very next release will have [the `backlog` tag](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3A%22status%3A+backlog%22), and issues/features being worked on will have [the `status: in progress` tag](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3A%22status%3A+in+progress%22).  Also note that bug reports as well as additional feature requests can be submitted via [the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues); read [the Bug Reports and Contributing page](contributing.md) for details.


### Planned Features for Future Releases

The following features are under consideration for future releases of PySceneDetect.  Feel free to jump in and help out!

 - automatic threshold detection for the current scene detection methods (can simply be an ouptut message indicating "Predicted Best Threshold: X")
 - optional suppression of short-length flashes/bursts of light [ [#35] ](https://github.com/Breakthrough/PySceneDetect/issues/35)
 - colour histogram-based scene detection algorithm in the HSV/HSL colourspace [ [#53] ](https://github.com/Breakthrough/PySceneDetect/issues/53)
 - [perceptual hash](https://en.wikipedia.org/wiki/Perceptual_hashing) based scene detection
 - improve robustness of content-aware detection by combining with edge detection (similar to MATLAB-based scene change detector)
 - adaptive bias for fade in/out interpolation
 - multithreaded implementation of detection algorithms for improved performance
 - GUI for easier previewing and threshold setting (will be GTK+ 3 based via PyGObject)
 - export scenes in chapter/XML format
 - additional timecode formats

