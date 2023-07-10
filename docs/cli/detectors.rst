
.. _cli-detectors:

***********************************************************************
Detectors
***********************************************************************

There are three scene detection algorithms: threshold based detection (``detect-threshold``), content-aware detection (``detect-content``), and adaptive detection (``detect-adaptive``).

In general, use ``detect-adaptive`` or ``detect-content`` for fast cuts, and ``detect-threshold`` for detecting fade in/out transitions.


``detect-adaptive``
========================================================================

Perform adaptive detection algorithm on input video.

Two-pass algorithm that first calculates frame scores with ``detect-content``, and then applies a rolling average when processing the result. This can help mitigate false detections in situations such as camera movement.

Examples
------------------------------------------------------------------------

    ``scenedetect -i video.mp4 detect-adaptive``

    ``scenedetect -i video.mp4 detect-adaptive --threshold 3.2``

Options
------------------------------------------------------------------------

.. option:: --threshold VAL, -t VAL

  Threshold value (float) that the calculated frame score must exceed to trigger a new scene (see frame metric adaptive_ratio in stats file). [default: ``3.0``]

.. option:: --min-content-val VAL, -c VAL

  Minimum threshold (float) that the content_val must exceed in order to register as a new cene. This is calculated the same way that ``detect-content`` calculates frame score. [default: ``15.0``]

.. option:: --min-delta-hsv VAL, -d VAL

  [DEPRECATED] Use -c/--min-content-val instead. [default: ``15.0``]

.. option:: --frame-window VAL, -f VAL

  Size of window (number of frames) before and after each frame to average together in order to detect deviations from the mean. [default: ``2``]

.. option:: --weights, -w

  Weights of the 4 components used to calculate content_val in the form (delta_hue, delta_sat, delta_lum, delta_edges). [default: ``1.000, 1.000, 1.000, 0.000``]

.. option:: --luma-only, -l

  Only consider luma (brightness) channel. Useful for greyscale videos. Equivalent to setting -w/--weights to 0, 0, 1, 0.

.. option:: --kernel-size N, -k N

  Size of kernel for expanding detected edges. Must be odd integer greater than or equal to 3. If unset, kernel size is estimated using video resolution. [default: ``auto``]

.. option:: --min-scene-len TIMECODE, -m TIMECODE

  Minimum length of any scene. Overrides global min-scene-len (-m) setting. TIMECODE can be specified as exact number of frames, a time in seconds followed by s, or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.


``detect-content``
========================================================================

Perform content detection algorithm on input video.

When processing each frame, a score (from 0 to 255.0) is calculated representing the difference in content from the previous frame (higher = more difference). A change in scene is triggered when this value exceeds the value set for ``-t``/``--threshold``. This value is the *content_val* column in a statsfile.

Frame scores are calculated from several components, which are used to generate a final weighted value with ``-w``/``--weights``. These are also recorded in the statsfile if set. Currently there are four components:

 - *delta_hue*: Difference between pixel hue values of adjacent frames.

 - *delta_sat*: Difference between pixel saturation values of adjacent frames.

 - *delta_lum*: Difference between pixel luma (brightness) values of adjacent frames.

 - *delta_edges*: Difference between calculated edges of adjacent frames. Typically larger than other components, so threshold may need to be increased to compensate.

Weights are set as a set of 4 numbers in the form (*delta_hue*, *delta_sat*, *delta_lum*, *delta_edges*). For example, ``-w 1.0 0.5 1.0 0.2 -t 32`` is a good starting point to use with edge detection.

Edge detection is not enabled by default. Current default parameters are ``-w 1.0 1.0 1.0 0.0 -t 27``. The final weighted sum is normalized based on the weight of the components, so they do not need to equal 100%.

Examples
------------------------------------------------------------------------

    ``scenedetect -i video.mp4 detect-content``

    ``scenedetect -i video.mp4 detect-content --threshold 27.5``

Options
------------------------------------------------------------------------

.. option:: --threshold VAL, -t VAL

  Threshold value that the content_val frame metric must exceed to trigger a new scene. Refers to frame metric content_val in stats file. [default: ``27.0``]

.. option:: --weights, -w

  Weights of the 4 components used to calculate content_val in the form (delta_hue, delta_sat, delta_lum, delta_edges). [default: ``1.000, 1.000, 1.000, 0.000``]

.. option:: --luma-only, -l

  Only consider luma (brightness) channel. Useful for greyscale videos. Equivalent to setting -w/--weights to 0, 0, 1, 0.

.. option:: --kernel-size N, -k N

  Size of kernel for expanding detected edges. Must be odd integer greater than or equal to 3. If unset, kernel size is estimated using video resolution. [default: ``auto``]

.. option:: --min-scene-len TIMECODE, -m TIMECODE

  Minimum length of any scene. Overrides global min-scene-len (-m) setting. TIMECODE can be specified as exact number of frames, a time in seconds followed by s, or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.


``detect-threshold``
========================================================================

Perform threshold detection algorithm on input video.

Detects fades in/out based on average frame pixel value compared against ``-t``/``--threshold``.

Examples
------------------------------------------------------------------------

    ``scenedetect -i video.mp4 detect-threshold``

    ``scenedetect -i video.mp4 detect-threshold --threshold 15``

Options
------------------------------------------------------------------------

.. option:: --threshold VAL, -t VAL

  Threshold value (integer) that the delta_rgb frame metric must exceed to trigger a new scene. Refers to frame metric delta_rgb in stats file. [default: ``12.0``]

.. option:: --fade-bias PERCENT, -f PERCENT

  Percent (%) from -100 to 100 of timecode skew for where cuts should be placed. -100 indicates the start frame, +100 indicates the end frame, and 0 is the middle of both. [default: ``0``]

.. option:: --add-last-scene, -l

  If set, if the video ends on a fade-out, a final scene will be generated from the last fade-out position to the end of the video. [default: ``True``]

.. option:: --min-scene-len TIMECODE, -m TIMECODE

  Minimum length of any scene. Overrides global min-scene-len (-m) setting. TIMECODE can be specified as exact number of frames, a time in seconds followed by s, or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.
