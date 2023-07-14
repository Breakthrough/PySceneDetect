
.. _scenedetect_cli-config_file:

***********************************************************************
Configuration File
***********************************************************************

A configuration file path can be specified using the ``-c``/``--config`` argument. PySceneDetect also looks for a config file named `scenedetect.cfg` in one of the following locations:

 * Windows:
     * ``C:/Users/%USERNAME%/AppData/Local/PySceneDetect/scenedetect.cfg``

 * Linux:
     * ``~/.config/PySceneDetect/scenedetect.cfg``
     * ``$XDG_CONFIG_HOME/scenedetect.cfg``

 * Mac:
     * ``~/Library/Preferences/PySceneDetect/scenedetect.cfg``

Run `scenedetect --help` to see the exact path on your system which will be used.  Values set on the command line take precedence over those set in the config file.  Most (but not all) command line parameters can be set using a configuration file, and some options can *only* be set using a config file. See the :ref:`Template <config_file Template>` below for a ``scenedetect.cfg`` file that describes each option, which you can use to create a new config file.  Note that lines starting with a ``#`` are comments and will be ignored.

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
    default-detector = detect-content
    min-scene-len = 0.8s

    [detect-content]
    threshold = 26

    [split-video]
    # Use higher quality encoding
    preset = slow
    rate-factor = 17
    filename = $VIDEO_NAME-Clip-$SCENE_NUMBER

    [save-images]
    format = jpeg
    quality = 80
    num-images = 3


.. _config_file Template:

=======================================================================
Template
=======================================================================

This template shows every possible configuration option and default values. It can be used as a ``scenedetect.cfg`` file. You can also `download it from Github <https://raw.githubusercontent.com/Breakthrough/PySceneDetect/v0.6.1-release/scenedetect.cfg>`_.

.. literalinclude:: ../../scenedetect.cfg
   :language: ini
