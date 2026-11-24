.. PySceneDetect documentation index file (contains toctree directive).
    Copyright (C) 2014 Brandon Castellano.  All rights reserved.

#######################################################################
PySceneDetect Reference Manual
#######################################################################

PySceneDetect finds scene changes in video (fast cuts and fades) and can split the video, save
frames, or export the scene list. Use it as the ``scenedetect`` command, or as the
``scenedetect`` Python package.

Install with ``pip install scenedetect`` (``pip install scenedetect-headless`` on servers without
GUI libraries), or download the Windows build from
`scenedetect.com/download <https://www.scenedetect.com/download/>`_. Splitting video requires
``ffmpeg`` (or ``mkvmerge`` with ``split-video -m``); the Windows build includes ``ffmpeg``.

=======================================================================
Quick Start
=======================================================================

From the command line, find the scenes in ``video.mp4`` and write one clip per scene:

.. code:: bash

    scenedetect -i video.mp4 split-video

Add ``list-scenes`` for a CSV, ``save-images`` for still frames, or a ``detect-*`` command to
pick the detector (default: ``detect-adaptive``). See the :doc:`CLI reference <cli>`.

The same from Python:

.. code:: python

    from scenedetect import detect, AdaptiveDetector, split_video_ffmpeg

    scenes = detect("video.mp4", AdaptiveDetector())
    split_video_ffmpeg("video.mp4", scenes)

``scenes`` is a list of ``(start, end)`` timecode pairs. See :doc:`examples` for side-by-side CLI
and Python examples (saving images, CSV output, tuning detectors, and more), or
:ref:`SceneManager <scenedetect-scene_manager>` for advanced workflows.

=======================================================================
Reference
=======================================================================

Most features work in both the CLI and the Python API. The :doc:`examples` page shows each task
both ways, and each reference page links to its counterpart across CLI commands, config file keys,
and Python functions or classes.

.. The toctrees are hidden so that the singlehtml build does not inline every document into
   the two columns; the sidebar extension reads them by their :name:.

.. container:: surfaces

   .. container:: surface

      .. rubric:: CLI

      .. include:: cli_index.inc

   .. container:: surface

      .. rubric:: Python API

      - :doc:`api`

        - :func:`~scenedetect.detect`
        - :func:`~scenedetect.open_video`

      - :doc:`api/detectors`

        - **Fast Cuts**

          - :class:`~scenedetect.detectors.adaptive_detector.AdaptiveDetector`
          - :class:`~scenedetect.detectors.content_detector.ContentDetector`
          - :class:`~scenedetect.detectors.hash_detector.HashDetector`
          - :class:`~scenedetect.detectors.histogram_detector.HistogramDetector`

        - **Other**

          - :class:`~scenedetect.detectors.threshold_detector.ThresholdDetector`

      - :doc:`api/output`

        - **Splitting & Images**

          - :func:`~scenedetect.output.split_video_ffmpeg`
          - :func:`~scenedetect.output.split_video_mkvmerge`
          - :func:`~scenedetect.output.save_images`

        - **Scene Lists & Exports**

          - :func:`~scenedetect.output.write_scene_list`
          - :func:`~scenedetect.output.write_scene_list_html`
          - :func:`~scenedetect.output.write_scene_list_edl`
          - :func:`~scenedetect.output.write_scene_list_fcpx`
          - :func:`~scenedetect.output.write_scene_list_fcp7`
          - :func:`~scenedetect.output.write_scene_list_otio`

      - :doc:`api/backends`
      - :doc:`api/common`
      - :doc:`api/scene_manager`
      - :doc:`api/detector`
      - :doc:`api/video_stream`
      - :doc:`api/stats_manager`
      - :doc:`api/platform`
      - :doc:`api/migration_guide`

.. toctree::
    :hidden:
    :caption: CLI
    :name: clitoc

    cli
    cli/config_file
    cli/backends

.. toctree::
    :hidden:
    :caption: Python API
    :name: apitoc

    api
    api/detectors
    api/output
    api/backends
    api/common
    api/scene_manager
    api/detector
    api/video_stream
    api/stats_manager
    api/platform
    api/migration_guide

.. toctree::
    :hidden:
    :caption: Guides
    :name: reftoc

    examples

Found a problem in the docs? Open an issue on
`the PySceneDetect issue tracker <https://github.com/Breakthrough/PySceneDetect/issues>`_.
Development happens on GitHub at
`github.com/Breakthrough/PySceneDetect <https://github.com/Breakthrough/PySceneDetect>`_.

=======================================================================
Indices and Tables
=======================================================================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
