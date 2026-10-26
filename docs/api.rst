
-----------------------
``scenedetect`` Package
-----------------------

.. seealso:: For the ``scenedetect`` command, see the :doc:`CLI reference <cli>`.

The `scenedetect` API is easy to integrate with most application workflows, while also being highly extensible. See the `Usage`_ section below for some common use cases and integrations. The `scenedetect` package is organized into several sub-modules:

    * :ref:`Functions <scenedetect-functions>`: high-level functions like :func:`scenedetect.detect() <scenedetect.detect>` to quickly analyze a video with any :ref:`detection algorithm <scenedetect-detectors>` (:ref:`example <scenedetect-usage>`) and get a list of timecode pairs as a result

    * :doc:`api/detectors`: detection algorithms:

        * :class:`AdaptiveDetector <scenedetect.detectors.adaptive_detector.AdaptiveDetector>`: finds fast cuts using rolling average of HSL changes

        * :class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`: detects fast cuts using weighted average of HSV changes

        * :class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>`: finds fades in/out using average pixel intensity changes in RGB

        * :class:`HistogramDetector <scenedetect.detectors.histogram_detector.HistogramDetector>`: finds fast cuts using HSV histogram changes

        * :class:`HashDetector <scenedetect.detectors.hash_detector.HashDetector>`: finds fast cuts using perceptual image hashing

    * :doc:`api/output`: Output formats:

        * :func:`split_video_ffmpeg <scenedetect.output.split_video_ffmpeg>` and :func:`split_video_mkvmerge <scenedetect.output.split_video_mkvmerge>` split a video based on the detected scenes

        * :func:`save_images <scenedetect.output.save_images>` can save an arbitrary number of images from each scene

        * :func:`write_scene_list <scenedetect.output.write_scene_list>` can be used to save scene/cut info as CSV, :func:`write_scene_list_html <scenedetect.output.write_scene_list_html>` for HTML

    * :doc:`api/backends`: PySceneDetect supports multiple libraries as an input backend:

        * OpenCV: :class:`VideoStreamCv2 <scenedetect.backends.opencv.VideoStreamCv2>`

        * PyAV: :class:`VideoStreamAv <scenedetect.backends.pyav.VideoStreamAv>`

        * MoviePy: :class:`VideoStreamMoviePy <scenedetect.backends.moviepy.VideoStreamMoviePy>`

        * Multiple videos can be treated as a single continuous stream using :class:`VideoStreamConcat <scenedetect.backends.concat.VideoStreamConcat>` (e.g. ``open_video(["part1.mp4", "part2.mp4"])``)

    * :doc:`api/common`: common functionality such as :class:`FrameTimecode <scenedetect.common.FrameTimecode>` for timecode handling

    * :doc:`api/scene_manager`: the :class:`SceneManager <scenedetect.scene_manager.SceneManager>` coordinates performing scene detection on a video with one or more detectors

    * :doc:`api/detector`: the interface (:class:`SceneDetector <scenedetect.detector.SceneDetector>`) that detectors must implement to be compatible with PySceneDetect

    * :doc:`api/video_stream`: the interface (:class:`VideoStream <scenedetect.video_stream.VideoStream>`) that video backends must implement to be compatible with PySceneDetect

    * :doc:`api/stats_manager`: the :class:`StatsManager <scenedetect.stats_manager.StatsManager>` allows you to store detection metrics for each frame and save them to CSV for further analysis

    * :doc:`api/platform`: logging and utility functions


Most types/functions are also available directly from the `scenedetect` package to make imports simpler.

.. warning::

    The PySceneDetect API is still under development. It is recommended that you pin the `scenedetect` version in your requirements to below the next major release:

    .. code:: python

        scenedetect~=0.7


.. _scenedetect-usage:

Usage
-----

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
    split_video_ffmpeg("my_video.mp4", scene_list)

More tasks, each shown as a command and as Python, are on the :doc:`examples` page. For advanced workflows, start with the :ref:`SceneManager <scenedetect-scene_manager>`. Logging is covered under :ref:`Platform & Logging <scenedetect-platform>`.

.. _scenedetect-functions:

Functions
---------

.. automodule:: scenedetect
    :members:
