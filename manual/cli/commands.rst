
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


``help``
=======================================================================

Print Command Help/Usage Information


``about``
=======================================================================

Print License And Copyright Information


``version``
=======================================================================

Print PySceneDetect Version Number


``time``
=======================================================================

Set Input Video Start (Seek) And End Time (Duration)


``list-scenes``
=======================================================================

Write Scenes To CSV (Timecode Table)



``save-images``
=======================================================================

Save Images For Each Scene


``split-video``
=======================================================================

Split Input Video Into Scenes
