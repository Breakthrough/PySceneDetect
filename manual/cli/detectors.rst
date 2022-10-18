
.. _cli-detectors:

***********************************************************************
Detectors
***********************************************************************

There are currently four implemented scene detection algorithms, threshold
based detection (``detect-threshold``), content-aware detection
(``detect-content``), adaptive content-aware detection (``detect-adaptive``), 
and perceptual hashing based detection (``detect-hash``). Each detector can be 
selected by adding the respective `detect-` command, and any relevant options, 
after setting the main ``scenedetect`` command global options.  In general, 
commands should follow the form:

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

Examples:

    ``detect-content``

    ``detect-content --threshold 27.5``


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


=======================================================================
``detect-threshold``
=======================================================================

Perform threshold detection algorithm on input video.

Detects fades in/out based on average frame pixel value compared against
`-t`/`--threshold`.

Examples:

  ``detect-threshold``

  ``detect-threshold --threshold 15``

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


=======================================================================
``detect-adaptive``
=======================================================================

Perform adaptive detection algorithm on input video.

Two-pass algorithm that first calculates frame scores with `detect-content`,
and then applies a rolling average when processing the result. This can help
mitigate false detections in situations such as camera movement.

Examples:

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
``detect-hash``
=======================================================================

Perform detection using a perceptual hashing algorithm on input video.

When processing each frame, the frame is converted into a hash and this is 
compared to the previously analyzed frame. If the difference between these two 
hashes exceeds the value set for `-t`/`--threshold`, then a scene change is 
triggered.

This detector is only available when using the OpenCV backend.

The hashing algorithm used is based on the implementation of `phash <https://github.com/JohannesBuchner/imagehash>`_. 
The basic steps of the hashing algorithm are detailed below:

1. The image is first converted to grayscale (meaning this detector is not 
sensitive to color transitions). 
2. The resulting grayscale image is then scaled down in size to a square image 
with the length of each side equal to `-s`/`--size` \* `-f`/`--freq_factor`.
3. The discrete cosine transform (DCT) of the resized image is calculated.
4. Only the low frequency information from the DCT is retained. This is 
accomplished by discarding all but the upper left values of the resulting DCT 
matrix. The size of the resulting submatrix is set as a square with the length 
of each side determined by `-s`/`--size`.
5. The median of the retained DCT information is determined.
6. The hash is calculated by converting the retained DCT matrix into a binary 
array by comparing each element to the median. The resulting binary values are 
True if the value is greater than the median and False if it is less than or 
equal to the median.

The metric used for scene detection is the difference between the hashes of 
subsequent frames. This difference is calculated using the Hamming distance 
between two hashes. This is defined as the number of elements that differ 
between two hashes. This metric is recorded in the statsfile as `hash_dist` if 
a statsfile is specified.

Examples:

    ``detect-hash``

    ``detect-hash --threshold 80``

Detector Options
-----------------------------------------------------------------------

  -t, --threshold VAL           Threshold value (float) that the calculated
                                frame score must exceed to trigger a new scene
                                (see frame metric hash_dist in stats file). 
                                [default: 100.0]

  -s, --size VAL                Hash size (int) that is used for the detector. 
                                Larger values can help increase sensitivity to 
                                small changes, but can increase computation 
                                time. [default: 16]

  -f, --freq_factor VAL         Frequency factor (int) used to determing how 
                                much high frequency data is discarded in the 
                                hashing algorithm. For example a value of 4 
                                corresponds to keeping only 1/4 of the 
                                frequency information of the image (a value of 
                                2 would be 1/2 of the frequency information, 
                                etc.). Smaller values make the detector more 
                                sensitive to smaller sized features in the 
                                frame, but can increase computation time. 
                                [default: 2]

  -m, --min-scene-len TIMECODE  Minimum length of any scene. Overrides global
                                min-scene-len (-m) setting. TIMECODE can be
                                specified as exact number of frames, a time in
                                seconds followed by s, or a timecode in the
                                format HH:MM:SS or HH:MM:SS.nnn.
