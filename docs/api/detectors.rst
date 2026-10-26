
.. _scenedetect-detectors:

---------
Detectors
---------

.. automodule:: scenedetect.detectors

.. seealso:: Each detector is also available as a ``detect-*`` command; see the ``detect-*`` commands in the :ref:`CLI reference <cli-detectors>`. The :option:`-m/--min-scene-len <scenedetect -m>` option sets ``min_scene_len`` for every detector.

.. note::

    **Defaults that differ between the CLI and Python:** ``min_scene_len`` defaults to ``15``
    frames in Python, while the CLI default is ``0.6s`` (the global
    :option:`-m/--min-scene-len <scenedetect -m>`, which each detector's ``-m`` overrides).
    ``detect-threshold`` also adds a final scene and ignores fades shorter than ``0.1s`` by
    default, while ``ThresholdDetector`` does not. A few parameters are also renamed. The table
    under each detector marks these rows **DIFFERS** or **RENAMED**, and parameters that have
    no CLI option **API only**. Where the CLI (or, for flags, the config file) spells the same
    value differently from Python, that spelling follows in parentheses.

AdaptiveDetector
----------------

.. seealso:: CLI: :ref:`detect-adaptive <command-detect-adaptive>` | Config file: :ref:`[detect-adaptive] <config-detect-adaptive>`

.. automodule:: scenedetect.detectors.adaptive_detector
   :no-members:

.. include:: detector_options/detect-adaptive.inc

.. autoclass:: scenedetect.detectors.adaptive_detector.AdaptiveDetector
   :members:

ContentDetector
---------------

.. seealso:: CLI: :ref:`detect-content <command-detect-content>` | Config file: :ref:`[detect-content] <config-detect-content>`

.. automodule:: scenedetect.detectors.content_detector
   :no-members:

.. include:: detector_options/detect-content.inc

.. autoclass:: scenedetect.detectors.content_detector.ContentDetector
   :members:

HashDetector
------------

.. seealso:: CLI: :ref:`detect-hash <command-detect-hash>` | Config file: :ref:`[detect-hash] <config-detect-hash>`

.. automodule:: scenedetect.detectors.hash_detector
   :no-members:

.. include:: detector_options/detect-hash.inc

.. autoclass:: scenedetect.detectors.hash_detector.HashDetector
   :members:

HistogramDetector
-----------------

.. seealso:: CLI: :ref:`detect-hist <command-detect-hist>` | Config file: :ref:`[detect-hist] <config-detect-hist>`

.. automodule:: scenedetect.detectors.histogram_detector
   :no-members:

.. include:: detector_options/detect-hist.inc

.. autoclass:: scenedetect.detectors.histogram_detector.HistogramDetector
   :members:

ThresholdDetector
-----------------

.. seealso:: CLI: :ref:`detect-threshold <command-detect-threshold>` | Config file: :ref:`[detect-threshold] <config-detect-threshold>`

.. automodule:: scenedetect.detectors.threshold_detector
   :no-members:

.. include:: detector_options/detect-threshold.inc

.. autoclass:: scenedetect.detectors.threshold_detector.ThresholdDetector
   :members:
