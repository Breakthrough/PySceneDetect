
.. _scenedetect-video_manager:

---------------------------------------------------------------
VideoManager
---------------------------------------------------------------

.. automodule:: scenedetect.video_manager


===============================================================
Usage Example
===============================================================

Assuming we have a file `video.mp4`, we can load it and iterate through the
first 2 minutes using the default downscale factor as follows.

We start by creating a :py:class:`VideoManager` and getting the base FrameTimecode:

.. code:: python

    video_manager = VideoManager(['video.mp4'])
    base_timecode = video_manager.get_base_timecode()

Note that the first argument to the :py:class:`VideoManager` constructor is a *list* of
video files to open.  Any number of videos can be *appended* by adding more
paths to the list, however, each video must have the same framerate and
resolution.

.. tip::

    If the video framerates differ slightly, supply the ``framerate``
    argument to override the framerate check:

    .. code:: python

        video_manager = VideoManager(['video1.mp4', 'video2.mp4'],
                                     framerate=23.976)
        # base_timecode will have a framerate of 23.976 now.
        base_timecode = video_manager.get_base_timecode()


Next, we set the duration to 2 minutes and the downscale factor to the default
based on video resolution:

.. code:: python

    video_manager.set_duration(duration=base_timecode + '00:02:00')
    video_manager.set_downscale_factor()

:py:meth:`set_duration() <VideoManager.set_duration>` takes up to two arguments of
``start_time``, ``end_time``, and ``duration``, where ``end_time`` and ``duration``
are mutually exclusive.  Each argument should be a
:py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>` object.

Note that if you are using a :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>`
and set the ``start_time`` argument of :py:meth:`VideoManager.set_duration`,
you must pass set the same ``start_time`` argument to the
:py:meth:`SceneManager.detect_scenes() <scenedetect.scene_manager.SceneManager.detect_scenes>`
method.

After calling the above, the number of frames returned by the :py:class:`VideoManager`
will be limited to 2 minutes of video exactly, and setting the default downscale factor
ensures an adequate frame size for performing scene detection in most use cases.

.. warning::

    The :py:meth:`~VideoManager.set_duration` and :py:meth:`~VideoManager.set_downscale_factor`
    methods must be called **before** :py:meth:`~VideoManager.start`.

Now that all of our options have been set, we can call :py:meth:`VideoManager.start`
and begin processing frames the same way we would with an OpenCV VideoCapture object:

.. code:: python

    video_manager.start()
    while True:
        ret_val, frame_image = video_manager.read()
        if not ret_val:
            break
        # Do stuff with frame_image here.


Note that the :py:meth:`VideoManager.read`, :py:meth:`VideoManager.grab` and
:py:meth:`VideoManager.retrieve` methods all have the same prototypes and function
as their OpenCV counterparts.  Likewise, the frame image returned by these
methods is a standard Numpy ``ndarray`` which can be operated on as expected.

Lastly, when all processing is done, make sure to call :py:meth:`VideoManager.release`
to cleanup all resources acquired by the :py:class:`VideoManager` object.

.. hint::
    Use a ``try``/``finally`` block to ensure that the :py:meth:`~VideoManager.release`
    method is called.  For example:

    .. code:: python

        video_manager = VideoManager(['video.mp4'])
        try:
            video_manager.set_downscale_factor()
            video_manager.start()
            while True:
                if not video_manager.grab():
                    break
        finally:
            # Ensures release() is called even if an exception
            # is thrown during any code added to process frames.
            video_manager.release()



When passing a :py:class:`VideoManager` to a
:py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` class, the
:py:meth:`~VideoManager.start` method must already have been called.  See the
:ref:`example in the SceneManager reference<scenemanager-example>` for more details.


``VideoManager`` Class
===============================================================

.. autoclass:: scenedetect.video_manager.VideoManager
   :members:
   :undoc-members:

``video_manager`` Functions and Constants
===============================================================

The following functions and constants are available in the ``scenedetect.video_manager`` module.

.. autodata:: scenedetect.video_manager.DEFAULT_DOWNSCALE_FACTORS

.. autofunction:: scenedetect.video_manager.compute_downscale_factor

.. autofunction:: scenedetect.video_manager.get_video_name

.. autofunction:: scenedetect.video_manager.get_num_frames

.. autofunction:: scenedetect.video_manager.open_captures

.. autofunction:: scenedetect.video_manager.validate_capture_framerate

.. autofunction:: scenedetect.video_manager.validate_capture_parameters


Exceptions
===============================================================

.. autoexception:: scenedetect.video_manager.InvalidDownscaleFactor

.. autoexception:: scenedetect.video_manager.VideoOpenFailure

.. autoexception:: scenedetect.video_manager.VideoFramerateUnavailable

.. autoexception:: scenedetect.video_manager.VideoParameterMismatch

.. autoexception:: scenedetect.video_manager.VideoDecodingInProgress

.. autoexception:: scenedetect.video_manager.VideoDecoderNotStarted


