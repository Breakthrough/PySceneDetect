
.. _scenedetect-migration_guide:

---------------------------------------------------------------
Migration Guide
---------------------------------------------------------------

This page details how to transition a program written using PySceneDetect 0.5 to the new 0.6 API. It is recommended to review the new :ref:`Quickstart <scenedetect-quickstart>` and :ref:`Example <scenedetect-detailed_example>` sections first, as they should cover the majority of use cases. Also see `tests/test_api.py <https://github.com/Breakthrough/PySceneDetect/blob/v0.6.4-release/tests/test_api.py>`_ for a set of demonstrations covering many high level use cases.

PySceneDetect v0.6 is a major step towards a more stable and simplified API.  The biggest change to existing workflows is how video input is handled, and that Python 3.6 or above is now required.

This page covers commonly used APIs which require updates to work with v0.6.  Note that this page is not an exhaustive set of changes.  For a complete list of breaking API changes, see `the changelog <https://www.scenedetect.com/changelog/>`_.

In some places, a backwards compatibility layer has been added to avoid breaking most applications upon release. This should not be relied upon, and will be removed in the future. You can call ``scenedetect.platform.init_logger(show_stdout=True)`` or attach a custom log handler to the ``'pyscenedetect'`` logger to help find these cases.


===============================================================
`VideoManager` Class
===============================================================

`VideoManager` has been deprecated and replaced with :mod:`scenedetect.backends`.  For most applications, the :func:`open_video <scenedetect.open_video>` function should be used instead:

.. code:: python

    from scenedetect import open_video
    video = open_video(video.mp4')

The resulting object can then be passed to a :class:`SceneManager <scenedetect.scene_manager.SceneManager>` when calling :meth:`detect_scenes <scenedetect.scene_manager.SceneManager.detect_scenes>`, or any other function/method that used to take a `VideoManager`, e.g.:

.. code:: python

    from scenedetect import open_video, SceneManager, ContentDetector
    video = open_video('video.mp4')
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    scene_manager.detect_scenes(video)
    print(scene_manager.get_scene_list())

See :mod:`scenedetect.backends` for examples of how to create specific backends.  Where previously a list of paths was accepted, now only a single string should be provided.


Seeking and Start/End Times
===============================================================

Instead of setting the start time via the `VideoManager`, now :meth:`seek <scenedetect.video_stream.VideoStream.seek>` to the starting time on the :class:`VideoStream <scenedetect.video_stream.VideoStream>` object.

Instead of setting the duration or end time via the `VideoManager`, now set the `duration` or `end_time` parameters when calling :meth:`detect_scenes <scenedetect.scene_manager.SceneManager.detect_scenes>`.

.. code:: python

    from scenedetect import open_video, SceneManager, ContentDetector
    video = open_video('video.mp4')
    # Can be seconds (float), frame # (int), or FrameTimecode
    start_time, end_time = 2.5, 5.0
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    video.seek(start_time)
    # Note there is also a `duration` parameter that can also be set.
    # If neither `duration` nor `end_time` is provided, the video will
    # be processed from its current position until the end.
    scene_manager.detect_scenes(video, end_time=end_time)
    print(scene_manager.get_scene_list())


===============================================================
`SceneManager` Class
===============================================================

The first argument of the :meth:`detect_scenes <scenedetect.scene_manager.SceneManager.detect_scenes>` method has been renamed to `video` and should now be a :class:`VideoStream <scenedetect.video_stream.VideoStream>` object (see above).


===============================================================
`save_images` Function
===============================================================

The second argument of :func:`save_images <scenedetect.scene_manager.save_images>` in :mod:`scenedetect.scene_manager` has been renamed from `video_manager` to `video`.

The `downscale_factor` parameter has been removed from :func:`save_images <scenedetect.scene_manager.save_images>` (use the `scale` parameter instead). To achieve the same result as the previous version, set `scale` to `1.0 / downscale_factor`.


===============================================================
`split_video_*` Functions
===============================================================

The the :mod:`scenedetect.video_splitter` functions :func:`split_video_ffmpeg <scenedetect.video_splitter.split_video_ffmpeg>` and :func:`split_video_mkvmerge <scenedetect.video_splitter.split_video_mkvmerge>` now only accept a single path as the input (first) argument.

The `suppress_output` and `hide_progress` arguments to the :func:`split_video_ffmpeg <scenedetect.video_splitter.split_video_ffmpeg>` and :func:`split_video_mkvmerge <scenedetect.video_splitter.split_video_mkvmerge>` have been removed, and two new options have been added:

 * `suppress_output` is now `show_output`, default is `False`
 * `hide_progress` is now `show_progress`, default is `False`

This makes the API consistent with that of :class:`SceneManager <scenedetect.scene_manager.SceneManager>`.


===============================================================
`StatsManager` Class
===============================================================

The :func:`save_to_csv <scenedetect.stats_manager.StatsManager.save_to_csv>` and :func:`load_from_csv <scenedetect.stats_manager.StatsManager.save_to_csv>` methods now accept either a `path` or an open `file` handle.

The `base_timecode` argument has been removed from :func:`save_to_csv <scenedetect.stats_manager.StatsManager.save_to_csv>`. It is no longer required.


===============================================================
`AdaptiveDetector` Class
===============================================================

The `video_manager` parameter has been removed and is no longer required when constructing an :class:`AdaptiveDetector <scenedetect.detectors.adaptive_detector.AdaptiveDetector>` object.


===============================================================
Other
===============================================================

`ThresholdDetector` Class
===============================================================

The `block_size` argument has been removed from the :class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>` constructor. It is no longer required.


`ContentDetector` Class
===============================================================

The `calculate_frame_score` method of :class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>` has been renamed to :meth:`_calculate_frame_score <scenedetect.detectors.content_detector.ContentDetector._calculate_frame_score>`. Use new global function :func:`calculate_frame_score <scenedetect.detectors.content_detector.calculate_frame_score>` to achieve the same result.


`MINIMUM_FRAMES_PER_SECOND_*` Constants
===============================================================

In :mod:`scenedetect.frame_timecode` the constants `MINIMUM_FRAMES_PER_SECOND_FLOAT` and `MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT` have been replaced with :data:`MAX_FPS_DELTA <scenedetect.frame_timecode.MAX_FPS_DELTA>`.


`get_aspect_ratio` Function
===============================================================

 The `get_aspect_ratio` function has been removed from `scenedetect.platform`. Use the :attr:`aspect_ratio <scenedetect.video_stream.VideoStream.aspect_ratio>` property from the :class:`VideoStream <scenedetect.video_stream.VideoStream>`  object instead.
