
.. _cli-backends:

***********************************************************************
Backends
***********************************************************************

PySceneDetect supports multiple backends for video input. Some can be configured by using :ref:`a config file <scenedetect_cli-config_file>`.


=======================================================================
OpenCV
=======================================================================

*[Default on Linux/OSX]*

This backend, named ``opencv`` on the command line, uses OpenCV's VideoCapture object for video input. It is mostly reliable and fast, although can occasionally run into issues processing videos with multiple audio tracks or small amounts of frame corruption.

The OpenCV backend also supports image sequences as inputs (e.g. ``frame%02d.jpg`` if you want to load frame001.jpg, frame002.jpg, frame003.jpg...). Make sure to specify the framerate manually (``-f``/``--framerate``) to ensure accurate timing calculations.


=======================================================================
PyAV
=======================================================================

*[Default on Windows]*

The PyAV backend is a more robust and faster backend that supports multithreaded decoding.

On Linux, the PyAV backend uses a slower threading mode by default (`threading-mode = slice`). Using the faster mode (`threading-mode = auto`) can cause the program to not quit properly, requiring Ctrl + C to fully stop it. For most use cases this does not affect anything, but it can be a problem if you are using the `scenedetect` command as part of a script.

If you wish to enable the faster threading mode, create/specify :ref:`a config file <scenedetect_cli-config_file>`, and set the following option:

.. code:: ini

    [backend-pyav]
    threading-mode = auto

Using this mode on Linux/OSX is not suggested for applications requiring the program to terminate gracefully. If required, your application should monitor the progress of the *scenedetect* command for the last expected log message. The command is then safe to terminate if it is still running after a few more seconds.
