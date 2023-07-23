
<img alt="PySceneDetect" src="img/pyscenedetect_logo_small.png" />

<div class="important">
<h3 class="wy-text-neutral"><span class="fa fa-info-circle wy-text-info"></span>&nbsp; Latest Release: <b>v0.6.2</b> (July 23, 2023)</h3>
<a href="download/" class="btn btn-success" style="margin-bottom:8px;" role="button"><span class="fa fa-download"></span>&nbsp; <b>Download</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="changelog/" class="btn btn-info" style="margin-bottom:8px;" role="button"><span class="fa fa-reorder"></span>&nbsp; <b>Changelog</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="docs/" class="btn btn-warning" style="margin-bottom:8px;" role="button"><span class="fa fa-gear"></span>&nbsp; <b>Documentation</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="cli/" class="btn btn-danger" style="margin-bottom:8px;" role="button"><span class="fa fa-book"></span>&nbsp; <b>Getting Started</b></a>
<br/>
See the changelog for the latest release notes and known issues.
</div>

**PySceneDetect** is a tool/library for **detecting shot changes in videos** ([example](cli.md)), and **automatically splitting the video into separate clips**.  PySceneDetect is free and open-source software, and there are [several detection methods available](features.md) - from simple threshold-based fade in/out detection, to advanced content aware fast-cut detection of each shot.


<h3>Quickstart</h3>

Split video on each fast cut using [command line (more examples)](cli.md):

```rst
scenedetect -i video.mp4 split-video
```

Split video on each fast cut using [Python API (docs)](docs.md):

```python
from scenedetect import detect, AdaptiveDetector, split_video_ffmpeg
scene_list = detect('my_video.mp4', AdaptiveDetector())
split_video_ffmpeg('my_video.mp4', scene_list)
```


<h3>Examples and Use Cases</h3>

Here are some of the things people are using PySceneDetect for:

 - splitting home videos or other source footage into individual scenes
 - automated detection and removal of commercials from PVR-saved video sources
 - processing and splitting surveillance camera footage
 - statistical analysis of videos to find suitable "loops" for looping GIFs/cinemagraphs
 - academic analysis of film and video (e.g. finding mean shot length)

Of course, this is just a small slice of what you can do with PySceneDetect, so why not <a href="download/" alt="Download PySceneDetect">try it out for yourself</a>!  The timecode format used by default (`HH:MM:SS.nnnn`) is compatible with most popular video tools, so in most cases the output scene list from PySceneDetect can be directly copied and pasted into another tool of your choice (e.g. `ffmpeg`, `avconv` or the `mkvtoolnix` suite).
