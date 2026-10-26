
.. _scenedetect-platform:

------------------
Platform & Logging
------------------

.. automodule:: scenedetect.platform
   :no-members:


Logging
-------

PySceneDetect outputs messages to a logger named ``pyscenedetect`` which does not have any default handlers. You can use :func:`scenedetect.init_logger <scenedetect.platform.init_logger>` with ``show_stdout=True`` or specify a log file (verbosity can also be specified) to attach some common handlers, or use ``logging.getLogger("pyscenedetect")`` and attach log handlers manually.

.. seealso:: CLI: :option:`-v/--verbosity <scenedetect -v>`, :option:`-l/--logfile <scenedetect -l>`, :option:`-q/--quiet <scenedetect -q>`

.. autofunction:: scenedetect.platform.init_logger


System Information
------------------

.. seealso:: CLI: :ref:`version <command-help>`

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
