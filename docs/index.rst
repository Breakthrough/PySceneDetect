
.. PySceneDetect documentation index file (contains toctree directive).
    Copyright (C) 2014-2023 Brandon Castellano.  All rights reserved.

#######################################################################
PySceneDetect Manual
#######################################################################

This manual refers to both the PySceneDetect command-line interface (the `scenedetect` command) and the PySceneDetect Python API (the `scenedetect` module).  The latest release of PySceneDetect can be installed via `pip install scenedetect[opencv]`, or Windows builds and source releases can be found at `scenedetect.com <http://scenedetect.com/>`_. Note that PySceneDetect requires `ffmpeg` or `mkvmerge` for video splitting support.

.. note::

     If you see any errors in this manual, or have any recommendations, feel free to raise an issue on `the PySceneDetect issue tracker <https://github.com/Breakthrough/PySceneDetect/issues>`_.

The latest source code for PySceneDetect can be found on Github at `github.com/Breakthrough/PySceneDetect <http://github.com/Breakthrough/PySceneDetect>`_.


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
    cli/config_file
    cli/backends


=======================================================================
``scenedetect`` Python Module 🐍
=======================================================================

.. toctree::
    :maxdepth: 3
    :caption: Python API Documentation:
    :name: apitoc

    api
    api/scene_manager
    api/detectors
    api/backends
    api/video_splitter
    api/frame_timecode
    api/scene_detector
    api/stats_manager
    api/video_stream
    api/platform
    api/migration_guide

=======================================================================
Indices and Tables
=======================================================================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
