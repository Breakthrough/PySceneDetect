
.. _scenedetect-migration_guide:

---------------------------------------------------------------
Migration Guide
---------------------------------------------------------------

===============================================================
`VideoManager`
===============================================================

TODO(v0.6)


===============================================================
`StatsManager`
===============================================================

TODO(v0.6)


===============================================================
`AdaptiveDetector`
===============================================================

The `video_manager` parameter is no longer required when constructing an :py:class:`AdaptiveDetector <scenedetect.detectors.adaptive_detector.AdaptiveDetector>` object.


===============================================================
`scene_manager.save_images` Parameters
===============================================================

The `downscale_factor` parameter has been removed from :py:func:`save_images <scenedetect.scene_manager.save_images>`. The `scale` parameter should be used instead. To achieve the same result as the previous version, set `scale` to `1.0 / downscale_factor`.


===============================================================
`frame_timecode` Constants
===============================================================

Replace uses of both `MAX_FPS_DELTA` and `MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT` from :py:mod:`scenedetect.frame_timecode` with :py:data:`MAX_FPS_DELTA <scenedetect.frame_timecode.MAX_FPS_DELTA>`.
