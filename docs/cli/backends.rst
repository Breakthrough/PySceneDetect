
.. _cli-backends:

***********************************************************************
Video Backends
***********************************************************************

PySceneDetect supports modular video input backends. You can configure backend options in a :ref:`config file <scenedetect_cli-config_file>`. Run ``scenedetect version`` to see which backends are installed.

The ``scenedetect`` command generates outputs after scene detection finishes. Most output commands require an input that can be replayed, and preferably seeked. Some backends support network streams and other input types, but live streams require the Python API.


.. _cli-backend-opencv:

=======================================================================
OpenCV
=======================================================================

.. seealso:: Python API: :class:`~scenedetect.backends.opencv.VideoStreamCv2` | Config file: :ref:`[backend-opencv] <config-backend-opencv>`

*[Default]*
The `OpenCV <https://opencv.org/>`_ backend (usually `opencv-python <https://pypi.org/project/opencv-python/>`_) uses OpenCV's ``VideoCapture`` to decode video. Select it with ``-b opencv`` on the command line, or set ``backend = opencv`` under ``[global]`` in your :ref:`config file <scenedetect_cli-config_file>`.

OpenCV is fast and reliable for most files, though it can occasionally fail on videos with multiple audio tracks or minor frame corruption. You can use ``opencv-python``, ``opencv-python-headless``, or a custom ``cv2`` build.

The OpenCV backend also supports image sequences (for example, ``frame%02d.jpg`` to load ``frame001.jpg``, ``frame002.jpg``, ``frame003.jpg``, and so on). Set the frame rate manually with ``-f`` / ``--frame-rate`` so timecodes are accurate.

Variable frame rate (VFR) video is supported. Scene detection uses PTS-derived timestamps from ``CAP_PROP_POS_MSEC`` for accurate timecodes. Seeking compensates for OpenCV's average-fps seek approximation so output timecodes stay accurate across the full video.


.. _cli-backend-pyav:

=======================================================================
PyAV
=======================================================================

.. seealso:: Python API: :class:`~scenedetect.backends.pyav.VideoStreamAv` | Config file: :ref:`[backend-pyav] <config-backend-pyav>`

The `PyAV <https://github.com/PyAV-Org/PyAV>`_ backend (`av package <https://pypi.org/project/av/>`_) handles multiple audio tracks and frame decode errors more reliably than OpenCV.

Variable frame rate (VFR) video is fully supported. PyAV reads native PTS timestamps directly from the video container, giving the most accurate timecodes for VFR content.

Select this backend with ``-b pyav`` on the command line, or set ``backend = pyav`` under ``[global]`` in your :ref:`config file <scenedetect_cli-config_file>`.


.. _cli-backend-moviepy:

=======================================================================
MoviePy
=======================================================================

.. seealso:: Python API: :class:`~scenedetect.backends.moviepy.VideoStreamMoviePy`

MoviePy runs ``ffmpeg`` as a subprocess and supports many input types. Inputs that support seeking, such as image sequences or AviSynth scripts, work with most commands.

.. warning::

    The MoviePy backend is experimental and is not included in the Windows installer. To use it, install PySceneDetect with ``pip`` (``pip install "scenedetect[moviepy]"``).

    Variable frame rate (VFR) video is **not supported**. MoviePy assumes a constant frame rate, so timecodes for VFR content will be inaccurate. Use the PyAV or OpenCV backend instead.

Select this backend with ``-b moviepy`` on the command line, or set ``backend = moviepy`` under ``[global]`` in your :ref:`config file <scenedetect_cli-config_file>`.
