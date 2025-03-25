
***********************************************************************
``scenedetect`` 🎬 Package
***********************************************************************

The `scenedetect` API is easy to integrate with most application workflows, while also being highly extensible. See the `Getting Started`_ section below for some common use cases and integrations. The `scenedetect` package is organized into several sub-modules:

    * :ref:`scenedetect 🎬 <scenedetect-functions>`: high-level functions like :func:`scenedetect.detect() <scenedetect.detect>` to quickly analyze a video with any :ref:`detection algorithm <scenedetect-detectors>` (:ref:`example <scenedetect-quickstart>`) and get a list of timecode pairs as a result

    * :ref:`scenedetect.detectors 🕵️ <scenedetect-detectors>`: detection algorithms:

        * :mod:`ContentDetector <scenedetect.detectors.content_detector>`: detects fast cuts using weighted average of HSV changes

        * :mod:`ThresholdDetector <scenedetect.detectors.threshold_detector>`: finds fades in/out using average pixel intensity changes in RGB

        * :mod:`AdaptiveDetector <scenedetect.detectors.adaptive_detector>` finds fast cuts using rolling average of HSL changes

        * :mod:`HistogramDetector <scenedetect.detectors.histogram_detector>` finds fast cuts using HSV histogram changes

        * :mod:`HashDetector <scenedetect.detectors.hash_detector>`: finds fast cuts using perceptual image hashing

    * :ref:`scenedetect.output ✂️ <scenedetect-output>`: Output formats:

        * :func:`split_video_ffmpeg <scenedetect.output.split_video_ffmpeg>` and :func:`split_video_mkvmerge <scenedetect.output.split_video_mkvmerge>` split a video based on the detected scenes

        * :func:`save_images <scenedetect.scene_manager.save_images>` can save an arbitrary number of images from each scene

        * :func:`write_scene_list <scenedetect.scene_manager.write_scene_list>` can be used to save scene/cut info as CSV, :func:`write_scene_list_html <scenedetect.scene_manager.write_scene_list_html>` for HTML

    * :ref:`scenedetect.backends 🎥 <scenedetect-backends>`: PySceneDetect supports multiple libraries as an input backend:

        * OpenCV: :class:`VideoStreamCv2 <scenedetect.backends.opencv.ideoStreamCv2>`

        * PyAV: :class:`VideoStreamAv <scenedetect.backends.pyav.VideoStreamAv>`

        * MoviePy: :class:`VideoStreamMoviePy <scenedetect.backends.moviepy.VideoStreamMoviePy>`

    * :ref:`scenedetect.common ⏱️ <scenedetect-common>`: common functionality such as :class:`FrameTimecode <scenedetect.common.FrameTimecode>` for timecode handling

    * :ref:`scenedetect.scene_manager 🎞️ <scenedetect-scene_manager>`: the :class:`SceneManager <scenedetect.scene_manager.SceneManager>` coordinates performing scene detection on a video with one or more detectors

    * :ref:`scenedetect.detector 🌐 <scenedetect-detector>`: the interface (:class:`SceneDetector <scenedetect.detector.SceneDetector>`) that detectors must implement to be compatible with PySceneDetect

    * :ref:`scenedetect.video_stream  <scenedetect-video_stream>`: the interface (:class:`VideoStream <scenedetect.video_stream.VideoStream>`) that detectors must implement to be compatible with PySceneDetect

    * :ref:`scenedetect.stats_manager 🧮 <scenedetect-stats_manager>`: the :class:`StatsManager <scenedetect.stats_manager.StatsManager>` allows you to store detection metrics for each frame and save them to CSV for further analysis

    * :ref:`scenedetect.platform 🐱‍💻 <scenedetect-platform>`: logging and utility functions


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
        print(f"{scene_start}-{scene_end}")

``scenes`` now contains a list of :class:`FrameTimecode <scenedetect.common.FrameTimecode>` pairs representing the start/end of each scene. Note that you can set ``show_progress=True`` when calling :func:`detect <scenedetect.detect>` to display a progress bar with estimated time remaining.

Here, we use :mod:`ContentDetector <scenedetect.detectors.content_detector>` to detect fast cuts. There are :ref:`many detector types <scenedetect-detectors>` which can be used to find fast cuts and fades in/out.  PySceneDetect can also export scene data in various formats, and can  :ref:`split the input video <scenedetect-output>` automatically if `ffmpeg` is available:

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
    api/scene_manager
    api/common
    api/output
    api/backends
    api/stats_manager
    api/detector
    api/video_stream
    api/platform


=======================================================================
Logging
=======================================================================

PySceneDetect outputs messages to a logger named ``pyscenedetect`` which does not have any default handlers. You can use :func:`scenedetect.init_logger <scenedetect.platform.init_logger>` with ``show_stdout=True`` or specify a log file (verbosity can also be specified) to attach some common handlers, or use ``logging.getLogger("pyscenedetect")`` and attach log handlers manually.
