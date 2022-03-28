
.. _cli-backends:

***********************************************************************
Backends
***********************************************************************

PySceneDetect supports multiple backends for video input. Some can be configured by using :ref:`a config file <scenedetect_cli-config_file>`.


=======================================================================
OpenCV
=======================================================================

*[Default on Linux/OSX]*

This backend, named ``opencv`` on the command line, uses OpenCV's VideoCapture object for video input. It is mostly reliable and fast, although can occasionally run into issues processing videos with multiple audio tracks or small amounts of frame corruption.

The OpenCV backend also supports image sequences as inputs (e.g. ``frame%02d.jpg`` if you want to load frame001.jpg, frame002.jpg, frame003.jpg...). Make sure to specify the framerate manually (``-f``/``--framerate``) to ensure accurate timing calculations.


=======================================================================
PyAV
=======================================================================

*[Default on Windows]*

The PyAV backend is a more robust backend that can handle multiple audio tracks and decode errors more gracefully.
