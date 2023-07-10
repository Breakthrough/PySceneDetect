
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

    ``scenedetect help``


=======================================================================
Overview
=======================================================================

PySceneDetect is used by specifying a detector and some commands to process a video with:

    ``scenedetect -i video.mp4 [detectors] [commands]``

Global options (e.g. `--input`, `--config`) must be specified before any commands. The order of commands is not strict, but each command should only be specified once. Detectors and commands can also have options:

    ``scenedetect -i video.mp4 detect-adaptive -t 30 list-scenes -n``

If a detector is not specified, ``detect-adaptive`` will be used by default. The default detector can be configured using a :ref:`a config file <scenedetect_cli-config_file>`.

You can use `help [command]` where `[command]` is a specific command or detection algorithm (e.g. `scenedetect help detect-content` or `scenedetect help split-video`). To show the complete help reference for the program you can run:

    ``scenedetect help all``


=======================================================================
System Dependencies
=======================================================================

If you are having trouble running PySceneDetect, check installed software dependencies with:

    ``scenedetect version --all``

Please include this information when submitting bug reports.


=======================================================================
Global Options
=======================================================================

.. option:: --input VIDEO, -i VIDEO

  [Required] Input video file. Also supports image sequences and URLs.

.. option:: --output DIR, -o DIR

  Output directory for created files (stats file, output videos, images, etc...). If not set defaults to working directory. Some commands allow overriding this value.

.. option:: --config FILE, -c FILE

  Path to config file.

.. option:: --stats CSV, -s CSV

  Stats file (.csv) path to write frame metrics. If the file exists, existing metrics will be overwritten. Can be used to find optimal detector options or for data analysis.

.. option:: --framerate FPS, -f FPS

  Override framerate with value as frames/sec (e.g. ``-f 29.97``).

.. option:: --min-scene-len TIMECODE, -m TIMECODE

  Minimum length of any scene. TIMECODE can be specified as exact number of frames, a time in seconds followed by s, or a timecode in the format HH:MM:SS or HH:MM:SS.nnn. [default: ``0.6s``]

.. option:: --drop-short-scenes

  Drop scenes shorter than ``--min-scene-len`` instead of combining them with neighbors.

.. option:: --merge-last-scene

  Merge last scene with previous if shorter than ``--min-scene-len``.

.. option:: --backend BACKEND, -b BACKEND

  Backend to use for video input. Backend options can be set using a config file (``-c``/``--config``). [available\: opencv, pyav, moviepy] [default: opencv].

.. option:: --downscale N, -d N

  Integer factor to downscale video by (e.g. 2, 3, 4...) before processing. Frame is scaled to width/N x height/N. If unset, value is auto selected based on resolution. Set to 1 to disable downscaling.

.. option:: --frame-skip N, -fs N

  Skips N frames during processing (-fs 1 skips every other frame, processing 50% of the video, -fs 2 processes 33% of the frames, -fs 3 processes 25%, etc...). Reduces processing speed at expense of accuracy. [default: ``0``]

.. option:: --verbosity LEVEL, -v LEVEL

  Level of debug/info/error information to show. Must be one of\: debug, info, warning, error, none. Overrides ``-q``/``--quiet``. Use ``-v debug`` for bug reports. [default: ``info``]

.. option:: --logfile LOG, -l LOG

  Path to log file for writing application logging information, mainly for debugging. Set ``-v debug`` as well if you are submitting a bug report. If verbosity is none, logfile is still be generated with info-level verbosity.

.. option:: --quiet, -q

  Suppresses all output of PySceneDetect to the terminal/stdout. Equivalent to ``-v none``.
