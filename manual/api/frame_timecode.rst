
FrameTimecode
----------------------------------------------

.. automodule:: scenedetect.frame_timecode


Usage Examples
=========================================

A :py:class:`FrameTimecode` can be created by specifying the frame number as an integer, along
with the framerate:

.. code:: python

    x = FrameTimecode(timecode = 0, fps = 29.97)


It can also be created from a floating-point number of seconds.  Note that calling
:py:meth:`x.get_frames() <FrameTimecode.get_frames>` will return 200 in this case (10.0 seconds at 20.0 frames/sec):

.. code:: python

    x = FrameTimecode(timecode = 10.0, fps = 20.0)


``timecode`` can also be specified as a string in "HH:MM:SS[.nnn]" format.  Note that
calling :py:meth:`x.get_frames() <FrameTimecode.get_frames>` will return 600 in this
case (1 minute, or 60 seconds, at 10 frames/sec):

.. code:: python

    x = FrameTimecode(timecode = "00:01:00.000", fps = 10.0)


:py:class:`FrameTimecode` objects can be added and subtracted.  Note, however, that a negative
timecode is not representable by a :py:class:`FrameTimecode`, and subtractions towards/past zero
will wrap at zero.

.. warning::

    Be careful when subtracting :py:class:`FrameTimecode` objects.
    In the example below, ``c`` will be at time 0 since ``b > a``,
    but ``d`` will be at frame 15:

    .. code:: python

        a = FrameTimecode(5, 10.0)
        b = FrameTimecode(10, 10.0)
        c = a - b   # b > a, so c == 0
        d = b - a
        print(c)
        print(d)



``FrameTimecode`` Class
=========================================

.. autoclass:: scenedetect.frame_timecode.FrameTimecode
   :members:
   :undoc-members:

