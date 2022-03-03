
.. _cli-detectors:

***********************************************************************
Detectors
***********************************************************************

There are currently two implemented scene detection algorithms, threshold
based detection (``detect-threshold``), and content-aware detection
(``detect-content``).  Each detector can be selected by adding the
respective `detect-` command, and any relevant options, after setting
the main ``scenedetect`` command global options.  In general, commands
should follow the form:

    ``scenedetect [global options] [detector] [commands]``

For example, to use the `detect-content` detector on a file `video.mp4`,
writing a stats file to file `video.stats.csv`, and printing a list of
detected scenes to the terminal:

    ``scenedetect -i video.mp4 -s video.stats.csv detect-content list-scenes -n``

Several more command line interface examples are shown in the following section.

=======================================================================
``detect-content``
=======================================================================

Perform content detection algorithm on input video.


Detector Options
-----------------------------------------------------------------------

The ``detect-content`` detector takes the following options:

  -t, --threshold VAL           Threshold value (float) that the content_val frame
                                metric must exceed to trigger a new scene.
                                Refers to frame metric content_val in stats
                                file.  [default: 30.0]



Usage Examples
-----------------------------------------------------------------------

  ``detect-content``

  ``detect-content --threshold 27.5``


=======================================================================
``detect-threshold``
=======================================================================

  Perform threshold detection algorithm on input video.

Detector Options
-----------------------------------------------------------------------

The ``detect-threshold`` detector takes the following options:

  -t, --threshold VAL           Threshold value (integer) that the delta_rgb
                                frame metric must exceed to trigger a new scene.
                                Refers to frame metric delta_rgb in stats file.
                                [default: 12]
  -f, --fade-bias PERCENT       Percent (%) from -100 to 100 of timecode skew
                                for where cuts should be placed. -100 indicates
                                the start frame, +100 indicates the end frame,
                                and 0 is the middle of both.  [default: 0]
  -l, --add-last-scene          If set, if the video ends on a fade-out, an
                                additional scene will be generated for the last
                                fade out position.
  -p, --min-percent PERCENT     Percent (%) from 0 to 100 of amount of pixels
                                that must meet the threshold value in orderto
                                trigger a scene change.  [default: 95]
  -b, --block-size N            Number of rows in image to sum per iteration
                                (can be tuned for performance in some cases).
                                [default: 8]


Usage Examples
-----------------------------------------------------------------------

  ``detect-threshold``

  ``detect-threshold --threshold 15``

