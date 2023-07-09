
PySceneDetect
==========================================================

Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

.. image:: https://img.shields.io/github/actions/workflow/status/Breakthrough/PySceneDetect/build-linux.yml
   :target: https://github.com/Breakthrough/PySceneDetect/actions

.. image:: https://img.shields.io/github/release/Breakthrough/PySceneDetect.svg
   :target: https://github.com/Breakthrough/PySceneDetect

.. image:: https://img.shields.io/pypi/status/scenedetect.svg
   :target: https://github.com/Breakthrough/PySceneDetect

.. image:: https://img.shields.io/pypi/l/scenedetect.svg
   :target: http://pyscenedetect.readthedocs.org/en/latest/copyright/

.. image:: https://img.shields.io/github/stars/Breakthrough/PySceneDetect.svg?style=social&label=View%20on%20Github
   :target: https://github.com/Breakthrough/PySceneDetect

----------------------------------------------------------

Website: https://www.scenedetect.com/

Documentation: https://www.scenedetect.com/docs

Github Repo: https://github.com/Breakthrough/PySceneDetect/

----------------------------------------------------------

PySceneDetect is a command-line tool and Python library which analyzes a video, looking for scene changes or cuts. PySceneDetect integrates with external tools (e.g. `ffmpeg`, `mkvmerge`) to automatically split the video into individual clips when using the `split-video` command and has several other features.

Install: ``pip install --upgrade scenedetect[opencv]``

Split video via CLI: ``scenedetect -i video.mp4 split-video``

Split video using Python API:

```python
from scenedetect import detect, AdaptiveDetector, split_video_ffmpeg
scene_list = detect('my_video.mp4', AdaptiveDetector())
split_video_ffmpeg('my_video.mp4', scene_list)
```

----------------------------------------------------------

Licensed under BSD 3-Clause (see the ``LICENSE`` file for details).

Copyright (C) 2014-2023 Brandon Castellano.
All rights reserved.

