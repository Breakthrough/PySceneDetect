
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

Run ``scenedetect --help`` to see the exact path on your system which will be used.  Values set on the command line take precedence over those set in the config file.  Most (but not all) command line parameters can be set using a configuration file, and some options can *only* be set using a config file. The :ref:`Sections <config_file-sections>` reference below lists every key with its default and the matching command-line option.  Note that lines starting with a ``#`` are comments and will be ignored.

The syntax of a configuration file is:

.. code:: ini

    [command]
    option_a = value
    #comment
    option_b = 1


=======================================================================
Sample File
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


.. _config_file-sections:

=======================================================================
Sections
=======================================================================

Every section of the config file, its keys and defaults, and the part of the ``scenedetect.cfg`` template that documents them. The complete template can be `downloaded from Github <https://github.com/Breakthrough/PySceneDetect/blob/main/scenedetect.cfg>`_ and used as a config file as-is (every key is commented out). Values shown in the template are the defaults, or an example where the default is unset.

.. include:: config_sections.inc
