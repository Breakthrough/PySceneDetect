
.. _scenedetect-migration_guide:

---------------------------------------------------------------
Migration Guide
---------------------------------------------------------------

===============================================================
VideoManager
===============================================================

TODO(v0.6)

===============================================================
StatsManager
===============================================================

TODO(v0.6)

===============================================================
scene_manager.save_images Parameters
===============================================================

The `downscale_factor` parameter has been removed from :py:func:`save_images <scenedetect.scene_manager.save_images>`. The existing `scale` parameter should be used instead. Equivalent functionality can be achieved by setting `scale` to `1.0 / downscale_factor`.

===============================================================
frame_timecode Module Constants
===============================================================

Replace uses of both `MAX_FPS_DELTA` and `MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT` from :py:mod:`scenedetect.frame_timecode` with :py:data:`MAX_FPS_DELTA <scenedetect.frame_timecode.MAX_FPS_DELTA>`.
