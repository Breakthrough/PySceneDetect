
.. PySceneDetect documentation index file (contains toctree directive).
    Copyright (C) 2014-2022 Brandon Castellano.  All rights reserved.


#######################################################################
PySceneDetect Manual
#######################################################################

.. warning::

    Version 0.6 is under development. This manual may be outdated or incorrect in places.

This manual refers to both the PySceneDetect command-line interface (the `scenedetect`
command) and the PySceneDetect Python API (the `scenedetect` module).  Information
regarding installing/downloading PySceneDetect or obtaining the latest release can be
found at `scenedetect.com <http://scenedetect.com/>`_.

PySceneDetect requires `ffmpeg` or `mkvmerge` for video splitting support.

.. note::

     If you see any errors in this manual, or have any recommendations,
     feel free to raise an issue on
     `the PySceneDetect issue tracker <https://github.com/Breakthrough/PySceneDetect/issues>`_.

The latest source code for PySceneDetect can be found on Github at
`github.com/Breakthrough/PySceneDetect <http://github.com/Breakthrough/PySceneDetect>`_.

***********************************************************************
Table of Contents
***********************************************************************

=======================================================================
``scenedetect`` Command Reference 🖥️
=======================================================================

.. toctree::
    :maxdepth: 2
    :caption: Command-Line Interface [CLI]:
    :name: clitoc

    cli/global_options
    cli/commands
    cli/detectors

=======================================================================
``scenedetect`` Python Module 🐍
=======================================================================

.. toctree::
    :maxdepth: 3
    :caption: Python API Documentation:
    :name: apitoc

    api
    api/frame_timecode
    api/video_stream
    api/backends
    api/scene_manager
    api/scene_list
    api/stats_manager
    api/scene_detector
    api/detectors
    api/video_splitter

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


