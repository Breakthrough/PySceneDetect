
***********************************************************************
``scenedetect`` 🎬 Application
***********************************************************************

=======================================================================
Quickstart
=======================================================================

Split the input video wherever a new scene is detected:

    ``scenedetect -i video.mp4 detect-content split-video``

Print a table of detected scenes to the terminal, and save an image
at the start, middle, and end frame of each scene:

    ``scenedetect -i video.mp4 detect-content list-scenes -n save-images``

Skip the first 10 seconds of the input video:

    ``scenedetect -i video.mp4 time -s 10s detect-content``

To show a summary of all other options and commands:

    ``scenedetect help``

You can also type `help command` where `command` is a specific command
or detection algorithm (e.g. `detect-content`, `split-video`). To show a
complete help listing for every command:

    ``scenedetect help all``


=======================================================================
Overview
=======================================================================

The options in this section represent the "global" arguments for the
main ``scenedetect`` command. The most commonly used options are the
input video
(`--input video.mp4`), the output directory (`--output video_out`), and
the stats file to use (`--stats video.stats.csv`).

Your commands should follow the form:

    ``scenedetect [global options] [detector] [commands]``

Where `[global options]` are the options on **this** page, `[detector]` is a scene
detection algorithm (`detect-content` or `detect-threshold`), and `[commands]`
are any other commands to be performed, and their own options (e.g.
`time --start 00:01:30`, `split-video -hq`).

.. note::
   Any options on this page (global options) *must* be set before using
   any commands.  Your commands should follow the form (where square brackets
   denote things that may be optional):

       ``scenedetect (global options) (command-A [command-A options]) (...)``

   This is because once a command is specified, all options/arguments afterwards
   will be parsed assuming they belong to *that* command.


=======================================================================
Global Options
=======================================================================

The ``scenedetect`` command takes the following global options:


  -i, --input VIDEO      [Required] Input video file. May be specified
                         multiple times to concatenate several videos
                         together. Also supports image sequences and URLs.
  -o, --output DIR       Output directory for all files (stats file, output
                         videos, images, log files, etc...).
  -f, --framerate FPS    Force framerate, in frames/sec (e.g. -f 29.97).
                         Disables check to ensure that all input videos have
                         the same framerates.
  -d, --downscale N      Integer factor to downscale frames by (e.g. 2, 3,
                         4...), where the frame is scaled to width/`N` x
                         height/`N` (thus `-d 1` implies no downscaling). Each
                         increment speeds up processing by a factor of 4 (e.g.
                         `-d 2` is 4 times quicker than `-d 1`). Higher values can
                         be used for high definition content with minimal
                         effect on accuracy. [default: 2 for SD, 4 for 720p, 6
                         for 1080p, 12 for 4k]
  -m, --min-scene-len TIMECODE
                         Minimum size/length of any scene. TIMECODE can
                         be specified as exact number of frames, a time
                         in seconds followed by s, or a timecode in the
                         format HH:MM:SS or HH:MM:SS.nnn [default: 0.6s]
  --drop-short-scenes    Drop scenes shorter than `--min-scene-len`
                         instead of combining them with neighbors
  -s, --stats CSV        Path to stats file (.csv) for writing frame metrics
                         to. If the file exists, any metrics will be
                         processed, otherwise a new file will be created. Can
                         be used to determine optimal values for various scene
                         detector options, and to cache frame calculations in
                         order to speed up multiple detection runs.
  -l, --logfile LOG      Path to log file for writing application logging
                         information, mainly for debugging. Make sure to set
                         `-v debug` as well if you are submitting a bug
                         report.
  -v, --verbosity LEVEL  Level of debug/info/error information to show.
                         Can be one of: `none`, `debug`, `info`, `warning`, `error`.
                         May be overriden by `-q`/`--quiet`.
                         Setting to `none` will suppress all output except that
                         generated by actions (e.g. timecode list output).
                         [default: `info`]
  -q, --quiet            Suppresses all output of PySceneDetect except for
                         those from the specified commands. Equivalent to
                         setting `--verbosity none`. Overrides the current
                         verbosity level, even if `-v`/`--verbosity` is set.
  -fs, --frame-skip N    **Not recommended, disallows use of a stats file**
                         (the `-s`/`--stats` option).
                         Skips `N` frames during processing (-fs 1 skips every
                         other frame, processing 50% of the video, -fs 2
                         processes 33% of the frames, -fs 3 processes 25%,
                         etc...). Reduces processing speed at expense of
                         accuracy.  [default: 0]


=======================================================================
Detectors and Commands
=======================================================================

Calls to the `scenedetect` command should be specified as follows:

    ``scenedetect [global options] [detector] [commands]``

`[detector]` specifies which :ref:`scene detection algorithm<cli-detectors>` to use.
`[commands]` specify one or more :ref:`commands<cli-commands>` (or "actions"), such
as splitting the input video, or saving a thumbnail for each scene.  Each command
can have its own sub-options, which are documented in the following sections of
this manual.

As an example, to use the `--input` and `--stats` options from above along with
the `detect-content` detector on a file `video.mp4`, and using the `list-scenes`
command to print a table of detected scenes to the terminal:

    ``scenedetect -i video.mp4 -s video.stats.csv detect-content list-scenes -n``

More examples can be found in the following section, which details the options for
all available commands.
