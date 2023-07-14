
.. _cli-detectors:

***********************************************************************
Detectors
***********************************************************************

There are three scene detection algorithms: threshold based detection (``detect-threshold``), content-aware detection (``detect-content``), and adaptive detection (``detect-adaptive``).

In general, use ``detect-adaptive`` or ``detect-content`` for fast cuts, and ``detect-threshold`` for detecting fade in/out transitions.

.. program:: scenedetect detect-adaptive

``detect-adaptive``
========================================================================

Perform adaptive detection algorithm on input video.

Two-pass algorithm that first calculates frame scores with :program:`detect-content <scenedetect detect-content>`, and then applies a rolling average when processing the result. This can help mitigate false detections in situations such as camera movement.

Examples
------------------------------------------------------------------------

    ``scenedetect -i video.mp4 detect-adaptive``

    ``scenedetect -i video.mp4 detect-adaptive --threshold 3.2``

Options
------------------------------------------------------------------------

.. option:: -t VAL, --threshold VAL

  Threshold (float) that frame score must exceed to trigger a cut. Refers to "adaptive_ratio" in stats file.

  Default: ``3.0``

.. option:: -c VAL, --min-content-val VAL

  Minimum threshold (float) that "content_val" must exceed to trigger a cut.

  Default: ``15.0``

.. option:: -d VAL, --min-delta-hsv VAL

  [DEPRECATED] Use :option:`-c/--min-content-val <-c>` instead.

  Default: ``15.0``

.. option:: -f VAL, --frame-window VAL

  Size of window to detect deviations from mean. Represents how many frames before/after the current one to use for mean.

  Default: ``2``

.. option:: -w, --weights

  Weights of 4 components ("delta_hue", "delta_sat", "delta_lum", "delta_edges") used to calculate "content_val".

  Default: ``1.000, 1.000, 1.000, 0.000``

.. option:: -l, --luma-only

  Only use luma (brightness) channel. Useful for greyscale videos. Equivalent to "--weights 0 0 1 0".

.. option:: -k N, --kernel-size N

  Size of kernel for expanding detected edges. Must be odd number >= 3. If unset, size is estimated using video resolution.

  Default: ``auto``

.. option:: -m TIMECODE, --min-scene-len TIMECODE

  Minimum length of any scene. Overrides global option :option:`-m/--min-scene-len <scenedetect -m>`. TIMECODE can be specified in frames (:option:`-m=100 <-m>`), in seconds with `s` suffix (:option:`-m=3.5s <-m>`), or timecode (:option:`-m=00:01:52.778 <-m>`).


.. program:: scenedetect detect-content

``detect-content``
========================================================================

Perform content detection algorithm on input video.

For each frame, a score from 0 to 255.0 is calculated which represents the difference in content between the current and previous frame (higher = more different). A cut is generated when a frame score exceeds :option:`-t/--threshold <-t>`. Frame scores are saved under the "content_val" column in a statsfile.

Scores are calculated from several components which are also recorded in the statsfile:

 - *delta_hue*: Difference between pixel hue values of adjacent frames.

 - *delta_sat*: Difference between pixel saturation values of adjacent frames.

 - *delta_lum*: Difference between pixel luma (brightness) values of adjacent frames.

 - *delta_edges*: Difference between calculated edges of adjacent frames. Typically larger than other components, so threshold may need to be increased to compensate.

Once calculated, these components are multiplied by the specified :option:`-w/--weights <-w>` to calculate the final frame score ("content_val").  Weights are set as a set of 4 numbers in the form (*delta_hue*, *delta_sat*, *delta_lum*, *delta_edges*). For example, "--weights 1.0 0.5 1.0 0.2 --threshold 32" is a good starting point for trying edge detection. The final sum is normalized by the weight of all components, so they need not equal 100%. Edge detection is disabled by default to improve performance.

Examples
------------------------------------------------------------------------

    ``scenedetect -i video.mp4 detect-content``

    ``scenedetect -i video.mp4 detect-content --threshold 27.5``

Options
------------------------------------------------------------------------

.. option:: -t VAL, --threshold VAL

  Threshold (float) that frame score must exceed to trigger a cut. Refers to "content_val" in stats file.

  Default: ``27.0``

.. option:: -w HUE SAT LUM EDGE, --weights HUE SAT LUM EDGE

  Weights of 4 components used to calculate frame score from (delta_hue, delta_sat, delta_lum, delta_edges).

  Default: ``1.000, 1.000, 1.000, 0.000``

.. option:: -l, --luma-only

  Only use luma (brightness) channel. Useful for greyscale videos. Equivalent to setting "-w 0 0 1 0".

.. option:: -k N, --kernel-size N

  Size of kernel for expanding detected edges. Must be odd integer greater than or equal to 3. If unset, kernel size is estimated using video resolution.

  Default: ``auto``

.. option:: -m TIMECODE, --min-scene-len TIMECODE

  Minimum length of any scene. Overrides global option :option:`-m/--min-scene-len <scenedetect -m>`. TIMECODE can be specified in frames (:option:`-m=100 <-m>`), in seconds with `s` suffix (:option:`-m=3.5s <-m>`), or timecode (:option:`-m=00:01:52.778 <-m>`).


.. program:: scenedetect detect-threshold

``detect-threshold``
========================================================================

Perform threshold detection algorithm on input video.

Detects fade-in and fade-out events using average pixel values. Resulting cuts are placed between adjacent fade-out and fade-in events.

Examples
------------------------------------------------------------------------

    ``scenedetect -i video.mp4 detect-threshold``

    ``scenedetect -i video.mp4 detect-threshold --threshold 15``

Options
------------------------------------------------------------------------

.. option:: -t VAL, --threshold VAL

  Threshold (integer) that frame score must exceed to start a new scene. Refers to "delta_rgb" in stats file.

  Default: ``12.0``

.. option:: -f PERCENT, --fade-bias PERCENT

  Percent (%) from -100 to 100 of timecode skew of cut placement. -100 indicates the start frame, +100 indicates the end frame, and 0 is the middle of both.

  Default: ``0``

.. option:: -l, --add-last-scene

  If set and video ends after a fade-out event, generate a final cut at the last fade-out position.

  Default: ``True``

.. option:: -m TIMECODE, --min-scene-len TIMECODE

  Minimum length of any scene. Overrides global option :option:`-m/--min-scene-len <scenedetect -m>`. TIMECODE can be specified in frames (:option:`-m=100 <-m>`), in seconds with `s` suffix (:option:`-m=3.5s <-m>`), or timecode (:option:`-m=00:01:52.778 <-m>`).
