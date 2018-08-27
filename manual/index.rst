
.. PySceneDetect documentation index file (contains toctree directive).
    Copyright (C) 2018 Brandon Castellano.  All rights reserved.


#######################################################################
PySceneDetect v0.5 Manual
#######################################################################

.. warning::

    This documentation is a draft/beta of the v0.5 documentation prepared for public review.
    If you spot any errors, issues, or discrepencies of any kind, feel free to
    `submit a new issue <https://github.com/Breakthrough/PySceneDetect/issues/new?template=blank-template.md>`_
    on the `PySceneDetect Issue Tracker <https://github.com/Breakthrough/PySceneDetect/issues>`_

    This documentation is almost complete, but still under development.  To fill in any gaps in the meantime,
    you can visit the main project page at `py.scenedetect.com <http://py.scenedetect.com>`_.

Note that this manual refers to both the the PySceneDetect
command-line interface (the `scenedetect` command) and the PySceneDetect Python API
(the `scenedetect` module).

Information regarding installing/downloading PySceneDetect or obtaining the latest
release can be found at
`scenedetect.com <http://scenedetect.com/>`_.

The latest source code for PySceneDetect can always be found on Github at
`github.com/Breakthrough/PySceneDetect <http://github.com/Breakthrough/PySceneDetect>`_.

.. note::

     PySceneDetect supports both Python 2.7 and 3.x.
     
     It is suggested to use or migrate to Python 3.x whenever possible,
     as it provides better overall performance.


***********************************************************************
Table of Contents
***********************************************************************

=======================================================================
``scenedetect`` Command Reference
=======================================================================

.. toctree::
    :maxdepth: 2
    :caption: Command-Line Interface [CLI]:
    :name: clitoc

    cli/global_options
    cli/detectors
    cli/commands

=======================================================================
``scenedetect`` Python Module
=======================================================================

.. toctree::
    :maxdepth: 3
    :caption: Python API Documentation:
    :name: apitoc

    api
    api/frame_timecode
    api/video_manager
    api/scene_manager
    api/stats_manager
    api/scene_detector
    api/detectors
    api/video_splitter

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


