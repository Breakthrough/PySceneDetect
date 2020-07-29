
***********************************************************************
Command Reference
***********************************************************************

The following commands are available when using ``scenedetect``.
Several commands can be combined together (the order does not
matter) to control various input/output options.

The following is a list of the available commands along with a
brief description of the command's function and an example.


Help/information commands (prints information and quits):

 - ``help`` - Prints help and usage information for commands
    ``help``, ``help [command]``, or ``help all``
 - ``about`` - Prints license and copyright information about PySceneDetect
    ``about``
 - ``version`` - Print PySceneDetect version number
    ``version``


Input/output commands (applies to input videos and detected scenes):

 - ``time`` - Set start time/end time/duration of input video(s)
    ``time --start 00:01:00 --end 00:02:00``
 - ``list-scenes`` - Write list of scenes and timecodes to the terminal as well as a .CSV file
    ``list-scenes``
 - ``save-images`` - Saves a given number of frames from every detected scene as images, by default JPEG
    ``save-images --quality 80``
 - ``split-video`` - Automatically split input video using either `ffmpeg` (`split-video` or `split-video -hq` for higher quality), or `mkvmerge` (`split-video --copy`)
    ``split-video`` or ``split-video -hq`` for higher quality, ``split-video --copy`` for no re-encoding
 - ``export-html`` - Exports scene list to a HTML file.  Requires ``save-images`` by default.

.. note:: When using multiple commands, make sure to not
   specify the same command twice. The order of commands does
   not matter, but each command should only be specified once.


=======================================================================
``help``, ``version``, and ``about``
=======================================================================

**The** ``help`` **command** prints PySceneDetect options and help information.  Usage:

 * ``help``
    Shows the main `scenedetect` program options and a list of commands.
 * ``help [command]``
    Shows options for a specific command/detector (`help list-scenes`, `help detect-threshold`).
 * ``help all``
    Shows the options and help information for *all* commands.

**The** ``version`` **command** command prints the version of PySceneDetect that is installed.

**The** ``about`` **command** prints PySceneDetect copyright, licensing, and redistribution
information.  This includes a list of all third-party software components that
PySceneDetect uses or interacts with, as well as a reference to the license and
copyright information for each component.


Usage Examples
-----------------------------------------------------------------------

The ``help`` command:

    ``scenedetect help``

    ``scenedetect help all``

    ``scenedetect help detect-content``

The ``about`` command:

    ``scenedetect about``

The ``version`` command:

    ``scenedetect version``

The program will terminate immediately after printing the requested information
if any of the above commands are given.


=======================================================================
``time``
=======================================================================

**The** ``time`` **command** is used for seeking the input video source, allowing you
to set the start time, end time, and duration.


Timecode Formats
-----------------------------------------------------------------------

Timecodes can be specified in the following formats:

 * Timestamp of hours/minutes/seconds in format ``HH:MM:SS`` or ``HH:MM:SS.nnn``
   (`00:01:40` indicates 1 minute and 40 seconds).  The `HH`, `MM`, and `SS` fields
   are all required; `.nnn` is optional.
 * Exact number of frames ``NNNN`` (`100` indicates frame 100)
 * Time in seconds ``SSSS.SSSs`` followed by lowercase `s` (`100s` indicates 100 seconds)


Command Options
-----------------------------------------------------------------------

The `time` command takes the following options:

 * ``-s``, ``--start TIMECODE``
    Time in video to begin detecting scenes. `TIMECODE` format
    is the same as other arguments.   [default: 0]
 * ``-d``, ``--duration TIMECODE``
    Maximum time in video to process. `TIMECODE` format
    is the same as other arguments. Mutually exclusive
    with `--end` / `-e`.
 * ``-e``, ``--end TIMECODE``
    Time in video to end detecting scenes. `TIMECODE`
    format is the same as other arguments. Mutually
    exclusive with `--duration` / `-d`.


Usage Examples
-----------------------------------------------------------------------

Using the `detect-content` detector, we start at 1 minute in and parse 30.5 seconds of `video.mp4`:

    ``scenedetect --input video.mp4 time --start 00:01:00 --duration 30.5s detect-content``

Same as above, but setting the end time instead of duration:

    ``scenedetect --input video.mp4 time --start 00:01:00 --end 00:01:30.500 detect-content``

Process the first 1000 frames only:

    ``scenedetect --input video.mp4 time --duration 1000 detect-content``


=======================================================================
``list-scenes``
=======================================================================

**The** ``list-scenes`` **command** is used to print out and write to a CSV file
a table of all scenes, their start/end timecodes, and frame numbers. The file also
includes the cut list, which is a list of timecodes of each scene boundary.



Command Options
-----------------------------------------------------------------------

The `list-scenes` command takes the following options:

 * ``-o``, ``--output DIR``
    Output directory to save videos to. Overrides global
    option `-o`/`--output` if set.
 * ``-f``, ``--filename NAME``
    Filename format to use for the scene list CSV file.
    You can use the `$VIDEO_NAME` macro in the file name.
    [default: `$VIDEO_NAME-Scenes.csv`]
 * ``-n``, ``--no-output-file``
    Disable writing scene list CSV file to disk.  If set,
    `-o`/`--output` and `-f`/`--filename` are ignored.
 * ``-q``, ``--quiet``
    Suppresses output of the table printed by the `list-scenes`
    command.


Usage Examples
-----------------------------------------------------------------------

Print table of detected scenes for `video.mp4` and save to CSV file `video-Scenes.csv`:

    ``scenedetect --input video.mp4 detect-content list-scenes``

Same as above, but *don't* create output file:

    ``scenedetect --input video.mp4 detect-content list-scenes -n``


=======================================================================
``save-images``
=======================================================================

**The** ``save-images`` **command** creates images for each detected scene.
It saves a set number of images for each detected scene, always including
the first and last frames.

Command Options
-----------------------------------------------------------------------

The `save-images` command takes the following options:

 * ``-o``, ``--output DIR``
    Output directory to save images to. Overrides global
    option -o/--output if set.
 * ``-f``, ``--filename NAME``
    Filename format, *without* extension, to use when
    saving image files. You can use the $VIDEO_NAME,
    $SCENE_NUMBER, and $IMAGE_NUMBER macros in the file
    name.  [default: $VIDEO_NAME-
    Scene-$SCENE_NUMBER-$IMAGE_NUMBER]
 * ``-n``, ``--num-images N``
    Number of images to generate. Will always include
    start/end frame, unless N = 1, in which case the image
    will be the frame at the mid-point in the scene.
 * ``-j``, ``--jpeg``
    Set output format to JPEG. [default]
 * ``-w``, ``--webp``
    Set output format to WebP.
 * ``-q``, ``--quality Q``
    JPEG/WebP encoding quality, from 0-100 (higher
    indicates better quality). For WebP, 100 indicates
    lossless. [default: JPEG: 95, WebP: 100]
 * ``-p``, ``--png``
    Set output format to PNG.
 * ``-c``, ``--compression C``
    PNG compression rate, from 0-9. Higher values produce
    smaller files but result in longer compression time.
    This setting does not affect image quality, only file
    size. [default: 3]


=======================================================================
``split-video``
=======================================================================

**The** ``split-video`` **command** splits the input video into individual clips,
by creating a new video clip for each detected scene.

Command Options
-----------------------------------------------------------------------

The `split-video` command takes the following options:

 * ``-o``, ``--output DIR``
    Output directory to save videos to. Overrides
    global option `-o`/`--output` if set.
 * ``-f``, ``--filename NAME``
    File name format, *without* extension, to use when saving image files.
    You can use the `$VIDEO_NAME` and `$SCENE_NUMBER`
    macros in the file name.  [default: `$VIDEO_NAME-
    Scene-$SCENE_NUMBER`]
 * ``-h``, ``--high-quality``
    Encode video with higher quality, overrides `-a`
    option if present. Equivalent to specifying
    --rate-factor 17 and --preset slow.
 * ``-a``, ``--override-args ARGS``
    Override codec arguments/options passed to FFmpeg
    when splitting and re-encoding scenes. Use double
    quotes (") around specified arguments. Must
    specify at least audio/video codec to use (e.g. `-a
    "-c:v [...] and -c:a [...]"`). [default: `"-c:v
    libx264 -preset veryfast -crf 22 -c:a copy"`]
 * ``-q``, ``--quiet``
    Suppresses output from external video splitting
    tool.
 * ``-c``, ``--copy``
    Copy instead of re-encode using mkvmerge instead
    of ffmpeg for splitting videos. All other
    arguments except -o/--output and -q/--quiet are
    ignored in this mode, and output files will be
    named $VIDEO_NAME-$SCENE_NUMBER.mkv. Significantly
    faster when splitting videos, however, output
    videos sometimes may not be split exactly,
    especially if the scenes are very short in length,
    or the input video is heavily compressed. This can
    lead to smaller scenes being merged with others,
    or scene boundaries being shifted in time - thus
    when using this option, the number of videos
    written may not match the number of scenes that
    was detected.
 * ``-crf``, ``--rate-factor RATE``
    Video encoding quality (x264 constant rate
    factor), from 0-100, where lower values represent
    better quality, with 0 indicating lossless.
    [default: 22, if `-hq`/`--high-quality` is set: 17]
 * ``-p``, ``--preset LEVEL``
    Video compression quality preset (x264 preset).
    Can be one of: ultrafast, superfast, veryfast,
    faster, fast, medium, slow, slower, and veryslow.
    Faster modes take less time to run, but the output
    files may be larger. [default: veryfast, if
    `-hq`/`--high-quality` is set: slow]



=======================================================================
``export-html``
=======================================================================

**The** ``export-html`` **command** generates an HTML file containing
all detected scenes in tabular format, including thumbnails by default.
This requires the ``save-images`` command to also be specified.
If images are not required, specify the `--no-images` option.

Command Options
-----------------------------------------------------------------------

The `export-html` command takes the following options:

 * ``-o``, ``--output DIR``
    Output directory to save videos to. Overrides
    global option `-o`/`--output` if set.
 * ``-f``, ``--filename NAME``
    Filename format to use for the scene list HTML
    file. You can use the $VIDEO_NAME macro in the
    file name.  [default: $VIDEO_NAME-Scenes.html]
 * ``--no-images``
    Export the scene list including or excluding the
    saved images.
 * ``-w``, ``--image-width pixels``
    Width in pixels of the images in the resulting
    HTML table.
 * ``-h``, ``--image-height pixels``
    Height in pixels of the images in the resulting
    HTML table.

