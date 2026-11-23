
.. _scenedetect_cli-config_file:

***********************************************************************
Configuration File
***********************************************************************

Specify a config file with ``-c`` / ``--config``. If you do not pass ``-c``, PySceneDetect looks for ``scenedetect.cfg`` in one of these locations:

 * Windows:
     * ``C:/Users/%USERNAME%/AppData/Local/PySceneDetect/scenedetect.cfg``

 * Linux:
     * ``~/.config/PySceneDetect/scenedetect.cfg``
     * ``$XDG_CONFIG_HOME/PySceneDetect/scenedetect.cfg``

 * macOS:
     * ``~/Library/Application Support/PySceneDetect/scenedetect.cfg``

Run ``scenedetect --help`` to see the exact path on your system. Command-line options override values in the config file. Most CLI options can be set in a config file, and some options are config-file only. The :ref:`Sections <config_file-sections>` reference below lists every key, its default value, and its matching CLI option. Lines starting with ``#`` are comments and are ignored.

The syntax of a config file is:

.. code:: ini

    [command]
    option_a = value
    # comment
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

Every section of the config file, its keys and defaults, and the matching part of the ``scenedetect.cfg`` template. You can `download the complete template from GitHub <https://github.com/Breakthrough/PySceneDetect/blob/latest/scenedetect.cfg>`_ and use it directly (every key is commented out). Values shown in the template are defaults, or examples where the default is unset.

.. include:: config_sections.inc
