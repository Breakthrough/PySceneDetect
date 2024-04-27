
PySceneDetect
==========================================================

Video Scene Cut Detection and Analysis Tool
----------------------------------------------------------

.. image:: https://img.shields.io/pypi/status/scenedetect.svg
   :target: https://github.com/Breakthrough/PySceneDetect

.. image:: https://img.shields.io/github/release/Breakthrough/PySceneDetect.svg
   :target: https://github.com/Breakthrough/PySceneDetect

.. image:: https://img.shields.io/pypi/l/scenedetect.svg
   :target: http://pyscenedetect.readthedocs.org/en/latest/copyright/

.. image:: https://img.shields.io/github/stars/Breakthrough/PySceneDetect.svg?style=social&label=View%20on%20Github
   :target: https://github.com/Breakthrough/PySceneDetect

----------------------------------------------------------

Documentation: https://www.scenedetect.com/docs

Github Repo: https://github.com/Breakthrough/PySceneDetect/

Install: ``pip install --upgrade scenedetect[opencv]``

----------------------------------------------------------

**PySceneDetect** is a tool for detecting shot changes in videos, and can automatically split videos into separate clips.  PySceneDetect is free and open-source software, and has several detection methods to find fast-cuts and threshold-based fades.

For example, to split a video: ``scenedetect -i video.mp4 split-video``

You can also use the Python API (`docs <https://www.scenedetect.com/docs/latest/>`_) to do the same:

.. code-block:: python

    from scenedetect import detect, AdaptiveDetector, split_video_ffmpeg
    scene_list = detect('my_video.mp4', AdaptiveDetector())
    split_video_ffmpeg('my_video.mp4', scene_list)

----------------------------------------------------------

Licensed under BSD 3-Clause (see the ``LICENSE`` file for details).

Copyright (C) 2014-2024 Brandon Castellano.
All rights reserved.

