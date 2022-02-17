
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


===============================================================
`split_video_*` Functions
===============================================================

The `suppress_output` and `hide_progress` arguments passed to the :py:func:`split_video_ffmpeg <scenedetect.video_splitter.split_video_ffmpeg>` and :py:func:`split_video_mkvmerge <scenedetect.video_splitter.split_video_mkvmerge>` have been renamed, and have new defaults:

 * `suppress_output` is now `show_output`, default is `False`

 * `hide_progress` is now `show_progress`, default is `False`

This makes the API consistent with that of :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>`.
