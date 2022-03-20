
***********************************************************************
``scenedetect`` 🎬 Application
***********************************************************************

=======================================================================
Quickstart
=======================================================================

Split the input video wherever a new scene is detected:

    ``scenedetect -i video.mp4 detect-content split-video``

Print a table of detected scenes to the terminal, and save an image at the start, middle, and end frame of each scene:

    ``scenedetect -i video.mp4 detect-content list-scenes -n save-images``

Skip the first 10 seconds of the input video:

    ``scenedetect -i video.mp4 time -s 10s detect-content``

To show a summary of all options and commands:

    ``scenedetect help``

You can also type `help [command]` where `[command]` is a specific command or detection algorithm (e.g. `scenedetect help detect-content` or `scenedetect help split-video`). To show a complete help listing for every command:

    ``scenedetect help all``


=======================================================================
Overview
=======================================================================

The PySceneDetect command-line interface is grouped into commands which can be combined together, each containing its own set of arguments:

    ``scenedetect [global options] [detectors] [commands]``

Where [command] is the name of the command, and ([options]) are the arguments/options associated with the command, if any. Global options (e.g. `--input`, `--framerate`) must be specified before any commands. The order of commands is not strict, but each command should only be specified once.


=======================================================================
Global Options
=======================================================================

The ``scenedetect`` command takes the following global options:


  -i, --input VIDEO             [Required] Input video file. Also supports
                                image sequences and URLs.

  -o, --output DIR              Output directory for created files (stats
                                file, output videos, images, etc...). If not
                                set defaults to working directory. Some
                                commands allow overriding this value.

  -f, --framerate FPS           Force framerate, in frames/sec (e.g. -f
                                29.97). Disables check to ensure that all
                                input videos have the same framerates.

  -d, --downscale N             Integer factor to downscale frames by (e.g. 2,
                                3, 4...), where the frame is scaled to width/N
                                x height/N (thus -d 1 implies no downscaling).
                                Leave unset for automatic downscaling based on
                                source resolution.

  -fs, --frame-skip N           Skips N frames during processing (-fs 1 skips
                                every other frame, processing 50% of the
                                video, -fs 2 processes 33% of the frames, -fs
                                3 processes 25%, etc...). Reduces processing
                                speed at expense of accuracy. [default: 0]

  -m, --min-scene-len TIMECODE  Minimum length of any scene. TIMECODE can be
                                specified as exact number of frames, a time in
                                seconds followed by s, or a timecode in the
                                format HH:MM:SS or HH:MM:SS.nnn. [default:
                                0.6s]

  --drop-short-scenes           Drop scenes shorter than `min-scene-len`
                                instead of combining them with neighbors.

  --merge-last-scene            Merge last scene with previous if shorter than
                                min-scene-len.

  -s, --stats CSV               Path to stats file (.csv) for writing frame
                                metrics to. If the file exists, any metrics
                                will be processed, otherwise a new file will
                                be created. Can be used to determine optimal
                                values for various scene detector options, and
                                to cache frame calculations in order to speed
                                up multiple detection runs.

  -v, --verbosity LEVEL         Level of debug/info/error information to show.
                                Must be one of: debug, info, warning, error,
                                none. Overrides `-q`/`--quiet`. Use `-v debug`
                                for bug reports. [default: info]

  -l, --logfile LOG             Path to log file for writing application
                                logging information, mainly for debugging. Set
                                `-v debug` as well if you are submitting a bug
                                report. If verbosity is none, logfile is still
                                be generated with info-level verbosity.

  -q, --quiet                   Suppresses all output of PySceneDetect to the
                                terminal/stdout. Equivalent to `-v none`.

  -b, --backend BACKEND         Name of backend to use for video input.
                                Backends available on this system:
                                dict_keys(['opencv', 'pyav']) [default:
                                opencv]

  -c, --config FILE             Path to config file. If not set, tries to load
                                one from a location based on your operating system.
                                Type `scenedetect help` and this option will show
                                the correct path on your system.
