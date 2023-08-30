
## Overview

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


## Features

 - exports list of scenes to .CSV file and terminal (both timecodes and frame numbers) with `list-scenes` command
 - exports timecodes in standard format (HH:MM:SS.nnn), comma-separated for easy copy-and-paste into external tools and analysis with spreadsheet software
 - statistics/analysis mode to export frame-by-frame video metrics via the `-s [FILE]`/`--stats [FILE]` argument (e.g. `--stats metrics.csv`)
 - output-suppression (quiet) mode for better automation with external scripts/programs (`-q`/`--quiet`)
 - save an image of the first and last frame of each detected scene via the `save-images` command
 - split the input video automatically if `ffmpeg` or `mkvmerge` is available via the `split-video` command


### Detection Methods

 - **threshold scene detection** (`detect-threshold`): analyzes video for changes in average frame intensity/brightness
 - **content-aware scene detection** (`detect-content`): based on changes between frames in the HSV color space to find fast cuts
 - **adaptive content scene detection** (`detect-adaptive`): based on `detect-content`, handles fast camera movement better by comparing neighboring frames in a rolling window


------------------------------------------------------------------------


## Version Roadmap

Future version roadmaps are now [tracked as milestones (link)](https://github.com/Breakthrough/PySceneDetect/milestones).  Specific issues/features that are queued up for the very next release will have [the `backlog` tag](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3A%22status%3A+backlog%22), and issues/features being worked on will have [the `status: in progress` tag](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3A%22status%3A+in+progress%22).  Also note that bug reports as well as additional feature requests can be submitted via [the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues); read [the Bug Reports and Contributing page](contributing.md) for details.


### Planned Features

The following features are under consideration for future releases. Any contributions towards completing these features are most welcome (pull requests may be accpeted via Github).

 - graphical interface (GUI)
 - automatic threshold detection for the current scene detection methods (or just ouptut message indicating "Predicted Threshold: X")
 - suppression of short-length flashes/bursts of light [#35](https://github.com/Breakthrough/PySceneDetect/issues/35)
 - histogram-based detection algorithm in HSV/HSL color space [#53](https://github.com/Breakthrough/PySceneDetect/issues/53)
 - [perceptual hash](https://en.wikipedia.org/wiki/Perceptual_hashing) based scene detection ([prototype by @wjs018 in PR#290](https://github.com/Breakthrough/PySceneDetect/pull/290))
 - adaptive bias for fade in/out interpolation
 - export scenes in chapter/XML format [#323](https://github.com/Breakthrough/PySceneDetect/issues/323)
