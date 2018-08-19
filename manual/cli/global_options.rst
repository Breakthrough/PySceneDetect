
***********************************************************************
 ``scenedetect`` Program Options
***********************************************************************

=======================================================================
Overview
=======================================================================

The options in this section represent the "global" arguments for the
main ``scenedetect`` command. The most commonly used options the
input video(s)
(`--input video.mp4`), the output directory (`--output video_out`), and
the stats file to use (`--stats video.stats.csv`)

.. attention::
   Any options on this page (global options) **must** be set before specifying
   *any* commands.  Your commands must follow the form (where square brackets
   denote things that may be optional):

       ``scenedetect (global options) (command-A [command-A options]) (...)``
   
   This is because once a command is specified, all options/arguments afterwards
   will be parsed assuming they belong to *that* command (unless the argument is
   another command, in which case the command is applied, and the process
   repeats).


=======================================================================
Reference
=======================================================================


-----------------------------------------------------------------------
 ``--input``: Input Video(s)Scene Detectors
-----------------------------------------------------------------------


-----------------------------------------------------------------------
Example
-----------------------------------------------------------------------

