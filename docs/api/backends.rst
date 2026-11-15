
.. _scenedetect-backends:

--------------
Video Backends
--------------

.. seealso:: CLI: :option:`-b/--backend <scenedetect -b>` and :ref:`Backends <cli-backends>` | Config file: :ref:`[global] backend <config-global>`

.. automodule:: scenedetect.backends
   :no-members:


Opening Videos
--------------

:func:`scenedetect.open_video` opens a video with any backend listed in :data:`AVAILABLE_BACKENDS <scenedetect.backends.AVAILABLE_BACKENDS>`, falling back to OpenCV. Each backend below can also be constructed directly.

.. autodata:: scenedetect.backends.AVAILABLE_BACKENDS


OpenCV
------

.. seealso:: CLI: :ref:`-b opencv <cli-backend-opencv>` | Config file: :ref:`[backend-opencv] <config-backend-opencv>`

.. automodule:: scenedetect.backends.opencv
   :no-members:

.. autoclass:: scenedetect.backends.opencv.VideoStreamCv2
   :members:

.. autoclass:: scenedetect.backends.opencv.VideoCaptureAdapter
   :members:


PyAV
----

.. seealso:: CLI: :ref:`-b pyav <cli-backend-pyav>` | Config file: :ref:`[backend-pyav] <config-backend-pyav>`

.. automodule:: scenedetect.backends.pyav
   :no-members:

.. autoclass:: scenedetect.backends.pyav.VideoStreamAv
   :members:


MoviePy
-------

.. seealso:: CLI: :ref:`-b moviepy <cli-backend-moviepy>`

.. automodule:: scenedetect.backends.moviepy
   :no-members:

.. autoclass:: scenedetect.backends.moviepy.VideoStreamMoviePy
   :members:


Multiple Videos
---------------

.. automodule:: scenedetect.backends.concat
   :no-members:

.. autoclass:: scenedetect.backends.concat.VideoStreamConcat
   :members:

.. autoclass:: scenedetect.backends.concat.SourceSpan
   :members:


Constants
---------

.. autodata:: scenedetect.backends.pyav.MAX_CONSECUTIVE_DECODE_FAILURES

.. autodata:: scenedetect.backends.concat.FRAMERATE_DELTA_TOLERANCE
