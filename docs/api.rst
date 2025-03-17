
***********************************************************************
``scenedetect`` 🎬 Package
***********************************************************************

The `scenedetect` API is easy to integrate with most application workflows, while also being highly extensible. See the `Getting Started`_ section below for some common use cases and integrations. The `scenedetect` package contains several modules:

    * :ref:`scenedetect 🎬 <scenedetect-functions>`: Includes the :func:`scenedetect.detect <scenedetect.detect>` function which takes a path and a  :ref:`detector <scenedetect-detectors>` to find scene transitions (:ref:`example <scenedetect-quickstart>`), and :func:`scenedetect.open_video <scenedetect.open_video>` for video input

    * :ref:`scenedetect.scene_manager 🎞️ <scenedetect-scene_manager>`: The :class:`SceneManager <scenedetect.scene_manager.SceneManager>` acts as a way to coordinate detecting scenes (via `SceneDetector` instances) on video frames (via :ref:`VideoStream <scenedetect-video_stream>` instances). This module also contains functionality to export information about scenes in various formats: :func:`save_images <scenedetect.scene_manager.save_images>` to save images for each scene, :func:`write_scene_list <scenedetect.scene_manager.write_scene_list>` to save scene/cut info as CSV, and :func:`write_scene_list_html <scenedetect.scene_manager.write_scene_list_html>` to export scenes in viewable HTML format.

    * :ref:`scenedetect.detectors 🕵️ <scenedetect-detectors>`: Detection algorithms:

        * :mod:`ContentDetector <scenedetect.detectors.content_detector>`: detects fast cuts using weighted average of HSV changes

        * :mod:`ThresholdDetector <scenedetect.detectors.threshold_detector>`: finds fades in/out using average pixel intensity changes in RGB

        * :mod:`AdaptiveDetector <scenedetect.detectors.adaptive_detector>` finds fast cuts using rolling average of HSL changes

        * :mod:`HistogramDetector <scenedetect.detectors.histogram_detector>` finds fast cuts using HSV histogram changes

        * :mod:`HashDetector <scenedetect.detectors.hash_detector>`: finds fast cuts using perceptual image hashing

    * :ref:`scenedetect.video_stream 🎥 <scenedetect-video_stream>`: Video input is handled through the :class:`VideoStream <scenedetect.video_stream.VideoStream>` interface. Implementations for common video libraries are provided in :mod:`scenedetect.backends`:

        * OpenCV: :class:`VideoStreamCv2 <scenedetect.backends.opencv.ideoStreamCv2>`
        * PyAV: :class:`VideoStreamAv <scenedetect.backends.pyav.VideoStreamAv>`
        * MoviePy: :class:`VideoStreamMoviePy <scenedetect.backends.moviepy.VideoStreamMoviePy>`

    * :ref:`scenedetect.video_splitter ✂️ <scenedetect-video_splitter>`: Contains :func:`split_video_ffmpeg <scenedetect.video_splitter.split_video_ffmpeg>` and :func:`split_video_mkvmerge <scenedetect.video_splitter.split_video_mkvmerge>` to split a video based on the detected scenes.

    * :ref:`scenedetect.common ⏱️ <scenedetect-common>`: Contains common types such as :class:`FrameTimecode <scenedetect.common.FrameTimecode>` used for timecode handing.

    * :ref:`scenedetect.scene_detector 🌐 <scenedetect-scene_detector>`: Contains :class:`SceneDetector <scenedetect.scene_detector.SceneDetector>` interface which detection algorithms must implement.

    * :ref:`scenedetect.stats_manager 🧮 <scenedetect-stats_manager>`: Contains :class:`StatsManager <scenedetect.stats_manager.StatsManager>` class for caching frame metrics and loading/saving them to disk in CSV format for analysis.

    * :ref:`scenedetect.platform 🐱‍💻 <scenedetect-platform>`: Logging and utility functions.


Most types/functions are also available directly from the `scenedetect` package to make imports simpler.

.. warning::

    The PySceneDetect API is still under development. It is recommended that you pin the `scenedetect` version in your requirements to below the next major release:

    .. code:: python

        scenedetect<0.8


.. _scenedetect-quickstart:

=======================================================================
Getting Started
=======================================================================

PySceneDetect makes it very easy to find scene transitions in a video with the :func:`scenedetect.detect` function:

.. code:: python

    from scenedetect import detect, ContentDetector
    path = "video.mp4"
    scenes = detect(path, ContentDetector())
    for (scene_start, scene_end) in scenes:
        print(f'{scene_start}-{scene_end}')

``scenes`` now contains a list of :class:`FrameTimecode <scenedetect.common.FrameTimecode>` pairs representing the start/end of each scene. Note that you can set ``show_progress=True`` when calling :func:`detect <scenedetect.detect>` to display a progress bar with estimated time remaining.

Here, we use :mod:`ContentDetector <scenedetect.detectors.content_detector>` to detect fast cuts. There are :ref:`many detector types <scenedetect-detectors>` which can be used to find fast cuts and fades in/out.  PySceneDetect can also export scene data in various formats, and can  :ref:`split the input video <scenedetect-video_splitter>` automatically if `ffmpeg` is available:

.. code:: python

    from scenedetect import detect, ContentDetector, split_video_ffmpeg
    scene_list = detect("my_video.mp4", ContentDetector())
    split_video_ffmpeg("my_video.mp4", scenes)

Recipes for common use cases can be `found on Github <https://github.com/Breakthrough/PySceneDetect/blob/v0.6.4-release/tests/test_api.py>`_ including limiting detection time and storing per-frame metrics. For advanced workflows, start with the :ref:`SceneManager usage examples <scenedetect-scene_manager>`.

.. _scenedetect-functions:

=======================================================================
Functions
=======================================================================

.. automodule:: scenedetect
    :members:

=======================================================================
Module Reference
=======================================================================

.. toctree::
    :maxdepth: 3
    :caption: PySceneDetect Module Documentation
    :name: fullapitoc

    api/detectors
    api/backends
    api/scene_manager
    api/video_splitter
    api/stats_manager
    api/common
    api/scene_detector
    api/video_stream
    api/platform


=======================================================================
Logging
=======================================================================

PySceneDetect outputs messages to a logger named ``pyscenedetect`` which does not have any default handlers. You can use :func:`scenedetect.init_logger <scenedetect.platform.init_logger>` with ``show_stdout=True`` or specify a log file (verbosity can also be specified) to attach some common handlers, or use ``logging.getLogger("pyscenedetect")`` and attach log handlers manually.
