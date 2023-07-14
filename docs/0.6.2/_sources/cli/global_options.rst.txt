
***********************************************************************
``scenedetect`` 🎬 Application
***********************************************************************

=======================================================================
Quickstart
=======================================================================

Split the input video wherever a new scene is detected:

    ``scenedetect -i video.mp4 split-video``

Save scene list in CSV format with images at the start, middle, and end of each scene:

    ``scenedetect -i video.mp4 list-scenes save-images``

Skip the first 10 seconds of the input video:

    ``scenedetect -i video.mp4 time --start 10s detect-content``

Show summary of all options and commands:

    ``scenedetect --help``


=======================================================================
Overview
=======================================================================

PySceneDetect is used by specifying a detector and some commands to process a video with:

    ``scenedetect -i video.mp4 [detectors] [commands]``

Global options (e.g. `--input`, `--config`) must be specified before any commands. The order of commands is not strict, but each command should only be specified once. Detectors and commands can also have options:

    ``scenedetect -i video.mp4 detect-adaptive -t 30 list-scenes -n``

If a detector is not specified, ``detect-adaptive`` will be used by default. The default detector can be configured using a :ref:`a config file <scenedetect_cli-config_file>`.

You can use `[command] --help` where `[command]` is a specific command or detector (e.g. `scenedetect detect-content --help`). To show the complete help reference for the program you can run:

    ``scenedetect help all``


=======================================================================
System Dependencies
=======================================================================

If you are having trouble running PySceneDetect, check installed software dependencies with:

    ``scenedetect version --all``

Please include this information when submitting bug reports.


.. program:: scenedetect

=======================================================================
Global Options
=======================================================================

.. option:: -i VIDEO, --input VIDEO

  [REQUIRED] Input video file. Image sequences and URLs are supported.

.. option:: -o DIR, --output DIR

  Output directory for created files. If unset, working directory will be used. May be overriden by command options.

.. option:: -c FILE, --config FILE

  Path to config file. See :ref:`config file reference <scenedetect_cli-config_file>` for details.

.. option:: -s CSV, --stats CSV

  Stats file (.csv) to write frame metrics. Existing files will be overwritten. Used for tuning detection parameters and data analysis.

.. option:: -f FPS, --framerate FPS

  Override framerate with value as frames/sec.

.. option:: -m TIMECODE, --min-scene-len TIMECODE

  Minimum length of any scene. TIMECODE can be specified as number of frames (:option:`-m=10 <-m>`), time in seconds followed by "s" (:option:`-m=2.5s <-m>`), or timecode (:option:`-m=00:02:53.633 <-m>`).

  Default: ``0.6s``

.. option:: --drop-short-scenes

  Drop scenes shorter than :option:`-m/--min-scene-len <-m>`, instead of combining with neighbors.

.. option:: --merge-last-scene

  Merge last scene with previous if shorter than :option:`-m/--min-scene-len <-m>`.

.. option:: -b BACKEND, --backend BACKEND

  Backend to use for video input. Backend options can be set using a config file (:option:`-c/--config <-c>`). [available: opencv, pyav, moviepy]

  Default: ``opencv``

.. option:: -d N, --downscale N

  Integer factor to downscale video by before processing. If unset, value is selected based on resolution. Set :option:`-d=1 <-d>` to disable downscaling.

.. option:: -fs N, --frame-skip N

  Skip N frames during processing. Reduces processing speed at expense of accuracy. :option:`-fs=1 <-fs>` skips every other frame processing 50% of the video, :option:`-fs=2 <-fs>` processes 33% of the video frames, :option:`-fs=3 <-fs>` processes 25%, etc...

  Default: ``0``

.. option:: -v LEVEL, --verbosity LEVEL

  Amount of information to show. Must be one of: debug, info, warning, error, none. Overrides :option:`-q/--quiet <-q>`.

  Default: ``info``

.. option:: -l FILE, --logfile FILE

  Save debug log to FILE. Appends to existing file if present.

.. option:: -q, --quiet

  Suppress output to terminal/stdout. Equivalent to setting :option:`--verbosity=none <--verbosity>`.
