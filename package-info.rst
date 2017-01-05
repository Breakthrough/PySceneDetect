      
PySceneDetect
==========================================================
Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

Documentation: http://pyscenedetect.readthedocs.org/

Github Repo: https://github.com/Breakthrough/PySceneDetect/


.. image:: https://readthedocs.org/projects/pyscenedetect/badge/?version=latest
   :target: http://pyscenedetect.readthedocs.org/en/latest/?badge=latest

.. image:: https://img.shields.io/github/release/Breakthrough/PySceneDetect.svg
   :target: https://github.com/Breakthrough/PySceneDetect

.. image:: https://img.shields.io/pypi/status/PySceneDetect.svg
   :target: https://github.com/Breakthrough/PySceneDetect

.. image:: https://img.shields.io/pypi/dm/PySceneDetect.svg
   :target: http://pyscenedetect.readthedocs.org/en/latest/download/

.. image:: https://img.shields.io/pypi/l/PySceneDetect.svg
   :target: http://pyscenedetect.readthedocs.org/en/latest/copyright/

.. image:: https://img.shields.io/github/stars/Breakthrough/PySceneDetect.svg?style=social&label=View%20on%20Github
   :target: https://github.com/Breakthrough/PySceneDetect


PySceneDetect is a command-line tool, written in Python and using OpenCV, which analyzes a video, looking for scene changes or cuts.  The output timecodes can then be used with another tool (e.g. `mkvmerge`, `ffmpeg`) to split the video into individual clips.  A frame-by-frame analysis can also be generated for a video, to help with determining optimal threshold values or detecting patterns/other analysis methods for a particular video.  

There are two main detection methods PySceneDetect uses: `threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `content` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail in the documentation.

In general, use `threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.

For help or other issues, feel free to submit any bugs or feature requests to Github: https://github.com/Breakthrough/PySceneDetect/issues

----------------------------------------------------------

Licensed under BSD 2-Clause (see the `LICENSE` file for details).

Copyright (C) 2012-2017 Brandon Castellano.
All rights reserved.

