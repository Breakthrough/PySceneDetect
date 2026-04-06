
.. _scenedetect-migration-guide:

***********************************************************************
Migration Guide: v0.6 to v0.7
***********************************************************************

PySceneDetect v0.7 is a major release that overhauls timestamp handling to support variable framerate (VFR) videos. While the high-level :func:`scenedetect.detect` workflow is largely unchanged, several internal APIs have been restructured. This guide covers the changes needed to update applications from v0.6 to v0.7.

The minimum supported Python version is now **Python 3.10**.


=======================================================================
Quick Check
=======================================================================

If your code only uses :func:`scenedetect.detect` with a built-in detector, it should work without changes:

.. code:: python

    # This still works in v0.7
    from scenedetect import detect, ContentDetector
    scenes = detect("video.mp4", ContentDetector())


=======================================================================
Import Changes
=======================================================================

Several submodules have been reorganized. If you import directly from `scenedetect` you do not need to make any changes. Update imports as follows:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - v0.6
     - v0.7
   * - ``from scenedetect.frame_timecode import FrameTimecode``
     - ``from scenedetect.common import FrameTimecode``
   * - ``from scenedetect.scene_detector import SceneDetector``
     - ``from scenedetect.detector import SceneDetector``
   * - ``from scenedetect.video_splitter import split_video_ffmpeg``
     - ``from scenedetect.output import split_video_ffmpeg``
   * - ``from scenedetect.video_splitter import split_video_mkvmerge``
     - ``from scenedetect.output import split_video_mkvmerge``
   * - ``from scenedetect.scene_manager import save_images``
     - ``from scenedetect.output import save_images``
   * - ``from scenedetect.scene_manager import write_scene_list``
     - ``from scenedetect.output import write_scene_list``
   * - ``from scenedetect.scene_manager import write_scene_list_html``
     - ``from scenedetect.output import write_scene_list_html``
   * - ``from scenedetect.video_manager import VideoManager``
     - Removed. Use :func:`scenedetect.open_video` instead.

.. note::

    Most commonly used types and functions are also available directly from the top-level ``scenedetect`` package (e.g. ``from scenedetect import FrameTimecode``), which has not changed.


=======================================================================
Custom Detector Changes
=======================================================================

If you have written a custom :class:`SceneDetector <scenedetect.detector.SceneDetector>` subclass, there are several interface changes.

``process_frame`` Signature
-----------------------------------------------------------------------

The ``frame_num`` parameter (``int``) has been replaced with ``timecode`` (:class:`FrameTimecode <scenedetect.common.FrameTimecode>`):

.. code:: python

    # v0.6
    class MyDetector(SceneDetector):
        def process_frame(self, frame_num: int, frame_img) -> List[int]:
            ...

    # v0.7
    class MyDetector(SceneDetector):
        def process_frame(self, timecode: FrameTimecode, frame_img) -> List[FrameTimecode]:
            ...

The same change applies to ``post_process()``. If you need the frame number, use ``timecode.frame_num``.

``SceneDetector`` is Now Abstract
-----------------------------------------------------------------------

``SceneDetector`` is now a Python `abstract class <https://docs.python.org/3/library/abc.html>`_. Subclasses **must** implement ``process_frame()``.

Removed Methods and Properties
-----------------------------------------------------------------------

The following have been removed from the ``SceneDetector`` interface:

- ``is_processing_required()`` - detectors can now assume they always have frame data
- ``stats_manager_required`` property - no longer needed
- ``SparseSceneDetector`` interface - removed entirely


=======================================================================
``FrameTimecode`` Changes
=======================================================================

Read-Only Properties
-----------------------------------------------------------------------

``frame_num`` and ``framerate`` are now read-only properties. To change them, construct a new ``FrameTimecode``:

.. code:: python

    # v0.6 - direct assignment
    tc.frame_num = 100  # No longer works

    # v0.7 - construct new instance
    tc = FrameTimecode(100, tc.framerate)

New Properties
-----------------------------------------------------------------------

Access ``frame_num``, ``framerate``, and ``seconds`` as properties instead of getter methods:

.. code:: python

    tc = FrameTimecode(100, 24.0)
    tc.frame_num   # 100
    tc.framerate    # Fraction(24, 1)
    tc.seconds      # ~4.167

Removed Methods
-----------------------------------------------------------------------

- ``previous_frame()`` - removed, use ``FrameTimecode(tc.frame_num - 1, tc.framerate)`` instead


=======================================================================
Framerate and Timestamp Changes
=======================================================================

Rational Framerates
-----------------------------------------------------------------------

``VideoStream.frame_rate`` now returns a ``Fraction`` instead of ``float``. Common NTSC rates (23.976, 29.97, 59.94) are automatically detected from float values:

.. code:: python

    from fractions import Fraction
    video = open_video("video.mp4")
    assert isinstance(video.frame_rate, Fraction)
    # e.g. Fraction(24000, 1001) instead of 23.976023976...

PTS-Backed Timestamps
-----------------------------------------------------------------------

All backends now return presentation timestamp (PTS) backed values from ``VideoStream.position``. This enables correct handling of VFR videos.

``FrameTimecode`` has new ``time_base`` and ``pts`` properties for accessing the underlying timing information. For VFR videos, ``frame_num`` is now an approximation based on PTS-derived time rather than a sequential count.


=======================================================================
``StatsManager`` Changes
=======================================================================

The ``StatsManager`` methods ``get_metrics()``, ``set_metrics()``, and ``metrics_exist()`` now take a ``FrameTimecode`` instead of ``int`` for the frame identifier, matching the detector interface change.


=======================================================================
Removed APIs
=======================================================================

The following deprecated APIs have been fully removed in v0.7:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Removed
     - Replacement
   * - ``scenedetect.video_manager`` module
     - :func:`scenedetect.open_video`
   * - ``base_timecode`` parameter (various functions)
     - No longer needed, remove the argument
   * - ``video_manager`` parameter (various functions)
     - Use ``video`` parameter instead
   * - ``SceneManager.get_event_list()``
     - Use ``SceneManager.get_cut_list()`` or ``SceneManager.get_scene_list()``
   * - ``AdaptiveDetector.get_content_val()``
     - Use ``StatsManager`` to query metrics
   * - ``AdaptiveDetector(min_delta_hsv=...)``
     - Use ``min_content_val`` parameter instead
   * - ``VideoStream.read(advance=...)``
     - Call ``read()`` without the ``advance`` parameter
   * - ``SparseSceneDetector``
     - No direct replacement, use ``SceneDetector``

.. note::

    Deprecated v0.6 compatibility shims that still exist now emit warnings using the ``warnings`` module. Address any ``DeprecationWarning`` messages to prepare for future releases.


=======================================================================
CLI Changes
=======================================================================

- The ``-d``/``--min-delta-hsv`` option on ``detect-adaptive`` has been removed. Use ``-c``/``--min-content-val`` instead.
- VFR videos now work correctly with both the OpenCV and PyAV backends.
- New ``save-xml`` command for exporting scenes in Final Cut Pro XML format.
