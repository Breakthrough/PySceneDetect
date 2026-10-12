
.. _scenedetect-migration-guide:

***********************************************************************
Migration Guide (v0.7)
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

.. note::

    The ``frame_timecode``, ``scene_detector``, and ``video_splitter`` submodules emit a ``DeprecationWarning`` when imported directly. The ``save_images``, ``write_scene_list``, and ``write_scene_list_html`` re-exports from ``scenedetect.scene_manager`` continue to work silently in v0.7 but **will be removed in v0.8**. Import these symbols from ``scenedetect`` directly to avoid breakage.


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

The same change applies to ``post_process()``. Using units of time instead of frame numbers is critical for temporal accuracy. If you need the frame number, use ``timecode.frame_num`` to the timecode to an integer.

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

:attr:`~scenedetect.common.FrameTimecode.frame_num` and :attr:`~scenedetect.common.FrameTimecode.frame_rate` are now read-only properties. To change them, construct a new ``FrameTimecode``:

.. code:: python

    tc = FrameTimecode(0, 24.0)
    # Can no longer reassign frame_num, must create a new FrameTimecode instead:
    #tc.frame_num = 100
    tc = FrameTimecode(100, tc)

New Properties
-----------------------------------------------------------------------

Access :attr:`~scenedetect.common.FrameTimecode.frame_num`, :attr:`~scenedetect.common.FrameTimecode.frame_rate`, and :attr:`~scenedetect.common.FrameTimecode.seconds` as properties instead of getter methods. The new :attr:`~scenedetect.common.FrameTimecode.frame_rate` property returns an exact :class:`fractions.Fraction` and matches :attr:`~scenedetect.video_stream.VideoStream.frame_rate`:

.. code:: python

    from fractions import Fraction
    tc = FrameTimecode(100, 29.97)
    tc.frame_num    # 100
    tc.frame_rate   # Fraction(30000, 1001) (exact)
    tc.time_base    # Fraction(1001, 30000)
    tc.seconds      # ~3.337

``time_base`` equals ``1 / frame_rate`` for CFR sources. For VFR (``Timecode``-backed) instances, ``time_base`` is authoritative and ``frame_rate`` is an approximation.

``Fraction`` participates in numeric arithmetic and comparisons just like ``float``, and converts implicitly when mixed with floats (the result is a ``float``). When a ``float`` is explicitly required (e.g. format specifiers, ``json.dumps``, ``isinstance(x, float)`` checks) wrap the value with ``float(...)``:

.. code:: python

    rate = tc.frame_rate            # Fraction(30000, 1001)
    rate * 2                        # Fraction(60000, 1001)
    rate > 24                       # True
    rate * 0.5                      # 14.985... (float, mixed arithmetic)
    f"{float(rate):.3f}"            # '29.970' (explicit cast for format spec)

The legacy ``framerate`` property (one word, returns ``float``) is retained as a deprecated alias and will emit a ``DeprecationWarning`` in a future release. Migrate to ``frame_rate``; cast with ``float(...)`` at the call site if you specifically need a ``float``.

Renamed Method: ``equal_framerate()``
-----------------------------------------------------------------------

:meth:`~scenedetect.common.FrameTimecode.equal_framerate` has been renamed to :meth:`~scenedetect.common.FrameTimecode.equal_frame_rate` for consistency with the :attr:`~scenedetect.common.FrameTimecode.frame_rate` property. The legacy ``equal_framerate()`` method is retained as a deprecated alias and will emit a ``DeprecationWarning`` in a future release. The new form additionally accepts a ``Fraction`` or another ``FrameTimecode`` (in addition to ``float``).

Removed Methods
-----------------------------------------------------------------------

- ``previous_frame()`` - removed, use ``FrameTimecode(tc.frame_num - 1, tc)`` instead (passing a ``FrameTimecode`` as the ``fps`` argument reuses its rate)


=======================================================================
Framerate and Timestamp Changes
=======================================================================

Rational Framerates
-----------------------------------------------------------------------

:attr:`~scenedetect.video_stream.VideoStream.frame_rate` now returns a ``Fraction`` instead of ``float``. Common NTSC rates (23.976, 29.97, 59.94) are automatically detected from float values:

.. code:: python

    from fractions import Fraction
    video = open_video("video.mp4")
    assert isinstance(video.frame_rate, Fraction)
    # e.g. Fraction(24000, 1001) instead of 23.976023976...

``frame_rate`` Keyword Argument
-----------------------------------------------------------------------

The ``framerate`` keyword argument has been renamed to ``frame_rate`` on :func:`~scenedetect.open_video` and on every backend constructor (:class:`~scenedetect.backends.opencv.VideoStreamCv2`, :class:`~scenedetect.backends.opencv.VideoCaptureAdapter`, :class:`~scenedetect.backends.pyav.VideoStreamAv`, :class:`~scenedetect.backends.moviepy.VideoStreamMoviePy`). The new form accepts ``float | Fraction | None``. The legacy ``framerate`` keyword is retained as a deprecated alias and will emit a ``DeprecationWarning`` in a future release; if both are supplied, ``frame_rate`` takes precedence.

.. code:: python

    # v0.6 - will still work but will be removed in a future version
    video = open_video("video.mp4", framerate=30.0)

    # v0.7
    video = open_video("video.mp4", frame_rate=30.0)

PTS-Backed Timestamps
-----------------------------------------------------------------------

All backends now return presentation timestamp (PTS) backed values from :attr:`~scenedetect.video_stream.VideoStream.position`. This enables correct handling of VFR videos.

``FrameTimecode`` has new :attr:`~scenedetect.common.FrameTimecode.time_base` and :attr:`~scenedetect.common.FrameTimecode.pts` properties for accessing the underlying timing information. For VFR videos, :attr:`~scenedetect.common.FrameTimecode.frame_num` is now an approximation based on PTS-derived time rather than a sequential count.


=======================================================================
``StatsManager`` Changes
=======================================================================

The ``StatsManager`` methods :meth:`~scenedetect.stats_manager.StatsManager.get_metrics`, :meth:`~scenedetect.stats_manager.StatsManager.set_metrics`, and :meth:`~scenedetect.stats_manager.StatsManager.metrics_exist` now formally accept either a ``FrameTimecode`` or a plain ``int`` frame number for the timecode argument. Passing a ``FrameTimecode`` is preferred and matches the detector interface; the ``int`` form is retained for compatibility with the deprecated ``load_from_csv()`` path, which keys metrics by integer frame number.

``StatsManager.load_from_csv()`` also accepts ``os.PathLike`` (e.g. ``pathlib.Path``) in addition to ``str`` / ``bytes`` / file handles.


=======================================================================
``SceneDetector`` Annotation Fixes
=======================================================================

:meth:`~scenedetect.detector.SceneDetector.post_process` now declares its parameter as ``timecode: FrameTimecode`` (previously typed as ``int``). The method already received a ``FrameTimecode`` at runtime and concrete detectors (e.g. ``ThresholdDetector``, ``ContentDetector``) already used the ``FrameTimecode`` type - only the abstract-base-class annotation was inconsistent. No call-site changes are needed; this just brings the signature into agreement with the documented and actual behavior.


=======================================================================
``SceneManager.detect_scenes()`` Time Arguments
=======================================================================

The ``duration`` and ``end_time`` arguments of :meth:`~scenedetect.scene_manager.SceneManager.detect_scenes` now formally accept ``int`` (frames), ``float`` (seconds), ``str`` (timecode string, e.g. ``"00:00:05.000"``), or ``FrameTimecode``. The internal code already validated these forms; the annotation was previously narrower than the documented behavior.

.. code:: python

    # All of these were always supported at runtime; now they type-check too:
    scene_manager.detect_scenes(video, end_time=15.0)         # seconds
    scene_manager.detect_scenes(video, end_time=1500)         # frames
    scene_manager.detect_scenes(video, end_time="00:01:00")   # timecode


=======================================================================
``save_images()`` Path Handling
=======================================================================

The ``output_dir`` argument of :func:`scenedetect.output.save_images` now accepts ``os.PathLike`` (e.g. ``pathlib.Path``) in addition to ``str``. No changes are required for existing string-based callers.


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
     - Use :meth:`~scenedetect.scene_manager.SceneManager.get_cut_list` or :meth:`~scenedetect.scene_manager.SceneManager.get_scene_list`
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

Removed / Renamed
-----------------------------------------------------------------------

- The ``-d``/``--min-delta-hsv`` option on ``detect-adaptive`` has been removed. Use ``-c``/``--min-content-val`` instead.
- The global ``--framerate`` flag has been renamed to ``-f``/``--frame-rate`` for consistency with the API. The legacy ``--framerate`` form is retained as a hidden alias and will be removed in v0.8; if both are supplied, ``--frame-rate`` takes precedence and a warning is logged.
- The ``export-html`` command has been renamed to :ref:`save-html <command-save-html>`. The legacy ``export-html`` command is retained as a deprecated alias and emits a deprecation warning when used.

New Commands and Options
-----------------------------------------------------------------------

- New :ref:`save-fcp <command-save-fcp>` command exports scenes in Final Cut Pro XML format (FCP7/FCPX).
- New :ref:`save-qp <command-save-qp>` command writes a QP file with scene boundary frame numbers, suitable for forcing keyframes at scene cuts in x264/x265.
- New :ref:`save-html <command-save-html>` command (replaces ``export-html``).
- New ``-s``/``--start-timecode`` option on :ref:`save-edl <command-save-edl>` provides a custom start timecode for generated EDLs (SMPTE ``HH:MM:SS:FF`` or 8-digit ``HHMMSSFF``).

Other Changes
-----------------------------------------------------------------------

- VFR videos now work correctly with both the OpenCV and PyAV backends.
- All CLI options that previously accepted only frame numbers now also accept seconds (e.g. ``0.6s``) and timecodes (e.g. ``00:00:00.600``).
