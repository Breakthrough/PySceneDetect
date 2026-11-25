
.. _scenedetect-platform:

------------------
Platform & Logging
------------------

.. automodule:: scenedetect.platform
   :no-members:

.. Public symbols are listed explicitly below by section; add new public helpers here.


Logging
-------

PySceneDetect writes log messages to the ``pyscenedetect`` logger, which has no default handlers. Call :func:`scenedetect.init_logger <scenedetect.platform.init_logger>` with ``show_stdout=True`` or a log file path to attach standard handlers, or configure ``logging.getLogger("pyscenedetect")`` directly.

.. seealso:: **Command Line:** :option:`-v/--verbosity <scenedetect -v>`, :option:`-l/--logfile <scenedetect -l>`, :option:`-q/--quiet <scenedetect -q>`

.. autofunction:: scenedetect.platform.init_logger


System Information
------------------

.. seealso:: **Command Line:** :ref:`version <command-help>`

.. autofunction:: scenedetect.platform.get_system_version_info


Files and Paths
---------------

.. autofunction:: scenedetect.platform.get_file_name

.. autofunction:: scenedetect.platform.get_and_create_path

.. autofunction:: scenedetect.platform.is_url

.. autoclass:: scenedetect.platform.Template
   :members:

.. autodata:: scenedetect.platform.StrPath

.. autodata:: scenedetect.platform.BytePath


External Tools
--------------

.. autofunction:: scenedetect.platform.get_ffmpeg_path

.. autofunction:: scenedetect.platform.get_ffmpeg_version

.. autofunction:: scenedetect.platform.get_mkvmerge_path

.. autofunction:: scenedetect.platform.get_mkvmerge_version

.. autofunction:: scenedetect.platform.invoke_command

.. autoexception:: scenedetect.platform.CommandTooLong
   :members:


Internals
---------

.. autodata:: scenedetect.platform.DEBUG_MODE

.. autofunction:: scenedetect.platform.get_cv2_imwrite_params

.. autoclass:: scenedetect.platform.FakeTqdmObject
   :members:

.. autoclass:: scenedetect.platform.FakeTqdmLoggingRedirect
   :members:
