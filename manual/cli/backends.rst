
.. _cli-backends:

***********************************************************************
Backends
***********************************************************************

PySceneDetect supports multiple backends for video input. Some can be configured by using :ref:`a config file <scenedetect_cli-config_file>`.


=======================================================================
OpenCV
=======================================================================

*[Default]*

The OpenCV backend uses an underlying VideoCapture object for video input. It is mostly reliable and fast, although can occasionally run into issues processing videos with multiple audio tracks or small amounts of frame corruption. It is provided by the `opencv-python` or `opencv-python-headless` packages on `pip`.

This backend can be used by specifying ``-b opencv`` via command line, or setting ``backend = opencv`` under the ``[global]`` section of your :ref:`config file <scenedetect_cli-config_file>`.

The OpenCV backend also supports image sequences as inputs (e.g. ``frame%02d.jpg`` if you want to load frame001.jpg, frame002.jpg, frame003.jpg...). Make sure to specify the framerate manually (``-f``/``--framerate``) to ensure accurate timing calculations.


=======================================================================
PyAV
=======================================================================

The PyAV backend (``-b pyav``) is a more robust backend that handles multiple audio tracks and frame decode errors gracefully.  It is provided by the `av` package on `pip`.

This backend can be used by specifying ``-b pyav`` via command line, or setting ``backend = pyav`` under the ``[global]`` section of your :ref:`config file <scenedetect_cli-config_file>`.
