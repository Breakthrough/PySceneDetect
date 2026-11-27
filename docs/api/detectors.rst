
.. _scenedetect-detectors:

---------
Detectors
---------

.. automodule:: scenedetect.detectors

.. seealso:: Scene cut detectors are available as ``detect-*`` commands in the :ref:`CLI reference <cli-detectors>`. The :option:`-m/--min-scene-len <scenedetect -m>` option sets their minimum scene length. Use :ref:`list-solid <command-list-solid>` to locate runs of solid-color frames.

.. note::

    **Defaults that differ between the CLI and Python:** ``min_scene_len`` defaults to ``15``
    frames in Python, while the CLI default is ``0.6s`` (the global
    :option:`-m/--min-scene-len <scenedetect -m>`, which each detector's ``-m`` overrides).
    ``detect-threshold`` also adds a final scene and ignores fades shorter than ``0.1s`` by
    default, while ``ThresholdDetector`` does not. A few parameters are also renamed. The table
    under each detector marks these rows **DIFFERS** or **RENAMED**, and parameters that have
    no CLI option **API only**. Where the CLI (or the config file) spells the same
    value differently from Python, that spelling follows in parentheses.

AdaptiveDetector
----------------

.. seealso:: **Command Line:** :ref:`detect-adaptive <command-detect-adaptive>` | **Config File:** :ref:`[detect-adaptive] <config-detect-adaptive>`

.. automodule:: scenedetect.detectors.adaptive_detector
   :no-members:

.. include:: detector_options/detect-adaptive.inc

.. autoclass:: scenedetect.detectors.adaptive_detector.AdaptiveDetector
   :members:

ContentDetector
---------------

.. seealso:: **Command Line:** :ref:`detect-content <command-detect-content>` | **Config File:** :ref:`[detect-content] <config-detect-content>`

.. automodule:: scenedetect.detectors.content_detector
   :no-members:

.. include:: detector_options/detect-content.inc

.. autoclass:: scenedetect.detectors.content_detector.ContentDetector
   :members:

HashDetector
------------

.. seealso:: **Command Line:** :ref:`detect-hash <command-detect-hash>` | **Config File:** :ref:`[detect-hash] <config-detect-hash>`

.. automodule:: scenedetect.detectors.hash_detector
   :no-members:

.. include:: detector_options/detect-hash.inc

.. autoclass:: scenedetect.detectors.hash_detector.HashDetector
   :members:

HistogramDetector
-----------------

.. seealso:: **Command Line:** :ref:`detect-hist <command-detect-hist>` | **Config File:** :ref:`[detect-hist] <config-detect-hist>`

.. automodule:: scenedetect.detectors.histogram_detector
   :no-members:

.. include:: detector_options/detect-hist.inc

.. autoclass:: scenedetect.detectors.histogram_detector.HistogramDetector
   :members:

SolidColorDetector
------------------

.. seealso:: **Command Line:** :ref:`list-solid <command-list-solid>` | **Config File:** :ref:`[list-solid] <config-list-solid>`

For example, to find solid-color sections lasting at least five frames:

.. code-block:: python

    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import SolidColorDetector

    detector = SolidColorDetector(min_frames=5)
    manager = SceneManager()
    manager.add_detector(detector)
    with open_video("recording.mp4") as video:
        manager.detect_scenes(video=video)
    for start, end in detector.get_intervals():
        print(start.get_timecode(), end.get_timecode(), (end - start).seconds)

The end time is exclusive. Adjacent solid frames belong to the same interval even
if their colors differ. Use a lower threshold to distinguish low-contrast detail
from a blank screen. To preserve fine detail during analysis, set
``manager.auto_downscale = False`` and ``manager.downscale = 1`` before detection.
On variable-frame-rate input, use timecodes for boundaries. The scene CSV's frame
numbers use the nominal frame rate. A run ending at the last observed frame uses
one nominal frame duration to estimate its exclusive end.

.. autoclass:: scenedetect.detectors.solid_color_detector.SolidColorDetector
   :members:

ThresholdDetector
-----------------

.. seealso:: **Command Line:** :ref:`detect-threshold <command-detect-threshold>` | **Config File:** :ref:`[detect-threshold] <config-detect-threshold>`

.. automodule:: scenedetect.detectors.threshold_detector
   :no-members:

.. include:: detector_options/detect-threshold.inc

.. autoclass:: scenedetect.detectors.threshold_detector.ThresholdDetector
   :members:
