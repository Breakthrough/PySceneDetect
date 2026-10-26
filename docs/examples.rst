.. _examples:

--------
Examples
--------

Each task shows the command line first, then the same task in Python. Every command in the
:doc:`CLI reference <cli>` links to its Python API and config file
counterparts, and each detector to a table of its options.

All examples assume a file called ``video.mp4`` in the working directory. Most Python examples
use :func:`scenedetect.detect`, which returns a list of ``(start, end)``
:class:`FrameTimecode <scenedetect.common.FrameTimecode>` pairs (empty if no cuts are found);
see :ref:`SceneManager <scenedetect-scene_manager>` for lower-level control.

Split a Video Into Scenes
-------------------------

Find the scenes and write one clip per scene. Requires ``ffmpeg`` (or ``mkvmerge`` with
``split-video -m`` / :func:`~scenedetect.output.split_video_mkvmerge`).

Command line:

.. code:: bash

    scenedetect -i video.mp4 split-video

Python:

.. code:: python

    from scenedetect import detect, ContentDetector, split_video_ffmpeg

    scenes = detect("video.mp4", ContentDetector())
    split_video_ffmpeg("video.mp4", scenes)

Save the Scene List as CSV
--------------------------

Write the scene list to ``video-Scenes.csv``.

Command line:

.. code:: bash

    scenedetect -i video.mp4 list-scenes

Python:

.. code:: python

    from scenedetect import detect, ContentDetector, write_scene_list

    scenes = detect("video.mp4", ContentDetector())
    write_scene_list("video-Scenes.csv", scenes)

Save Images From Each Scene
---------------------------

Save three images from each scene (start, middle, end) into the ``images`` directory.

Command line:

.. code:: bash

    scenedetect -i video.mp4 -o images save-images --num-images 3

Python:

.. code:: python

    from scenedetect import detect, open_video, ContentDetector, save_images

    scenes = detect("video.mp4", ContentDetector())
    video = open_video("video.mp4")
    save_images(scenes, video, num_images=3, output_dir="images")

Pick a Detector and Tune It
---------------------------

Every detector is both a ``detect-*`` command and a class in
:ref:`scenedetect.detectors <scenedetect-detectors>`. Options map to constructor arguments of
the same name, with a few exceptions listed on that page. Here, a lower threshold makes
:ref:`detect-content <command-detect-content>` more sensitive.

Command line:

.. code:: bash

    scenedetect -i video.mp4 detect-content --threshold 20

Python:

.. code:: python

    from scenedetect import detect, ContentDetector

    scenes = detect("video.mp4", ContentDetector(threshold=20))

Detect Fades In and Out
-----------------------

:ref:`detect-threshold <command-detect-threshold>` finds fades to and from black instead of
fast cuts. Defaults differ: the command adds a final scene and ignores fades shorter than
``0.1s``, while :class:`ThresholdDetector <scenedetect.detectors.ThresholdDetector>` does
neither (see :ref:`Detectors <scenedetect-detectors>`).

Command line:

.. code:: bash

    scenedetect -i video.mp4 detect-threshold

Python:

.. code:: python

    from scenedetect import detect, ThresholdDetector

    scenes = detect("video.mp4", ThresholdDetector())

Set a Minimum Scene Length
--------------------------

Cuts closer together than this are ignored. On the command line
:option:`-m/--min-scene-len <scenedetect -m>` applies to every detector and defaults to
``0.6s``; in Python each detector takes ``min_scene_len`` and defaults to ``15`` frames.

Command line:

.. code:: bash

    scenedetect -i video.mp4 -m 2s detect-content

Python:

.. code:: python

    from scenedetect import detect, ContentDetector

    scenes = detect("video.mp4", ContentDetector(min_scene_len="2s"))

Analyze Only Part of the Video
------------------------------

Skip the first 10 seconds and stop after one minute. Times can be given as frames (``100``),
seconds (``10s``) or timecodes (``00:01:00``).

Command line:

.. code:: bash

    scenedetect -i video.mp4 time --start 10s --end 00:01:00 detect-content

Python:

.. code:: python

    from scenedetect import detect, ContentDetector

    scenes = detect("video.mp4", ContentDetector(), start_time="10s", end_time="00:01:00")

Save Per-Frame Statistics
-------------------------

Write the metric each detector computes for every frame to a CSV file, to help choose a
threshold.

Command line:

.. code:: bash

    scenedetect -i video.mp4 -s stats.csv detect-content

Python:

.. code:: python

    from scenedetect import detect, ContentDetector

    scenes = detect("video.mp4", ContentDetector(), stats_file_path="stats.csv")

Use a Different Video Backend
-----------------------------

Decode with PyAV instead of OpenCV (see :ref:`Video Backends <scenedetect-backends>`).

Command line:

.. code:: bash

    scenedetect -i video.mp4 -b pyav detect-content

Python:

.. code:: python

    from scenedetect import detect, ContentDetector

    scenes = detect("video.mp4", ContentDetector(), backend="pyav")

Run Several Detectors at Once
-----------------------------

Find both fast cuts and fades. In Python this needs a
:class:`SceneManager <scenedetect.scene_manager.SceneManager>`, which also gives you per-frame
callbacks and access to the cut list.

Command line:

.. code:: bash

    scenedetect -i video.mp4 detect-content detect-threshold

Python:

.. code:: python

    from scenedetect import open_video, SceneManager, ContentDetector, ThresholdDetector

    video = open_video("video.mp4")
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.add_detector(ThresholdDetector())
    scene_manager.detect_scenes(video, show_progress=True)
    scenes = scene_manager.get_scene_list()
