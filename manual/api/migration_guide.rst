
.. _scenedetect-migration_guide:

---------------------------------------------------------------
Migration Guide
---------------------------------------------------------------

This page details how to transition a program written using PySceneDetect v0.5 to the new v0.6 API.

PySceneDetect v0.6 is a major step towards a more stable and simplified API.  The biggest change to most existing workflows is how video input is handled, and that Python 3.6 or above is now required.

This page covers the most commonly used APIs which require updates to work with v0.6.  Note that this page is not an exhaustive set of changes.  For a complete list of breaking API changes, see `the changelog <https://pyscenedetect.readthedocs.io/en/latest/changelog/>`_.


===============================================================
`VideoManager` Class
===============================================================

`VideoManager` has been removed and placed with :py:mod:`scenedetect.backends`.  For most applications, the easiest way to update this is to use the :py:func:`open_video <scenedetect.backends.open_video>` function:

.. code:: python

    from scenedetect import open_video
    video = open_video(video.mp4')

The resulting object can then be passed to a :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` when calling :py:meth:`detect_scenes <scenedetect.scene_manager.SceneManager.detect_scenes>`, or any other function/method that used to take a `VideoManager`, e.g.:

    from scenedetect import open_video, SceneManager, ContentDetector
    video = open_video('video.mp4')
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    scene_manager.detect_scenes(video)
    print(scene_manager.get_scene_list())

See :py:mod:`scenedetect.backends` for examples of how to create specific backends. Note that where previously a list of paths was accepted, now only a single string should be provided.


===============================================================
`SceneManager` Class
===============================================================

The first argument of the :py:meth:`detect_scenes <scenedetect.scene_manager.SceneManager.detect_scenes>` method has been renamed to `video` and should now be a :py:class:`VideoStream <scenedetect.video_stream.VideoStream>` object (see above).


===============================================================
`save_images` Function
===============================================================

The second argument of :py:func:`save_images <scenedetect.scene_manager.save_images>` in :py:mod:`scenedetect.scene_manager` has been renamed from `video_manager` to `video`.

The `downscale_factor` parameter has been removed from :py:func:`save_images <scenedetect.scene_manager.save_images>` (use the `scale` parameter instead). To achieve the same result as the previous version, set `scale` to `1.0 / downscale_factor`.


===============================================================
`split_video_*` Functions
===============================================================

The the :py:mod:`scenedetect.video_splitter` functions :py:func:`split_video_ffmpeg <scenedetect.video_splitter.split_video_ffmpeg>` and :py:func:`split_video_mkvmerge <scenedetect.video_splitter.split_video_mkvmerge>` now only accept a single path as the input (first) argument, where previously it was required to be a list.

The `suppress_output` and `hide_progress` arguments to the :py:func:`split_video_ffmpeg <scenedetect.video_splitter.split_video_ffmpeg>` and :py:func:`split_video_mkvmerge <scenedetect.video_splitter.split_video_mkvmerge>` have been removed, and two new options have been added:

 * `suppress_output` is now `show_output`, default is `False`
 * `hide_progress` is now `show_progress`, default is `False`

This makes the API consistent with that of :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>`.


===============================================================
`StatsManager` Class
===============================================================

The :py:func:`save_to_csv <scenedetect.stats_manager.StatsManager.save_to_csv>` and :py:func:`load_from_csv <scenedetect.stats_manager.StatsManager.save_to_csv>` methods now accept either a `path` or an open `file` handle.


===============================================================
`AdaptiveDetector` Class
===============================================================

The `video_manager` parameter has been removed and is no longer required when constructing an :py:class:`AdaptiveDetector <scenedetect.detectors.adaptive_detector.AdaptiveDetector>` object.


===============================================================
Other
===============================================================

`ThresholdDetector` Class
===============================================================

The `block_size` argument has been removed from the :py:class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>`` constructor. It is no longer required.


`ContentDetector` Class
===============================================================

The `calculate_frame_score` method of :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>` has been renamed to :py:meth:`_calculate_frame_score <scenedetect.detectors.content_detector.ContentDetector._calculate_frame_score>`. Use new global function :py:func:`calculate_frame_score <scenedetect.detectors.content_detector.calculate_frame_score>` to achieve the same result.


`MINIMUM_FRAMES_PER_SECOND_*` Constants
===============================================================

In :py:mod:`scenedetect.frame_timecode` the constants `MINIMUM_FRAMES_PER_SECOND_FLOAT` and `MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT` have been replaced with :py:data:`MAX_FPS_DELTA <scenedetect.frame_timecode.MAX_FPS_DELTA>`.

