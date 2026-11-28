
.. _scenedetect-scene_manager:

-------------
Scene Manager
-------------

.. automodule:: scenedetect.scene_manager
   :no-members:

.. seealso::

   Command line equivalents of :class:`~scenedetect.scene_manager.SceneManager` settings:

   - :option:`--crop <scenedetect --crop>`: :attr:`~scenedetect.scene_manager.SceneManager.crop`
   - :option:`-d/--downscale <scenedetect -d>`: :attr:`~scenedetect.scene_manager.SceneManager.downscale`, :attr:`~scenedetect.scene_manager.SceneManager.auto_downscale`
   - :option:`-fs/--frame-skip <scenedetect -fs>`: :meth:`~scenedetect.scene_manager.SceneManager.detect_scenes` ``frame_skip``
   - :ref:`time <command-time>`: :meth:`~scenedetect.scene_manager.SceneManager.detect_scenes` ``duration``, ``end_time``
   - :option:`-s/--stats <scenedetect -s>`: :class:`~scenedetect.stats_manager.StatsManager`

.. autoclass:: scenedetect.scene_manager.SceneManager
   :members:


Functions
---------

.. autofunction:: scenedetect.scene_manager.get_scenes_from_cuts

.. autofunction:: scenedetect.scene_manager.expand_scenes_to_bounds

.. autofunction:: scenedetect.scene_manager.compute_downscale_factor


Constants
---------

.. autodata:: scenedetect.scene_manager.DEFAULT_MIN_WIDTH

.. autodata:: scenedetect.scene_manager.MAX_FRAME_QUEUE_LENGTH

.. autodata:: scenedetect.scene_manager.MAX_FRAME_SIZE_ERRORS

.. autodata:: scenedetect.scene_manager.PROGRESS_BAR_DESCRIPTION
