
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

  -t, --threshold VAL           Threshold value that the content_val frame
                                metric must exceed to trigger a new scene.
                                Refers to frame metric content_val in stats
                                file. [default: 27.0]

  -l, --luma-only               Only consider luma/brightness channel (useful
                                for greyscale videos).

  -m, --min-scene-len TIMECODE  Minimum length of any scene. Overrides global
                                min-scene-len (-m) setting. TIMECODE can be
                                specified as exact number of frames, a time in
                                seconds followed by s, or a timecode in the
                                format HH:MM:SS or HH:MM:SS.nnn. [setting: 40]

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

  -t, --threshold VAL           Threshold value (integer) that the delta_rgb
                                frame metric must exceed to trigger a new
                                scene. Refers to frame metric delta_rgb in
                                stats file. [default: 12.0]

  -f, --fade-bias PERCENT       Percent (%) from -100 to 100 of timecode skew
                                for where cuts should be placed. -100
                                indicates the start frame, +100 indicates the
                                end frame, and 0 is the middle of both.
                                [default: 0]

  -l, --add-last-scene          If set, if the video ends on a fade-out, a
                                final scene will be generated from the last
                                fade-out position to the end of the video.
                                [default: True]

  -m, --min-scene-len TIMECODE  Minimum length of any scene. Overrides global
                                min-scene-len (-m) setting. TIMECODE can be
                                specified as exact number of frames, a time in
                                seconds followed by s, or a timecode in the
                                format HH:MM:SS or HH:MM:SS.nnn.

Usage Examples
-----------------------------------------------------------------------

  ``detect-threshold``

  ``detect-threshold --threshold 15``


=======================================================================
``detect-adaptive``
=======================================================================

Perform adaptive detection algorithm on input video.

Detector Options
-----------------------------------------------------------------------

  -t, --threshold VAL           Threshold value (float) that the calculated
                                frame score must exceed to trigger a new scene
                                (see frame metric adaptive_ratio in stats
                                file). [default: 3.0]

  -d, --min-delta-hsv VAL       Minimum threshold (float) that the content_val
                                must exceed in order to register as a new
                                scene. This is calculated the same way that
                                `detect-content` calculates frame score.
                                [default: 15.0]

  -w, --frame-window VAL        Size of window (number of frames) before and
                                after each frame to average together in order
                                to detect deviations from the mean. [default:
                                2]

  -l, --luma-only               Only consider luma/brightness channel (useful
                                for greyscale videos).

  -m, --min-scene-len TIMECODE  Minimum length of any scene. Overrides global
                                min-scene-len (-m) setting. TIMECODE can be
                                specified as exact number of frames, a time in
                                seconds followed by s, or a timecode in the
                                format HH:MM:SS or HH:MM:SS.nnn.


Usage Examples
-----------------------------------------------------------------------

  ``detect-adaptive``

  ``detect-adaptive --threshold 3.2 --min-delta-hsv 16``
