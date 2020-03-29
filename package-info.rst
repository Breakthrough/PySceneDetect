
PySceneDetect
==========================================================

Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

.. image:: https://readthedocs.org/projects/pyscenedetect/badge/?version=latest
   :target: http://pyscenedetect.readthedocs.org/en/latest/?badge=latest

.. image:: https://img.shields.io/github/release/Breakthrough/PySceneDetect.svg
   :target: https://github.com/Breakthrough/PySceneDetect

.. image:: https://img.shields.io/pypi/status/scenedetect.svg
   :target: https://github.com/Breakthrough/PySceneDetect

.. image:: https://img.shields.io/pypi/l/scenedetect.svg
   :target: http://pyscenedetect.readthedocs.org/en/latest/copyright/

.. image:: https://img.shields.io/github/stars/Breakthrough/PySceneDetect.svg?style=social&label=View%20on%20Github
   :target: https://github.com/Breakthrough/PySceneDetect

----------------------------------------------------------

Website: http://py.scenedetect.com/

Documentation: http://manual.scenedetect.com/

Github Repo: https://github.com/Breakthrough/PySceneDetect/

----------------------------------------------------------

PySceneDetect is a command-line tool and Python library which analyzes a video, looking for scene changes or cuts.  PySceneDetect integrates with external tools (e.g. `mkvmerge`, `ffmpeg`) to automatically split the video into individual clips when using the `split-video` command.  A frame-by-frame analysis can also be generated for a video, called a stats file, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.

There are two main detection methods PySceneDetect uses: `detect-threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `detect-content` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail in the documentation.

In general, use `detect-threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `detect-content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--stats` argument) in order to determine the correct paramters - specifically, the proper threshold value.

For help or other issues, feel free to submit any bugs or feature requests to Github: https://github.com/Breakthrough/PySceneDetect/issues

----------------------------------------------------------

Licensed under BSD 3-Clause (see the `LICENSE` file for details).

Copyright (C) 2014-2020 Brandon Castellano.
All rights reserved.

