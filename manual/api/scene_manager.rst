SceneManager
-----------------------------------

.. automodule:: scenedetect.scene_manager

Usage Example
===================================

In the code example below, we create a function ``find_scenes()`` which performs
the following actions:

 * loads a video file by path (`str`) as argument `video_path` using a
   :py:class:`VideoManager <scenedetect.video_manager.VideoManager>`
 * loads/saves a stats file for the video to ``{video_path}.stats.csv`` using a
   :py:class:`StatsManager <scenedetect.stats_manager.StatsManager>`
 * performs content-aware scene detection on the video using a 
   :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`
   bound to a :py:class:`SceneManager`
 * ``print()`` out a table of detected scenes to the terminal/console
 * returns a list of tuples of
   :py:class:`FrameTimecode <scenedetect.frame_timecode.FrameTimecode>`
   objects of the start and end times for each detected scene

This example is a modified version of
`the api_test.py file <https://github.com/Breakthrough/PySceneDetect/blob/master/api_test.py>`_,
and shows complete usage of a
:py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` object
to perform content-aware scene detection using the
:py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`,
printing a list of scenes, and both saving/loading a stats file to make
subsequent calls to the script (specifically the
:py:meth:`detect_scenes <SceneManager.detect_scenes>` method) significantly faster.

.. code:: python

    import os

    import scenedetect
    from scenedetect.video_manager import VideoManager
    from scenedetect.scene_manager import SceneManager
    from scenedetect.frame_timecode import FrameTimecode
    from scenedetect.stats_manager import StatsManager      # for saving/loading stats file
    from scenedetect.detectors import ContentDetector       # for content-aware scene detection

    def find_scenes(video_path):
        # type: (str) -> List[Tuple[FrameTimecode, FrameTimecode]]
        video_manager = VideoManager([video_path])
        stats_manager = StatsManager()
        # Construct our SceneManager and pass it our StatsManager instance.
        scene_manager = SceneManager(stats_manager)

        # Add ContentDetector algorithm (constructor takes detector options like threshold).
        scene_manager.add_detector(ContentDetector())
        base_timecode = video_manager.get_base_timecode()

        # We save our stats file to {VIDEO_PATH}.stats.csv.
        stats_file_path = '%s.stats.csv' % video_path

        scene_list = []

        try:
            # If stats file exists, load it.
            if os.path.exists(stats_file_path):
                # Read stats from CSV file opened in read mode:
                with open(stats_file_path, 'r') as stats_file:
                    stats_manager.load_from_csv(stats_file, base_timecode)

            start_time = base_timecode + 20     # 00:00:00.667
            end_time = base_timecode + 20.0     # 00:00:20.000
            # Set video_manager duration to read frames from 00:00:00 to 00:00:20.
            video_manager.set_duration(start_time=start_time, end_time=end_time)

            # Set downscale factor to improve processing speed.
            video_manager.set_downscale_factor()

            # Start video_manager.
            video_manager.start()

            # Perform scene detection on video_manager.
            scene_manager.detect_scenes(frame_source=video_manager,
                                        start_time=start_time)

            # Obtain list of detected scenes.
            scene_list = scene_manager.get_scene_list(base_timecode)
            # Like FrameTimecodes, each scene in the scene_list can be sorted if the
            # list of scenes becomes unsorted.

            print('List of scenes obtained:')
            for i, scene in enumerate(scene_list):
                print('    Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
                    i+1,
                    scene[0].get_timecode(), scene[0].get_frames(),
                    scene[1].get_timecode(), scene[1].get_frames(),))

            # We only write to the stats file if a save is required:
            if stats_manager.is_save_required():
                with open(stats_file_path, 'w') as stats_file:
                    stats_manager.save_to_csv(stats_file, base_timecode)

        finally:
            video_manager.release()

        return scene_list



``SceneManager`` Class
===================================

.. autoclass:: scenedetect.scene_manager.SceneManager
   :members:
   :undoc-members:


``scene_manager`` Functions
===============================================================

.. autofunction:: scenedetect.scene_manager.write_scene_list

