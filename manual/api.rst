
***********************************************************************
``scenedetect`` 🎬 Module
***********************************************************************

=======================================================================
Overview
=======================================================================

The ``scenedetect`` module is organized into several sub-modules, each containing the implementation of a particular class. The most commonly used classes are available for import directly from the `scenedetect` module (see the `Detailed Example`_ below).  The following is an overview of the main classes/modules provided in the `scenedetect` package:

    * :ref:`scenedetect.scene_manager 🎞️ <scenedetect-scene_manager>`: Contains :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` class which applies `SceneDetector` objects on a `VideoStream`. Also contains the :py:func:`save_images <scenedetect.scene_manager.save_images>` and :py:func:`write_scene_list <scenedetect.scene_manager.write_scene_list>` / :py:func:`write_scene_list_html <scenedetect.scene_manager.write_scene_list_html>` functions to export information about the detected scenes in various formats.

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


Note that every module has the same name of the implemented
class in `lowercase_underscore` format, whereas the class name itself
is in `PascalCase` format.  However, most types/functions are also available directly from the `scenedetect` package to make imports simpler.


=======================================================================
Quickstart
=======================================================================

To get started, the :py:func:`scenedetect.detect_scenes` function will perform scene detection using :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`, and return the resulting scene list:

.. code:: python

    from scenedetect import detect, ContentDetector
    scene_list = detect('my_video.mp4', ContentDetector())
    for i, scene in enumerate(scene_list):
        print('    Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
            i+1,
            scene[0].get_timecode(), scene[0].get_frames(),
            scene[1].get_timecode(), scene[1].get_frames(),))

You can also set ``show_progress=True`` when calling :py:func:`detect <scenedetect.detect>` to display a progress bar and estimated time remaining.

Now that we have a list of the timecodes where each scene is, let's :ref:`split the video <scenedetect-video_splitter>` into each scene if `ffmpeg` is installed (`mkvmerge` is also supported):

.. code:: python

    from scenedetect import detect, ContentDetector, split_video_ffmpeg
    scene_list = detect('my_video.mp4', ContentDetector())
    split_video_ffmpeg('my_video.mp4', scene_list)

The next example shows how we can write our own function to do the same thing using the various library components.


.. _scenedetect-detailed_example:
=======================================================================
Detailed Example
=======================================================================

In the code example below, we create a function ``find_scenes()`` which will load a video, detect the scenes, and return a list of tuples containing the (start, end) timecodes of each detected scene.  Note that you can modify the `threshold` argument to modify the sensitivity of the :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`, or use other detection algorithms (e.g. :py:class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>`, :py:class:`AdaptiveDetector <scenedetect.detectors.adaptive_detector.AdaptiveDetector>`).

.. code:: python

    from scenedetect import SceneManager, open_video, ContentDetector

    def find_scenes(video_path, threshold=27.0):
        # Create our video & scene managers, then add the detector.
        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(
            ContentDetector(threshold=threshold))
        # Detect all scenes in video from current position to end.
        scene_manager.detect_scenes(video)
        # `get_scene_list` returns a list of start/end timecode pairs
        # for each scene that was found.
        return scene_manager.get_scene_list()

For a more advanced example of using the PySceneDetect API to with a stats file (to speed up processing of the same file multiple times), take a look at the :ref:`example in the SceneManager reference<scenemanager-example>`.


=======================================================================
Migrating From v0.5
=======================================================================

PySceneDetect v0.6 introduces several breaking changes which are incompatible with v0.5. See :ref:`Migration Guide <scenedetect-migration_guide>` for details on how to update your application.


=======================================================================
Module-Level Functions
=======================================================================

.. autofunction:: scenedetect.detect
