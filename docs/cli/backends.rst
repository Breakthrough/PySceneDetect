
.. _cli-backends:

***********************************************************************
Backends
***********************************************************************

PySceneDetect supports multiple backends for video input. Some can be configured by using :ref:`a config file <scenedetect_cli-config_file>`. Installed backends can be verified by running ``scenedetect version --all``.


=======================================================================
OpenCV
=======================================================================

*[Default]*
The `OpenCV <https://opencv.org/>`_ backend (usually `opencv-python <https://pypi.org/project/opencv-python/>`_) uses an underlying ``cv2.VideoCapture object`` for video input. Can be used by specifying ``-b opencv`` via command line, or setting ``backend = opencv`` under the ``[global]`` section of your :ref:`config file <scenedetect_cli-config_file>`.

It is mostly reliable and fast, although can occasionally run into issues processing videos with multiple audio tracks or small amounts of frame corruption. You can use a custom version of the ``cv2`` package, or install either the `opencv-python` or `opencv-python-headless` packages from `pip`.

The OpenCV backend also supports image sequences as inputs (e.g. ``frame%02d.jpg`` if you want to load frame001.jpg, frame002.jpg, frame003.jpg...). Make sure to specify the framerate manually (``-f``/``--framerate``) to ensure accurate timing calculations.


=======================================================================
PyAV
=======================================================================

The `PyAV <https://github.com/PyAV-Org/PyAV>`_ backend (package `av <https://pypi.org/project/av/>_`) is a more robust backend that handles multiple audio tracks and frame decode errors gracefully.

This backend can be used by specifying ``-b pyav`` via command line, or setting ``backend = pyav`` under the ``[global]`` section of your :ref:`config file <scenedetect_cli-config_file>`.
