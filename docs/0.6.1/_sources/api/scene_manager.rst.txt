
.. _scenedetect-scene_manager:

-----------------------------------------------------------------------
SceneManager
-----------------------------------------------------------------------

.. automodule:: scenedetect.scene_manager


.. _scenemanager-example:

=======================================================================
Storing Per-Frame Statistics
=======================================================================

A `SceneManager` can use an optional :py:class:`StatsManager <scenedetect.stats_manager.StatsManager>` to save per-frame statistics to disk:

.. code:: python

    from scenedetect import open_video, ContentDetector, SceneManager, StatsManager
    video = open_video(test_video_file)
    scene_manager = SceneManager(stats_manager=StatsManager())
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video=video)
    scene_list = scene_manager.get_scene_list()
    print_scenes(scene_list=scene_list)
    # Save per-frame statistics to disk.
    scene_manager.stats_manager.save_to_csv(csv_file=STATS_FILE_PATH)


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
