
.. _scenedetect-video_stream:

---------------------------------------------------------------
VideoStream
---------------------------------------------------------------

.. automodule:: scenedetect.video_stream


===============================================================
Example
===============================================================

A :py:class:`VideoStream <scenedetect.video_stream.VideoStream>` is not used directly, but by
constructing a concrete implementation from :py:mod:`scenedetect.backends`.  For most use cases,
this can be done using the :py:func:`scenedetect.backends.open_video` function.  See the
:py:mod:`scenedetect.backends` documentation for an example.

For an example implementation of :py:class:`VideoStream <scenedetect.video_stream.VideoStream>`,
see :py:class:`VideoStreamCv2 <scenedetect.backends.opencv.VideoStreamCv2>` in the
:py:mod:`scenedetect.backends.opencv` module.

``VideoStream`` Class
===============================================================

.. autoclass:: scenedetect.video_stream.VideoStream
   :members:
   :undoc-members:


``video_stream`` Functions and Constants
===============================================================

The following functions and constants are available in the ``scenedetect.video_stream`` module.

.. autodata:: scenedetect.video_stream.DEFAULT_MIN_WIDTH

.. autofunction:: scenedetect.video_stream.compute_downscale_factor


Exceptions
===============================================================

.. autoexception:: scenedetect.video_stream.VideoOpenFailure

.. autoexception:: scenedetect.video_stream.SeekError




