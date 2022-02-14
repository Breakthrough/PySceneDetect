
***********************************************************************
``scenedetect`` 🎬 Module
***********************************************************************

=======================================================================
Overview
=======================================================================

The ``scenedetect`` module is organized into several sub-modules, each
containing the implementation of a particular class.  The most commonly
used classes are available for import directly from the `scenedetect`
module (see the `Example`_ below).  The following is an overview of the
main classes/modules provided in the `scenedetect` package:

    * :ref:`scenedetect.frame_timecode ⏱️ <scenedetect-frame_timecode>`: Contains
      :py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>`
      class for storing, converting, and performing arithmetic on timecodes
      with frame-accurate precision.

    * :ref:`scenedetect.video_stream 🎥 <scenedetect-video_stream>`: Contains
      :py:class:`VideoStream <scenedetect.video_stream.VideoStream>`
      interface for video decoding using different backends (:py:mod:`scenedetect.backends`).
      Current supported backends:

        * OpenCV: :py:class:`VideoStreamCv2 <scenedetect.backends.opencv.VideoStreamCv2>`
        * PyAV: TODO(v0.6)

    * :ref:`scenedetect.scene_manager 🎞️ <scenedetect-scene_manager>`: Contains
      :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>`
      class for applying `SceneDetector` objects on a `VideoStream`,
      and optionally using a `StatsManager` as a cache.

    * :ref:`scenedetect.stats_manager 🧮 <scenedetect-stats_manager>`: Contains
      :py:class:`StatsManager <scenedetect.stats_manager.StatsManager>`
      class for caching frame metrics and loading/saving them to disk in
      CSV format for analysis. Also be used as a persistent cache
      to make several scene detection runs on the same video source
      `significantly` faster.

    * :ref:`scenedetect.scene_detector 🌐 <scenedetect-scene_detector>`: Contains
      :py:class:`SceneDetector <scenedetect.scene_detector.SceneDetector>`
      base class for implementing scene detection algorithms.

    * :ref:`scenedetect.detectors 🕵️ <scenedetect-detectors>`: Contains all detection algorithm
      implementations, which are classes that inherit from
      :py:class:`SceneDetectors <scenedetect.scene_detector.SceneDetector>`.

        * :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`
          detects fast changes/cuts in video content.

        * :py:class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>`
          detects changes in video brightness/intensity.

    * :ref:`scenedetect.video_splitter ✂️ <scenedetect-video_splitter>`: Contains
      helper functions to use external tools after processing
      to split the video into individual scenes.


Note that every module has the same name of the implemented
class in `lowercase_underscore` format, whereas the class name itself
is in `PascalCase` format.  There are also some constants, functions,
and exceptions defined in various modules that are documented in the
section describing the associated class.


=======================================================================
Example
=======================================================================

In the code example below, we create a function ``find_scenes()`` which will
load a video, detect the scenes, and return a list of tuples containing the
(start, end) timecodes of each detected scene.  Note that you can modify
the `threshold` argument to modify the sensitivity of the
:py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`.

.. code:: python

    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector

    def find_scenes(video_path, threshold=27.0):
        # Create our video & scene managers, then add the detector.
        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(
            ContentDetector(threshold=threshold))
        # Improve processing speed by downscaling before processing.
        scene_manager.auto_downscale = True
        # Detect all scenes in video from current position to end.
        scene_manager.detect_scenes(video)
        # `get_scene_list` returns a list of start/end timecode pairs
        # for each scene that was found.
        return scene_manager.get_scene_list()

    # Detect scenes and print them to the terminal.
    scenes = find_scenes('video.mp4')
    for i, scene in enumerate(scenes):
      print('Scene %d: Start = %s, End = %s' % (i, scene[0], scene[1]))

For a more advanced example of using the PySceneDetect API to with a stats file
(to speed up processing of the same file multiple times), take a look at the
:ref:`example in the SceneManager reference<scenemanager-example>`.


=======================================================================
Migrating From v0.5
=======================================================================

PySceneDetect v0.6 introduces several breaking changes which are incompatible with v0.5. See :ref:`Migration Guide <scenedetect-migration_guide>` for details on how to update your application.
