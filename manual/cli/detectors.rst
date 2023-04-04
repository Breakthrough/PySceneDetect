
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

When processing each frame, a score (from 0 to 255.0) is calculated
representing the difference in content from the previous frame (higher =
more difference). A change in scene is triggered when this value exceeds the
value set for `-t`/`--threshold`. This value is the *content_val* column in
a statsfile.

Frame scores are calculated from several components, which are used to
generate a final weighted value with `-w`/`--weights`. These are also
recorded in the statsfile if set. Currently there are four components:

  - *delta_hue*: Difference between pixel hue values of adjacent frames.

  - *delta_sat*: Difference between pixel saturation values of adjacent
  frames.

  - *delta_lum*: Difference between pixel luma (brightness) values of
  adjacent frames.

  - *delta_edges*: Difference between calculated edges of adjacent frames.
  Typically larger than other components, so threshold may need to be
  increased to compensate.

Weights are set as a set of 4 numbers in the form (*delta_hue*, *delta_sat*,
*delta_lum*, *delta_edges*). For example, `-w 1.0 0.5 1.0 0.2 -t 32` is a
good starting point to use with edge detection.

Edge detection is not enabled by default. Current default parameters are `-w
1.0 1.0 1.0 0.0 -t 27`. The final weighted sum is normalized based on the
weight of the components, so they do not need to equal 100%.

Detector Options
-----------------------------------------------------------------------

  -t, --threshold VAL             Threshold value that the content_val frame
                                  metric must exceed to trigger a new scene.
                                  Refers to frame metric content_val in stats
                                  file. [default: 27.0]  [0.0<=x<=255.0]

  -w, --weights <FLOAT FLOAT FLOAT FLOAT>...
                                  Weights of the 4 components used to
                                  calculate content_val in the form
                                  (delta_hue, delta_sat, delta_lum,
                                  delta_edges). [default: 1.000, 1.000, 1.000,
                                  0.000]

  -l, --luma-only                 Only consider luma (brightness) channel.
                                  Useful for greyscale videos. Equivalent
                                  tosetting -w/--weights to 0, 0, 1, 0.

  -k, --kernel-size N             Size of kernel for expanding detected edges.
                                  Must be odd integer greater than or equal to
                                  3. If unset, kernel size is estimated using
                                  video resolution. [default: auto]

  -m, --min-scene-len TIMECODE    Minimum length of any scene. Overrides
                                  global min-scene-len (-m) setting. TIMECODE
                                  can be specified as exact number of frames,
                                  a time in seconds followed by s, or a
                                  timecode in the format HH:MM:SS or
                                  HH:MM:SS.nnn.

Examples
-----------------------------------------------------------------------

    ``detect-content``

    ``detect-content --threshold 27.5``


=======================================================================
``detect-threshold``
=======================================================================

Perform threshold detection algorithm on input video.

Detects fades in/out based on average frame pixel value compared against
`-t`/`--threshold`.

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

Two-pass algorithm that first calculates frame scores with `detect-content`,
and then applies a rolling average when processing the result. This can help
mitigate false detections in situations such as camera movement.

Detector Options
-----------------------------------------------------------------------

  -t, --threshold VAL             Threshold value (float) that the calculated
                                  frame score must exceed to trigger a new
                                  scene (see frame metric adaptive_ratio in
                                  stats file). [default: 3.0]
  -c, --min-content-val VAL       Minimum threshold (float) that the
                                  content_val must exceed in order to register
                                  as a new scene. This is calculated the same
                                  way that `detect-content` calculates frame
                                  score. [default: 15.0]
  -f, --frame-window VAL          Size of window (number of frames) before and
                                  after each frame to average together in
                                  order to detect deviations from the mean.
                                  [default: 2]
  -w, --weights <FLOAT FLOAT FLOAT FLOAT>...
                                  Weights of the 4 components used to
                                  calculate content_val in the form
                                  (delta_hue, delta_sat, delta_lum,
                                  delta_edges). [default: 1.000, 1.000, 1.000,
                                  0.000]
  -l, --luma-only                 Only consider luma (brightness) channel.
                                  Useful for greyscale videos. Equivalent
                                  tosetting -w/--weights to 0, 0, 1, 0.
  -k, --kernel-size N             Size of kernel for expanding detected edges.
                                  Must be odd integer greater than or equal to
                                  3. If unset, kernel size is estimated using
                                  video resolution. [default: auto]
  -m, --min-scene-len TIMECODE    Minimum length of any scene. Overrides
                                  global min-scene-len (-m) setting. TIMECODE
                                  can be specified as exact number of frames,
                                  a time in seconds followed by s, or a
                                  timecode in the format HH:MM:SS or
                                  HH:MM:SS.nnn.

Usage Examples
-----------------------------------------------------------------------

    ``detect-adaptive``

    ``detect-adaptive --threshold 3.2``


Detector Options
-----------------------------------------------------------------------

  -t, --threshold VAL           Threshold value (float) that the calculated
                                frame score must exceed to trigger a new scene
                                (see frame metric adaptive_ratio in stats
                                file). [default: 3.0]

  -d, --min-content-val VAL     Minimum threshold (float) that the content_val
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


=======================================================================
``detect-hist``
=======================================================================

Perform color histogram detection algorithm on input video.

This algorithm first separates the color channels of the video and then
quantizes each color image. The color channels are then bit-shifted and joined
together once again. A histogram is calculated for the resulting composite image
and if the element-wise difference between histograms of adjacent frames 
exceeds the threshold value, a new scene is triggered.

The input video for the ``detect-hist`` must be an 8-bit color video due to the
bit shifting calculations that are done.

Detector Options
-----------------------------------------------------------------------

  -t, --threshold VAL           Threshold value (float) that the calculated
                                histogram difference must exceed to trigger a
                                new scene (see frame metric hist_diff in stats
                                file). [default: 20000.0]

  -b, --bits VAL                The number of most significant bits to retain
                                when quantizing video frames. A higher value
                                retains more color information, but increases
                                computational complexity. Can be in the range
                                [1-8] since input video must be 8-bit color.
                                [default: 4]

  -m, --min-scene-len TIMECODE  Minimum length of any scene. Overrides global
                                min-scene-len (-m) setting. TIMECODE can be
                                specified as exact number of frames, a time in
                                seconds followed by s, or a timecode in the
                                format HH:MM:SS or HH:MM:SS.nnn.

Usage Examples
-----------------------------------------------------------------------

    ``detect-hist``

    ``detect-hist --threshold 25000.0``