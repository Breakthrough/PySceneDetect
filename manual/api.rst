
***********************************************************************
The ``scenedetect`` Module
***********************************************************************


=======================================================================
Overview
=======================================================================

The ``scenedetect`` module is organized into several sub-modules, each
containing a particular class.  Every module has the same name of the
implemented class in `lowercase_underscore` format, whereas the class
name is in `PascalCase` format.  There are also some constants,
functions, and exceptions defined in various modules that are
documented in the section describing the associated class.

The following is an overview of the modules and classes
provided in the ``scenedetect`` package:

    * ``scenedetect``: Main PySceneDetect module.

        * ``scenedetect.frame_timecode``: Contains
          :py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>`
          class for storing, converting, and performing arithmetic on timecodes
          with frame-accurate precision.


        * ``scenedetect.video_manager``: Contains
          :py:class:`VideoManager <scenedetect.video_manager.VideoManager>`
          class for loading one or more videos, providing seeking, and downscaling.

        * ``scenedetect.scene_manager``: Contains
          :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>`
          class for applying `SceneDetector` objects on a `VideoManager`,
          and optionally using a `StatsManager` as a cache.

        * ``scenedetect.stats_manager``: Contains
          :py:class:`StatsManager <scenedetect.stats_manager.StatsManager>`
          class for caching frame metrics and loading/saving them to disk in
          CSV format for analysis. Also be used as a persistent cache
          to make several scene detection runs on the same video source
          `significantly` faster.
    
        * ``scenedetect.scene_detector``: Contains
          :py:class:`SceneDetector <scenedetect.scene_detector.SceneDetector>`
          base class for implementing scene detection algorithms.

        * ``scenedetect.detectors``: Contains all detection algorithm
          implementations, which are classes that inherit from
          :py:class:`SceneDetectors <scenedetect.scene_detector.SceneDetector>`.

            * ``scenedetect.detectors.content_detector``: The
              :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`
              algorithm, which detects fast changes/cuts in video content.
            * ``scenedetect.detectors.threshold_detector``: The
              :py:class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>`
              algorithm, which detects changes in video brightness/intensity.

        * ``scenedetect.video_splitter``: Contains
          helper functions to use external tools after processing
          to split the video into individual scenes.
          

=======================================================================
Example
=======================================================================

For an example of using the PySceneDetect API to perform scene detection,
take a look at the :ref:`example in the SceneManager reference<scenemanager-example>`.

