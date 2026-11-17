## Overview

**PySceneDetect** is a tool for **detecting shot changes in videos** ([CLI guide](cli.md)), and can **automatically split the video into separate clips**. PySceneDetect is free and open-source software, and has several [detection methods](features.md#detection-methods) to find fast-cuts and threshold-based fades.

## Quickstart

Split video on each fast cut using the [CLI guide](cli.md):

```bash
scenedetect -i video.mp4 split-video
```

Split video on each fast cut using the [Python API (docs)](docs.md):

```python
from scenedetect import detect, AdaptiveDetector, split_video_ffmpeg

scene_list = detect("my_video.mp4", AdaptiveDetector())
split_video_ffmpeg("my_video.mp4", scene_list)
```

## Examples and Use Cases

Here are some of the things people are using PySceneDetect for:

- splitting home videos or other source footage into individual scenes
- automated detection and removal of commercials from PVR-saved video sources
- processing and splitting surveillance camera footage
- statistical analysis of videos to find suitable "loops" for looping GIFs/cinemagraphs
- academic analysis of film and video (e.g. finding mean shot length)

Of course, this is just a small slice of what you can do with PySceneDetect -- [Download PySceneDetect](download.md) to try it out for yourself! The timecode format used by default (`HH:MM:SS.nnnn`) is compatible with most popular video tools, so in most cases the output scene list from PySceneDetect can be directly copied and pasted into another tool of your choice (e.g. `ffmpeg`, `avconv` or the `mkvtoolnix` suite).
