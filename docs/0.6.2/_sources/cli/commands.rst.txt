
.. _cli-commands:

***********************************************************************
Commands
***********************************************************************

The following commands are available when using ``scenedetect``. Several commands can be combined together (the order does not matter) to control various input/output options.

The following is a list of the available commands along with a brief description of the command's function and an example.


Help/information commands:

 - :ref:`help <info Commands>` - Prints help and usage information for commands
    ``help`` or ``help split-video`` or ``help all``
 - :ref:`about <info Commands>` - Prints license and copyright information about PySceneDetect
 - :ref:`version <info Commands>` - Print PySceneDetect version Number

Input/output commands (applies to input videos and detected scenes):

 - :ref:`time <time Command>` - Set start time/end time/duration of input video
    ``time --start 00:01:00 --end 00:02:00``

 - :ref:`list-scenes <list-scenes Command>` - Save start/end/duration of each scene in .CSV format
    ``list-scenes`` or ``list-scenes --no-output-file``

 - :ref:`save-images <save-images Command>` - Extract frames from every detected scene as images
    ``save-images`` or ``save-images --num-images 5``

 - :ref:`split-video <split-video Command>` - Automatically split video with ffmpeg/mkvmerge
    ``split-video`` or ``split-video --copy``

 - :ref:`export-html <export-html Command>` - Export scene list to HTML file
    ``export-html`` or ``export-html --no-images``

.. note:: When using multiple commands, make sure to not specify the same command twice. The order of commands does not matter, but each command should only be specified once.


.. _info Commands:

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

``help`` command (show help for global options/command):

    ``scenedetect help``

    ``scenedetect help detect-adaptive``

    ``scenedetect help all``

``about`` command (show license/copyright info):

    ``scenedetect about``

``version`` command (show software or system version info):

    ``scenedetect version``

    ``scenedetect version --all``

System Dependencies
-----------------------------------------------------------------------

You can use the ``version`` command with  ``-a`` / ``--all`` to check installed software dependencies:

    ``scenedetect version --all``

Please include this information when submitting bug reports.


.. _time Command:

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

  -s, --start TIMECODE     Time in video to begin detecting scenes. TIMECODE
                           can be specified as exact number of frames (-s 100
                           to start at frame 100), time in seconds followed by
                           s (-s 100s to start at 100 seconds), or a timecode
                           in the format HH:MM:SS or HH:MM:SS.nnn (-s 00:01:40
                           to start at 1m40s).

  -d, --duration TIMECODE  Maximum time in video to process. TIMECODE format
                           is the same as other arguments. Mutually exclusive
                           with --end / -e.

  -e, --end TIMECODE       Time in video to end detecting scenes. TIMECODE
                           format is the same as other arguments. Mutually
                           exclusive with --duration / -d.

Usage Examples
-----------------------------------------------------------------------

Using the `detect-content` detector, we start at 1 minute in and parse 30.5 seconds of `video.mp4`:

    ``scenedetect --input video.mp4 time --start 00:01:00 --duration 30.5s detect-content``

Same as above, but setting the end time instead of duration:

    ``scenedetect --input video.mp4 time --start 00:01:00 --end 00:01:30.500 detect-content``

Process the first 1000 frames only:

    ``scenedetect --input video.mp4 time --duration 1000 detect-content``


.. _list-scenes Command:

=======================================================================
``list-scenes``
=======================================================================

**The** ``list-scenes`` **command** is used to print out and write to a CSV file
a table of all scenes, their start/end timecodes, and frame numbers. The file also
includes the cut list, which is a list of timecodes of each scene boundary.

Command Options
-----------------------------------------------------------------------

  -o, --output DIR      Output directory to save videos to. Overrides global
                        option -o/--output if set.

  -f, --filename NAME   Filename format to use for the scene list CSV file.
                        You can use the $VIDEO_NAME macro in the file name.
                        Note that you may have to wrap the name using single
                        quotes. [default: $VIDEO_NAME-Scenes.csv]

  -n, --no-output-file  Disable writing scene list CSV file to disk.  If set,
                        -o/--output and -f/--filename are ignored.

  -q, --quiet           Suppresses output of the table printed by the list-
                        scenes command.

  -s, --skip-cuts       Skips outputting the cut list as the first row in the
                        CSV file. Set this option if compliance with RFC
                        4180 is required.

Usage Examples
-----------------------------------------------------------------------

Print table of detected scenes for `video.mp4` and save to CSV file `video-Scenes.csv`:

    ``scenedetect --input video.mp4 detect-content list-scenes``

Same as above, but *don't* create output file:

    ``scenedetect --input video.mp4 detect-content list-scenes -n``


.. _save-images Command:

=======================================================================
``save-images``
=======================================================================

**The** ``save-images`` **command** creates images for each detected scene.
It saves a set number of images for each detected scene, always including
the first and last frames.

Command Options
-----------------------------------------------------------------------

  -o, --output DIR      Output directory to save images to. Overrides global
                        option -o/--output if set.

  -f, --filename NAME   Filename format, *without* extension, to use when
                        saving image files. You can use the $VIDEO_NAME,
                        $SCENE_NUMBER, $IMAGE_NUMBER, and $FRAME_NUMBER macros
                        in the file name. Note that depending on the specifics
                        of your computing environment, non-standard characters
                        in image filenames may not be preserved due to an OpenCV
                        issue. Also note that you may have to wrap the format in
                        single quotes. [default: $VIDEO_NAME-Scene-
                        $SCENE_NUMBER-$IMAGE_NUMBER]

  -n, --num-images N    Number of images to generate. Will always include
                        start/end frame, unless N = 1, in which case the image
                        will be the frame at the mid-point in the scene.
                        [default: 3]

  -j, --jpeg            Set output format to JPEG (default).
  -w, --webp            Set output format to WebP
  -q, --quality Q       JPEG/WebP encoding quality, from 0-100 (higher
                        indicates better quality). For WebP, 100 indicates
                        lossless. [default: JPEG: 95, WebP: 100]

  -p, --png             Set output format to PNG.
  -c, --compression C   PNG compression rate, from 0-9. Higher values produce
                        smaller files but result in longer compression time.
                        This setting does not affect image quality, only file
                        size. [default: 3]

  -m, --frame-margin N  Number of frames to ignore at the beginning and end of
                        scenes when saving images. [default: 3]

  -s, --scale S         Optional factor by which saved images are rescaled. A
                        scaling factor of 1 would not result in rescaling. A
                        value <1 results in a smaller saved image, while a
                        value >1 results in an image larger than the original.
                        This value is ignored if either the height, -h, or
                        width, -w, values are specified.

  -H, --height H        Optional value for the height of the saved images.
                        Specifying both the height and width, -W, will resize
                        images to an exact size, regardless of aspect ratio.
                        Specifying only height will rescale the image to that
                        number of pixels in height while preserving the aspect
                        ratio.

  -W, --width W         Optional value for the width of the saved images.
                        Specifying both the width and height, -H, will resize
                        images to an exact size, regardless of aspect ratio.
                        Specifying only width will rescale the image to that
                        number of pixels wide while preserving the aspect
                        ratio.


.. _split-video Command:

=======================================================================
``split-video``
=======================================================================

**The** ``split-video`` **command** splits the input video into individual clips,
by creating a new video clip for each detected scene.

Command Options
-----------------------------------------------------------------------

  -o, --output DIR          Output directory to save videos to. Overrides
                            global option -o/--output if set.

  -f, --filename NAME       File name format to use when saving videos (with
                            or without extension). You can use the $VIDEO_NAME 
                            or $SCENE_NUMBER macros. Additional macros that are 
                            available only with the ffmpeg backend include 
                            $START_TIME, $END_TIME, $START_FRAME, and 
                            $END_FRAME. A potential formatting pitfall is that 
                            macros cannot be followed by an underscore character
                             in order to be replaced correctly. For example, the
                             value Scene-$SCENE_NUMBER-Frame-$FRAME_NUMBER will 
                            properly replace both macro values. However, using 
                            Scene_$SCENE_NUMBER_Frame_$FRAME_NUMBER will not. 
                            Note that you may have to wrap the format in single 
                            quotes to avoid variable expansion. [default: 
                            $VIDEO_NAME-Scene-$SCENE_NUMBER]

  -q, --quiet               Hides any output from the external video splitting
                            tool. [setting: off]

  -c, --copy                Copy instead of re-encode. Much faster, but less
                            precise. Equivalent to specifying -a "-map 0 -c:v
                            copy -c:a copy ".

  -hq, --high-quality       Encode video with higher quality, overrides -f
                            option if present. Equivalent to specifying
                            --rate-factor 17 and --preset slow.

  -crf, --rate-factor RATE  Video encoding quality (x264 constant rate
                            factor), from 0-100, where lower values represent
                            better quality, with 0 indicating lossless.
                            [setting: 20]

  -p, --preset LEVEL        Video compression quality preset (x264 preset).
                            Can be one of: ultrafast, superfast, veryfast,
                            faster, fast, medium, slow, slower, and veryslow.
                            Faster modes take less time to run, but the output
                            files may be larger. [default: veryfast]

  -a, --args ARGS           Override codec arguments/options passed to FFmpeg
                            when splitting and re-encoding scenes. Use double
                            quotes (") around specified arguments. Must
                            specify at least audio/video codec to use (e.g. -a
                            "-c:v [...] -c:a [...]"). [default: -map 0 -c:v
                            libx264 -preset veryfast -crf 22 -c:a aac]

  -m, --mkvmerge            Split the video using mkvmerge. Faster than re-
                            encoding, but less precise. The output will be
                            named $VIDEO_NAME-$SCENE_NUMBER.mkv. If set, all
                            options other than -f/--filename, -q/--quiet and
                            -o/--output will be ignored. Note that mkvmerge
                            automatically appends asuffix of "-$SCENE_NUMBER".


.. _export-html Command:

=======================================================================
``export-html``
=======================================================================

**The** ``export-html`` **command** generates an HTML file containing
all detected scenes in tabular format, including thumbnails by default.
This requires the ``save-images`` command to also be specified.
If images are not required, specify the `--no-images` option.

Command Options
-----------------------------------------------------------------------

  -f, --filename NAME        Filename format to use for the scene list HTML
                             file. You can use the $VIDEO_NAME macro in the
                             file name. Note that you may have to wrap the
                             format name using single quotes. [default:
                             $VIDEO_NAME-Scenes.html]

  --no-images                Export the scene list including or excluding the
                             saved images.

  -w, --image-width pixels   Width in pixels of the images in the resulting
                             HTML table.

  -h, --image-height pixels  Height in pixels of the images in the resulting
                             HTML table.
