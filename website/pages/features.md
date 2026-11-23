# Features

## Overview

### Content-aware scene detection

PySceneDetect finds cuts between scenes by comparing frame content, not only fades to black. A threshold detector is also included for detecting fades.

### Standard export formats

Export detected scene cuts in formats that work directly with video editors and command-line tools. The default comma-separated `HH:MM:SS.nnn` format can be pasted directly into `ffmpeg` or `mkvmerge`.

### Per-frame video analysis

Export frame-by-frame metrics to a CSV stats file so you can plot trends in a spreadsheet and pick the best threshold for your video.

### Modular Python API

PySceneDetect is written in Python with an extensible API. You can embed it in your own applications or write custom detectors for specialized video workflows.

------------------------------------------------------------------------

## Key Capabilities

- Export timecodes in comma-separated `HH:MM:SS.nnn` format for external tools and spreadsheets.
- Save frame-by-frame video metrics to a CSV stats file with `-s FILE` / `--stats FILE` (for example, `--stats metrics.csv`).
- Hide terminal output with `-q` / `--quiet` when automating scripts.
- Save still frames from each scene with the `save-images` command.
- Split the input video into separate scene clips with `split-video` using `ffmpeg` or `mkvmerge`.

## Output Formats

- **CSV** (`list-scenes`): save a scene list table and comma-separated cut times (`HH:MM:SS.nnn`).
- **EDL** (`save-edl`): save a CMX 3600 edit decision list for most video editors.
- **Final Cut Pro XML** (`save-fcp`): save a Final Cut Pro X (FCPXML) or Final Cut Pro 7 (xmeml) timeline.
- **HTML** (`save-html`): save an HTML scene table to view in a web browser, with optional preview images.
- **Images** (`save-images`): save still frames from each scene as JPEG, PNG, or WebP files.
- **Keyframes** (`save-keyframes`): save cut frame numbers in keyframe format v1 (for example, for Aegisub).
- **OpenTimelineIO** (`save-otio`): save an [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) timeline file.
- **QP** (`save-qp`): save cut frame numbers for use with x264 and x265 `--qpfile`.
- **Video Clips** (`split-video`): split the input video into one file per scene with `ffmpeg` or `mkvmerge`.

## Detectors

PySceneDetect includes five detectors. You can run them alone or combine more than one for the same video:

- **Adaptive detector** (`detect-adaptive`, default): compares each frame's HSV content score against a rolling average of nearby frames to find fast cuts while reducing false cuts during camera motion.
- **Content detector** (`detect-content`): compares differences in the HSV color space (and optional edges) between adjacent frames to find fast cuts.
- **Perceptual hash detector** (`detect-hash`): computes a perceptual hash for each frame and compares adjacent hashes to find fast cuts.
- **Histogram detector** (`detect-hist`): compares Y-channel (brightness) histograms in the YUV color space between adjacent frames to find fast cuts.
- **Threshold detector** (`detect-threshold`): measures average RGB frame brightness to find fades to and from black.

Each detector uses default settings tuned for both speed and accuracy. You can adjust every option from the command line or a config file, and every parameter in Python. See the [Reference Manual](/docs/latest/) for details and the [Benchmarks](benchmarks.md) page for accuracy scores across public datasets.

------------------------------------------------------------------------

## Version Roadmap

Planned releases are tracked in [GitHub milestones](https://github.com/Breakthrough/PySceneDetect/milestones), and active work uses [the `in progress` label](https://github.com/Breakthrough/PySceneDetect/issues?q=is%3Aissue+is%3Aopen+label%3A%22in+progress%22). Submit bug reports and feature requests on [the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues); see [Contributing & Support](contributing.md) for guidelines.

### Planned features

Areas under consideration for future releases include a cross-platform GUI, automatic threshold selection, improved flash suppression ([#35](https://github.com/Breakthrough/PySceneDetect/issues/35)), better dissolve detection, and adaptive fade bias. See [Features That Need Help](contributing.md#features-that-need-help) if you would like to contribute.
