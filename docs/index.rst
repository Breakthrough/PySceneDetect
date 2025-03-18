
.. PySceneDetect documentation index file (contains toctree directive).
    Copyright (C) 2014-2024 Brandon Castellano.  All rights reserved.

#######################################################################
PySceneDetect Documentation
#######################################################################

Welcome to the PySceneDetect docs. The docs are split into two separate parts: one for the command-line interface (the `scenedetect` command) and another for the Python API (the `scenedetect` module).

You can install the latest release of PySceneDetect by running `pip install scenedetect[opencv]` or downloading the Windows build from `scenedetect.com/download <http://www.scenedetect.com/download/>`_. PySceneDetect requires `ffmpeg` or `mkvmerge` for video splitting support.

.. note::

     If you see any errors in the documentation, or want to suggest improvements, feel free to raise an issue on `the PySceneDetect issue tracker <https://github.com/Breakthrough/PySceneDetect/issues>`_.

PySceneDetect development happens on Github at `github.com/Breakthrough/PySceneDetect <http://github.com/Breakthrough/PySceneDetect>`_.


***********************************************************************
Table of Contents
***********************************************************************

=======================================================================
``scenedetect`` Command Reference 🖥️
=======================================================================

.. toctree::
    :maxdepth: 2
    :caption: Command-Line Interface:
    :name: clitoc

    cli
    cli/config_file
    cli/backends


=======================================================================
``scenedetect`` Python Module 🐍
=======================================================================

.. toctree::
    :maxdepth: 2
    :caption: API Documentation:
    :name: apitoc

    api
    api/detectors
    api/scene_manager
    api/common
    api/backends
    api/video_splitter
    api/stats_manager
    api/detector
    api/video_stream
    api/platform

=======================================================================
Indices and Tables
=======================================================================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
