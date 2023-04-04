
***********************************************************************
``scenedetect`` 🎬 Package
***********************************************************************

=======================================================================
Overview
=======================================================================

The `scenedetect` API is designed to be extensible and easy to integrate with most application workflows.  Many use cases are covered by the `Quickstart`_ and `Example`_ sections below.  The `scenedetect` package provides:

    * :ref:`scenedetect.scene_manager 🎞️ <scenedetect-scene_manager>`: The :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` class applies `SceneDetector` objects on video frames from a :ref:`VideoStream <scenedetect-video_stream>`. Also contains the :py:func:`save_images <scenedetect.scene_manager.save_images>` and :py:func:`write_scene_list <scenedetect.scene_manager.write_scene_list>` / :py:func:`write_scene_list_html <scenedetect.scene_manager.write_scene_list_html>` functions to export information about the detected scenes in various formats.

    * :ref:`scenedetect.detectors 🕵️ <scenedetect-detectors>`: Scene/shot detection algorithms:

        * :py:mod:`ContentDetector <scenedetect.detectors.content_detector>`: detects fast changes/cuts in video content.

        * :py:mod:`ThresholdDetector <scenedetect.detectors.threshold_detector>`: detects changes in video brightness/intensity.

        * :py:mod:`AdaptiveDetector <scenedetect.detectors.adaptive_detector>`: similar to `ContentDetector` but may result in less false negatives during rapid camera movement.

    * :ref:`scenedetect.video_stream 🎥 <scenedetect-video_stream>`: Contains :py:class:`VideoStream <scenedetect.video_stream.VideoStream>` interface for video decoding using different backends (:py:mod:`scenedetect.backends`). Current supported backends:

        * OpenCV: :py:class:`VideoStreamCv2 <scenedetect.backends.opencv.ideoStreamCv2>`
        * PyAV: In Development

    * :ref:`scenedetect.video_splitter ✂️ <scenedetect-video_splitter>`: Contains :py:func:`split_video_ffmpeg <scenedetect.video_splitter.split_video_ffmpeg>` and :py:func:`split_video_mkvmerge <scenedetect.video_splitter.split_video_mkvmerge>` to split a video based on the detected scenes.

    * :ref:`scenedetect.frame_timecode ⏱️ <scenedetect-frame_timecode>`: Contains
      :py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>`
      class for storing, converting, and performing arithmetic on timecodes
      with frame-accurate precision.

    * :ref:`scenedetect.scene_detector 🌐 <scenedetect-scene_detector>`: Contains :py:class:`SceneDetector <scenedetect.scene_detector.SceneDetector>` base class for implementing scene detection algorithms.

    * :ref:`scenedetect.stats_manager 🧮 <scenedetect-stats_manager>`: Contains :py:class:`StatsManager <scenedetect.stats_manager.StatsManager>` class for caching frame metrics and loading/saving them to disk in CSV format for analysis. Also used as a persistent cache to make multiple passes on the same video significantly faster.

    * :ref:`scenedetect.platform 🐱‍💻 <scenedetect-platform>`: Logging and utility functions.


Most types/functions are also available directly from the `scenedetect` package to make imports simpler.

.. note::

    The PySceneDetect API is still under development. It is recommended that you pin the `scenedetect` version in your requirements to below the next major release:

    .. code:: python

        scenedetect<0.7


.. _scenedetect-quickstart:

=======================================================================
Quickstart
=======================================================================

To get started, the :py:func:`scenedetect.detect` function takes a path to a video and a :ref:`scene detector object<scenedetect-detectors>`, and returns a list of start/end timecodes.  For detecting fast cuts (shot changes), we use the :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`:

.. code:: python

    from scenedetect import detect, ContentDetector
    scene_list = detect('my_video.mp4', ContentDetector())

``scene_list`` is now a list of :py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>` pairs representing the start/end of each scene (try calling ``print(scene_list)``). Note that you can set ``show_progress=True`` when calling :py:func:`detect <scenedetect.detect>` to display a progress bar with estimated time remaining.

Next, let's print the scene list in a more readable format by iterating over it:

.. code:: python

    for i, scene in enumerate(scene_list):
        print('Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
            i+1,
            scene[0].get_timecode(), scene[0].get_frames(),
            scene[1].get_timecode(), scene[1].get_frames(),))

Now that we know where each scene is, we can also :ref:`split the input video <scenedetect-video_splitter>` automatically using `ffmpeg` (`mkvmerge` is also supported):

.. code:: python

    from scenedetect import detect, ContentDetector, split_video_ffmpeg
    scene_list = detect('my_video.mp4', ContentDetector())
    split_video_ffmpeg('my_video.mp4', scene_list)

This is just a small snippet of what PySceneDetect offers. The library is very modular, and can integrate with most application workflows easily.

In the next example, we show how the library components can be used to create a more customizable scene cut/shot detection pipeline.  Additional demonstrations/recipes can be found in the `tests/test_api.py <https://github.com/Breakthrough/PySceneDetect/blob/v0.6.1-release/tests/test_api.py>`_ file.


.. _scenedetect-detailed_example:

=======================================================================
Example
=======================================================================

In this example, we create a function ``find_scenes()`` which will load a video, detect the scenes, and return a list of tuples containing the (start, end) timecodes of each detected scene.  Note that you can modify the `threshold` argument to modify the sensitivity of the :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`, or use other detection algorithms (e.g. :py:class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>`, :py:class:`AdaptiveDetector <scenedetect.detectors.adaptive_detector.AdaptiveDetector>`).

.. code:: python

    from scenedetect import SceneManager, open_video, ContentDetector

    def find_scenes(video_path, threshold=27.0):
        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(
            ContentDetector(threshold=threshold))
        # Detect all scenes in video from current position to end.
        scene_manager.detect_scenes(video)
        # `get_scene_list` returns a list of start/end timecode pairs
        # for each scene that was found.
        return scene_manager.get_scene_list()

Using a :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` directly allows tweaking the Parameters passed to :py:meth:`detect_scenes <scenedetect.scene_manager.SceneManager.detect_scenes>` including setting a limit to the number of frames to process, which is useful for live streams/camera devices.  You can also combine detection algorithms or create new ones from scratch.

For a more advanced example of using the PySceneDetect API to with a stats file (to save per-frame metrics to disk and/or speed up multiple passes of the same video), take a look at the :ref:`example in the SceneManager reference<scenemanager-example>`.

In addition to module-level examples, demonstrations of some common use cases can be found in the `tests/test_api.py <https://github.com/Breakthrough/PySceneDetect/blob/v0.6.1-release/tests/test_api.py>`_ file.


=======================================================================
Migrating From 0.5
=======================================================================

PySceneDetect 0.6 introduces several breaking changes which are incompatible with 0.5. See :ref:`Migration Guide <scenedetect-migration_guide>` for details on how to update your application. In addition, demonstrations of common use cases can be found in the `tests/test_api.py <https://github.com/Breakthrough/PySceneDetect/blob/v0.6.1-release/tests/test_api.py>`_ file.


=======================================================================
Module-Level Functions
=======================================================================


`detect`
===============================================================

.. autofunction:: scenedetect.detect

`open_video`
===============================================================
.. autofunction:: scenedetect.open_video


=======================================================================
Logging
=======================================================================

PySceneDetect outputs messages to a logger named ``pyscenedetect`` which does not have any default handlers. You can use :py:func:`scenedetect.init_logger <scenedetect.platform.init_logger>` with ``show_stdout=True`` or specify a log file (verbosity can also be specified) to attach some common handlers, or use ``logging.getLogger('pyscenedetect')`` and attach log handlers manually.
