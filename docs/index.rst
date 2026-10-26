.. PySceneDetect documentation index file (contains toctree directive).
    Copyright (C) 2014 Brandon Castellano.  All rights reserved.

#######################################################################
PySceneDetect Documentation
#######################################################################

PySceneDetect finds scene changes in video (fast cuts and fades) and can split the video, save
frames, or export the scene list. Use it as the ``scenedetect`` command, or as the
``scenedetect`` Python package.

Install with ``pip install scenedetect`` (``pip install scenedetect-headless`` on servers without
GUI libraries), or download the Windows build from
`scenedetect.com/download <https://www.scenedetect.com/download/>`_. Splitting video requires
``ffmpeg`` (or ``mkvmerge`` with ``split-video -m``); the Windows build bundles both.

=======================================================================
Quick Start
=======================================================================

From the command line, find the scenes in ``video.mp4`` and write one clip per scene:

.. code:: bash

    scenedetect -i video.mp4 split-video

Add ``list-scenes`` for a CSV, ``save-images`` for still frames, or a ``detect-*`` command to
pick the detector. See the :doc:`CLI reference <cli>`.

The same from Python:

.. code:: python

    from scenedetect import detect, ContentDetector, split_video_ffmpeg

    scenes = detect("video.mp4", ContentDetector())
    split_video_ffmpeg("video.mp4", scenes)

``scenes`` is a list of ``(start, end)`` timecode pairs. More :doc:`examples`, each done both
ways, cover images, CSV output, detector tuning and more; see :ref:`SceneManager
<scenedetect-scene_manager>` for advanced workflows.

=======================================================================
Reference
=======================================================================

Most features exist on both sides. The :doc:`examples` page shows each task done both ways,
and every page links to its counterpart on the other side: each command to the function or
class that does the same, and each detector to a table of its options, config file keys and
constructor parameters.

.. The toctrees are hidden so that the singlehtml build does not inline every document into
   the two columns; the sidebar extension reads them by their :name:.

.. container:: surfaces

   .. container:: surface

      .. rubric:: CLI

      .. include:: cli_index.inc

   .. container:: surface

      .. rubric:: Python API

      - :doc:`api`
      - :doc:`api/detectors`: :class:`~scenedetect.detectors.AdaptiveDetector`,
        :class:`~scenedetect.detectors.ContentDetector`,
        :class:`~scenedetect.detectors.HashDetector`,
        :class:`~scenedetect.detectors.HistogramDetector`,
        :class:`~scenedetect.detectors.ThresholdDetector`
      - :doc:`api/output`
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

Found a problem in the docs? Raise an issue on
`the PySceneDetect issue tracker <https://github.com/Breakthrough/PySceneDetect/issues>`_.
Development happens on Github at
`github.com/Breakthrough/PySceneDetect <https://github.com/Breakthrough/PySceneDetect>`_.

=======================================================================
Indices and Tables
=======================================================================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
