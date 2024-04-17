
.. _cli-backends:

***********************************************************************
Backends
***********************************************************************

PySceneDetect supports multiple backends for video input. Some can be configured by using :ref:`a config file <scenedetect_cli-config_file>`. Installed backends can be verified by running ``scenedetect version --all``.

Note that the `scenedetect` command output is generated as a post-processing step, after scene detection completes. Most commands require the ability for the input to be replayed, and preferably it should also support seeking. Network streams and other input types are supported with certain backends, however integration with live streams requires use of the Python API.


=======================================================================
OpenCV
=======================================================================

*[Default]*
The `OpenCV <https://opencv.org/>`_ backend (usually `opencv-python <https://pypi.org/project/opencv-python/>`_) uses OpenCV's ``VideoCapture`` for video input. Can be used by specifying ``-b opencv`` via command line, or setting ``backend = opencv`` under the ``[global]`` section of your :ref:`config file <scenedetect_cli-config_file>`.

It is mostly reliable and fast, although can occasionally run into issues processing videos with multiple audio tracks or small amounts of frame corruption. You can use a custom version of the ``cv2`` package, or install either the `opencv-python` or `opencv-python-headless` packages from `pip`.

The OpenCV backend also supports image sequences as inputs (e.g. ``frame%02d.jpg`` if you want to load frame001.jpg, frame002.jpg, frame003.jpg...). Make sure to specify the framerate manually (``-f``/``--framerate``) to ensure accurate timing calculations.


=======================================================================
PyAV
=======================================================================

The `PyAV <https://github.com/PyAV-Org/PyAV>`_ backend (`av package <https://pypi.org/project/av/>`_) is a more robust backend that handles multiple audio tracks and frame decode errors gracefully.

This backend can be used by specifying ``-b pyav`` via command line, or setting ``backend = pyav`` under the ``[global]`` section of your :ref:`config file <scenedetect_cli-config_file>`.


=======================================================================
MoviePy
=======================================================================

MoviePy launches ffmpeg as a subprocess, and can be used with various types of inputs. If the input supports seeking it should work fine with most operations, for example, image sequences or AviSynth scripts.

.. warning::

    The MoviePy backend is still under development and is not included with current Windows distribution. To enable MoviePy support, you must install PySceneDetect using `python` and `pip`.

This backend can be used by specifying ``-b moviepy`` via command line, or setting ``backend = moviepy`` under the ``[global]`` section of your :ref:`config file <scenedetect_cli-config_file>`.
