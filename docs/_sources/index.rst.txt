
.. PySceneDetect documentation index file (contains toctree directive).
    Copyright (C) 2014-2023 Brandon Castellano.  All rights reserved.

#######################################################################
PySceneDetect Documentation
#######################################################################

This documentation covers the PySceneDetect command-line interface (the `scenedetect` command) and Python API (the `scenedetect` module).  The latest release of PySceneDetect can be installed via `pip install scenedetect[opencv]`. Windows builds and source releases can be found at `scenedetect.com/download <http://www.scenedetect.com/download/>`_. Note that PySceneDetect requires `ffmpeg` or `mkvmerge` for video splitting support.

.. note::

     If you see any errors in the documentation, or want to suggest improvements, feel free to raise an issue on `the PySceneDetect issue tracker <https://github.com/Breakthrough/PySceneDetect/issues>`_.

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

    cli
    cli/config_file
    cli/backends


=======================================================================
``scenedetect`` Python Module 🐍
=======================================================================

.. toctree::
    :maxdepth: 2
    :caption: Python API Documentation:
    :name: apitoc

    api
    api/detectors
    api/backends
    api/scene_manager
    api/video_splitter
    api/stats_manager
    api/frame_timecode
    api/scene_detector
    api/video_stream
    api/platform
    api/migration_guide

=======================================================================
Indices and Tables
=======================================================================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
