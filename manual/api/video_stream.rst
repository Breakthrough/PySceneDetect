
.. _scenedetect-video_stream:

---------------------------------------------------------------
VideoStream
---------------------------------------------------------------

.. automodule:: scenedetect.video_stream


===============================================================
Usage Example
===============================================================

A :py:func:`VideoStream <scenedetect.video_stream.VideoStream>` is not used directly, but by constructing a concrete implementation from :py:module:`scenedetect.backends`. In most cases where any backend is acceptable, the :py:func:`scenedetect.backends.open_video` function can be used.

Assuming we have a file `video.mp4` in our working directory, we can load it and iterate through all of the frames:

.. code:: python

    from scenedetect.backends import open_video
    video = open_video(path='video.mp4')
    while True:
        frame = video.read()
        if frame == False:
            break
    print("Read %d frames" % video.frame_number)

If we want to use a specific backend, we can pass it to :py:func:`open_video <scenedetect.backends.open_video>`:

.. code:: python

    # Specifying a backend via `open_video`:
    from scenedetect.backends import open_video
    video = open_video(path='video.mp4', backend='opencv')

Or we can import and use specific backend directly:

    # Manually importing and constructing a backend:
    from scenedetect.backends.opencv import VideoStreamCv2
    video = VideoStreamCv2(path_or_device='video.mp4')

Backends available on the current system are populated in the `scenedetect.backends.AVAILABLE_BACKENDS` dict, which maps each backend's name to its corresponding type (e.g. {`'opencv': VideoStreamCv2`, ...}).  See the :py:module:`scenedetect.backends` for more information on available backends.  Note that the `'opencv'` backend (:py:class:`VideoStreamCv2 <scenedetect.backends.opencv.VideoStreamCv2>`) is guaranteed to exist).


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




