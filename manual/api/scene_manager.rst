
.. _scenedetect-scene_manager:

-----------------------------------------------------------------------
SceneManager
-----------------------------------------------------------------------

.. automodule:: scenedetect.scene_manager


.. _scenemanager-example:

=======================================================================
Usage Example
=======================================================================

In the code example below, we create a function ``find_scenes()`` which performs the following actions:

 * loads a video file by path (`str`) using :py:func:`scenedetect.backends.open_video`
 * loads/saves a stats file for the video to ``{video_path}.stats.csv`` using a :py:class:`StatsManager <scenedetect.stats_manager.StatsManager>`
 * performs content-aware scene detection on the video using a :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>` bound to a :py:class:`SceneManager`
 * ``print()`` out a table of detected scenes to the terminal/console
 * returns a list of tuples of :py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>` objects of the start and end times for each detected scene

This example is a modified version of `the api_test.py file <https://github.com/Breakthrough/PySceneDetect/blob/master/tests/test_api.py>`_, and shows complete usage of a :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` object to perform content-aware scene detection using the :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`, printing a list of scenes, then saving the calculated per-frame metrics to disk:

.. code:: python

    import os

    from scenedetect import open_video, ContentDetector, SceneManager, StatsManager

    def find_scenes(video_path):
        # type: (str) -> List[Tuple[FrameTimecode, FrameTimecode]]

        video_stream = open_video(path=video_path)
        stats_manager = StatsManager()
        # Construct our SceneManager and pass it our StatsManager.
        scene_manager = SceneManager(stats_manager)

        # Add ContentDetector algorithm (each detector's constructor
        # takes various options, e.g. threshold).
        scene_manager.add_detector(ContentDetector())

        # Save calculated metrics for each frame to {VIDEO_PATH}.stats.csv.
        stats_file_path = '%s.stats.csv' % video_path

        # Perform scene detection.
        scene_manager.detect_scenes(video=video_stream)
        scene_list = scene_manager.get_scene_list()
        for i, scene in enumerate(scene_list):
            print(
                'Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
                i+1,
                scene[0].get_timecode(), scene[0].get_frames(),
                scene[1].get_timecode(), scene[1].get_frames(),))

        # Store the frame metrics we calculated for the next time the program runs.
        stats_manager.save_to_csv(path=stats_file_path, base_timecode=base_timecode)

        return scene_list

The statsfile can be used to find a better threshold for certain inputs, or perform further statistical analysis.  The use of a :py:class:`StatsManager <scenedetect.stats_manager.StatsManager>` also allows certain detectors to operate faster on subsequent passes by caching calculations.  Statsfiles can be persisted on disk and loaded again, which helps avoid unnecessary calculations in applications where multiple passes are expected (e.g. interactively selecting a threshold).


=======================================================================
``SceneManager`` Class
=======================================================================

.. autoclass:: scenedetect.scene_manager.SceneManager
   :members:
   :undoc-members:


.. _scenedetect-scene_manager-functions:

=======================================================================
``scene_manager`` Functions
=======================================================================

.. autofunction:: scenedetect.scene_manager.save_images

.. autofunction:: scenedetect.scene_manager.write_scene_list

.. autofunction:: scenedetect.scene_manager.write_scene_list_html

.. autofunction:: scenedetect.scene_manager.get_scenes_from_cuts
