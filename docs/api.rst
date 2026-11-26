
-----------------------
``scenedetect`` Package
-----------------------

.. seealso:: For the ``scenedetect`` command, see the :doc:`CLI reference <cli>`.

The ``scenedetect`` API integrates into Python applications and supports custom detectors and video backends. See `Usage`_ below for common examples. The ``scenedetect`` package is organized into these submodules:

    * :ref:`Functions <scenedetect-functions>`: high-level functions such as :func:`scenedetect.detect() <scenedetect.detect>` to analyze a video with any :ref:`detector <scenedetect-detectors>` (:ref:`example <scenedetect-usage>`) and return a list of frame position pairs

    * :doc:`api/detectors`: built-in detectors:

        * :class:`AdaptiveDetector <scenedetect.detectors.adaptive_detector.AdaptiveDetector>`: finds fast cuts using a rolling average of HSV content changes

        * :class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`: finds fast cuts using a weighted average of HSV color and optional edge changes

        * :class:`HashDetector <scenedetect.detectors.hash_detector.HashDetector>`: finds fast cuts using perceptual image hashing

        * :class:`HistogramDetector <scenedetect.detectors.histogram_detector.HistogramDetector>`: finds fast cuts using Y-channel (brightness) histogram changes in YUV

        * :class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>`: finds fades in and out using average RGB pixel brightness

    * :doc:`api/output`: output helpers:

        * :func:`split_video_ffmpeg <scenedetect.output.split_video_ffmpeg>` and :func:`split_video_mkvmerge <scenedetect.output.split_video_mkvmerge>` split a video into clips for each detected scene

        * :func:`save_images <scenedetect.output.save_images>` saves still frames from each scene

        * :func:`write_scene_list <scenedetect.output.write_scene_list>` writes scene lists as CSV, :func:`write_scene_list_html <scenedetect.output.write_scene_list_html>` writes HTML reports, and additional helpers export EDL, Final Cut Pro XML, OpenTimelineIO, and FFmetadata chapters

    * :doc:`api/backends`: modular video input backends:

        * OpenCV: :class:`VideoStreamCv2 <scenedetect.backends.opencv.VideoStreamCv2>`

        * PyAV: :class:`VideoStreamAv <scenedetect.backends.pyav.VideoStreamAv>`

        * MoviePy: :class:`VideoStreamMoviePy <scenedetect.backends.moviepy.VideoStreamMoviePy>`

        * Multiple videos can be read as one continuous stream with :class:`VideoStreamConcat <scenedetect.backends.concat.VideoStreamConcat>` (for example, ``open_video(["part1.mp4", "part2.mp4"])``)

    * :doc:`api/common`: common types such as :class:`FramePosition <scenedetect.common.FramePosition>`, :class:`FrameDuration <scenedetect.common.FrameDuration>`, and :class:`Timecode <scenedetect.common.Timecode>` for frame positions and timing

    * :doc:`api/scene_manager`: :class:`SceneManager <scenedetect.scene_manager.SceneManager>` runs scene detection on a video with one or more detectors

    * :doc:`api/detector`: the :class:`SceneDetector <scenedetect.detector.SceneDetector>` base class for custom detectors

    * :doc:`api/video_stream`: the :class:`VideoStream <scenedetect.video_stream.VideoStream>` base class for custom video backends

    * :doc:`api/stats_manager`: :class:`StatsManager <scenedetect.stats_manager.StatsManager>` stores per-frame detection metrics and writes them to a CSV stats file

    * :doc:`api/platform`: logging and utility functions


Most common types and functions can be imported directly from the top-level ``scenedetect`` package.

.. warning::

    The PySceneDetect API may change before v1.0. Pin ``scenedetect`` to a minor release in your dependencies:

    .. code:: text

        scenedetect~=0.8.0


.. _scenedetect-usage:

Usage
-----

Find scene cuts in a video with :func:`scenedetect.detect`:

.. code:: python

    from scenedetect import detect, ContentDetector
    path = "video.mp4"
    scenes = detect(path, ContentDetector())
    for (scene_start, scene_end) in scenes:
        print(f"{scene_start}-{scene_end}")

``scenes`` is a list of :class:`FramePosition <scenedetect.common.FramePosition>` pairs giving the start and exclusive end of each scene. Pass ``show_progress=True`` to :func:`detect <scenedetect.detect>` to show a progress bar with estimated time remaining.

This example uses :class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>` to find fast cuts. You can choose from several :ref:`detectors <scenedetect-detectors>` for fast cuts and fades. PySceneDetect can also export scene lists in several formats and :ref:`split the input video <scenedetect-output>` when ``ffmpeg`` is installed:

.. code:: python

    from scenedetect import detect, ContentDetector, split_video_ffmpeg
    scene_list = detect("my_video.mp4", ContentDetector())
    split_video_ffmpeg("my_video.mp4", scene_list)

See :doc:`examples` for more tasks shown as both CLI commands and Python code. For advanced workflows, start with :ref:`SceneManager <scenedetect-scene_manager>`. Logging is covered under :ref:`Platform & Logging <scenedetect-platform>`.

.. _scenedetect-functions:

Functions
---------

.. automodule:: scenedetect
    :members:
