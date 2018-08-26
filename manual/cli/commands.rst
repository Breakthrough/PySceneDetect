
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


.. note:: When using multiple commands, make sure to not
   specify the same command twice. The order of commands does
   not matter, but each command should only be specified once.




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

Start at 1 minute in and parse 30.5 seconds of video:

    ``scenedetect --input video.mp4 time --start 00:01:00 --duration 30.5s``

Same as above, but setting the end time instead of duration:

    ``scenedetect --input video.mp4 time --start 00:01:00 --end 00:01:30.500``

Process the first 1000 frames only:

    ``scenedetect --input video.mp4 time --duration 1000``




``list-scenes``
=======================================================================

**The** ``list-scenes`` **command** (Write Scenes To CSV [Timecode Table])




``save-images``
=======================================================================

**The** ``save-images`` **command** (Save Images For Each Scene)




``split-video``
=======================================================================

**The** ``split-video`` **command** (Split Input Video Into Scenes)

