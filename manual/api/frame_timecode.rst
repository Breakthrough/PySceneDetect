
.. _scenedetect-frame_timecode:

---------------------------------------------------------------
FrameTimecode
---------------------------------------------------------------

.. automodule:: scenedetect.frame_timecode


===============================================================
Usage Examples
===============================================================

A :py:class:`FrameTimecode` can be created by specifying a timecode (`int` for number of frames, `float` for number of seconds, or `str` in the form "HH:MM:SS" or "HH:MM:SS.nnn") with a framerate:

.. code:: python

    frames = FrameTimecode(timecode = 29, fps = 29.97)
    seconds_float = FrameTimecode(timecode = 10.0, fps = 10.0)
    timecode_str = FrameTimecode(timecode = "00:00:10.000", fps = 10.0)


Arithmetic/comparison operations with :py:class:`FrameTimecode` objects is also possible,
and the other operand can also be of the above types:

.. code:: python

    x = FrameTimecode(timecode = "00:01:00.000", fps = 10.0)
    # Can add int (frames), float (seconds), or str (timecode).
    print(x + 10)
    print(x + 10.0)
    print(x + "00:10:00")
    # Same for all comparison operators.
    print((x + 10.0) == "00:01:10.000")


:py:class:`FrameTimecode` objects can be added and subtracted, however the current implementation disallows negative values, and will clamp negative results to 0.

.. warning::

    Be careful when subtracting :py:class:`FrameTimecode` objects or adding negative
    amounts of frames/seconds. In the example below, ``c`` will be at frame 0 since
    ``b > a``, but ``d`` will be at frame 5:

    .. code:: python

        a = FrameTimecode(5, 10.0)
        b = FrameTimecode(10, 10.0)
        c = a - b   # b > a, so c == 0
        d = b - a
        assert(c == 0)
        assert(d == 5)

===============================================================
``FrameTimecode`` Class
===============================================================

.. autoclass:: scenedetect.frame_timecode.FrameTimecode
   :members:
   :undoc-members:

===============================================================
Constants
===============================================================

.. autodata:: scenedetect.frame_timecode.MAX_FPS_DELTA
