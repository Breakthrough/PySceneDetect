
.. _scenedetect_cli-config_file:

***********************************************************************
Configuration File
***********************************************************************

Most command line parameters can be set using a configuration file. See the :ref:`Template <config_file Template>` below for an example ``scenedetect.cfg`` file containing every possible option, along with comments that describe each one.  Note that lines starting with a ``#`` are comments and will be ignored.

PySceneDetect looks for a file named ``scenedetect.cfg`` in one of the following locations:

 * Windows:
     * ``C:/Users/%USERNAME%/AppData/Local/PySceneDetect/scenedetect.cfg``

 * Linux:
     * ``~/.config/PySceneDetect/scenedetect.cfg``
     * ``$XDG_CONFIG_HOME/scenedetect.cfg``

 * Mac:
     * ``~/Library/Preferences/PySceneDetect/scenedetect.cfg``

Run `scenedetect help` to see the exact path on your system which will be used. You can also specify the direct path to a config file using the ``-c``/``--config`` argument. Values set on the command line take precedence over those set in the config file.

The syntax of a configuration file is:

.. code:: ini

    [command]
    option_a = value
    #comment
    option_b = 1


=======================================================================
Example
=======================================================================

.. code:: ini

    [global]
    min-scene-len = 0.8s

    [detect-content]
    threshold = 26

    [split-video]
    preset = slow
    rate-factor = 17
    # Don't need to use quotes even if filename contains spaces
    filename = $VIDEO_NAME-Clip-$SCENE_NUMBER

    [save-images]
    format = jpeg
    quality = 80
    num-images = 3


.. _config_file Template:

=======================================================================
Template
=======================================================================

This template shows every possible configuration option and default values. It can be used as a ``scenedetect.cfg`` file. You can also `download it from Github <https://raw.githubusercontent.com/Breakthrough/PySceneDetect/v0.6/scenedetect.cfg>`_.

.. literalinclude:: ../../scenedetect.cfg
   :language: ini
