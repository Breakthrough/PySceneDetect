
# Getting Started

This page outlines the most commonly used command-line options for using PySceneDetect.


## Usage (Command Line)

Show help information and summary of command-line arguments:

```rst
scenedetect --help
```

Perform content-aware scene detection on a video `my_video.mp4` ([example](usage-example.md)):

```rst
scenedetect -i my_video.mp4 -d content -t 30
```

In order to effectively use PySceneDetect, you should become familiar with the basic command line options described below - especially the scene detection method/algorithm (`-d` / `--detector`) and the threshold/sensitivity value (`-t` / `--threshold`).  These are described in the following section with respect to each detection method (`content` and `threshold`).  Note that descriptions for all command-line arguments, as well as their default values, can be obtained by running PySceneDetect with the `-h` / `--help` flag.


## Detection Methods

There are two main detection methods PySceneDetect uses: `threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `content` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  Each mode has slightly different parameters, and is described in detail below.

In general, use `threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `content` mode.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--statsfile` flag) in order to determine the correct paramters - specifically, the proper threshold value.


### Content-Aware Detection Mode

Unlike threshold mode, content-aware mode looks at the *difference* between each pair of adjacent frames, triggering a scene break when this difference exceeds the threshold value.  A good threshold value to try when using content-aware mode (`-d content`) is `30` (`-t 30`), for example:

```rst
scenedetect -i my_video.mp4 -d content -t 30
```

The optimal threshold can be determined by generating a statsfile (`-s`), opening it with a spreadsheet editor (e.g. Excel), and examining the `delta_hsv_avg` column.  This value should be very small between similar frames, and grow large when a big change in content is noticed (look at the values near frame numbers/times where you know a scene change occurs).  The threshold value should be set so that most scenes fall below the threshold value, and scenes where changes occur should *exceed* the threshold value (thus triggering a scene change).  


### Threshold-Based Detection Mode

Threshold-based mode is what most traditional scene detection programs use, which looks at the average intensity of the *current* frame, triggering a scene break when the intensity falls below the threshold (or crosses back upwards).  A good threshold value to try when using threshold mode (`-d threshold`) is `12` (`-t 12`), with a minimum percentage of at least 90% (`-m 0.9`).  Using values less than `8` may cause problems with some videos (especially those encoded at lower quality bitrates).

```rst
scenedetect -i my_video.mp4 -d threshold -t 12
```

The optimal threshold can be determined by generating a statsfile (`-s`), opening it with a spreadsheet editor (e.g. Excel), and examining the `avg_rgb` column.  These values represent the average intensity of the pixels for that particular frame (taken by averaging the R, G, and B values over the whole frame).  The threshold value should be set so that the average intensity of most frames in content scenes lie above the threshold value, and scenes where scene changes/breaks occur should fall *under* the threshold value (thus triggering a scene change).


## Seeking, Duration, and Setting Start/Stop Times

There are three command line options that control what portion of the video PySceneDetect processes - start time (`-st`), end time (`-et`), and duration (`-dt`).  Specifying both end time and duration is redundant, and in this case, duration overrides end time.  Timecodes can be given in three formats:  exact frame number (e.g. `12345`), number of seconds followed by `s` (e.g. `123s`, `123.45s`), or standard format (HH:MM:SS[.nnn], e.g. `12:34:56`, `12:34:56.789`).

For example, let's say we have a video shot at 30 FPS, and want to analyze only the segment from the 5 to the 6.5 minute mark in the video (we want to analyze the 90 seconds, or 2700 frames, between 00:05:00 and 00:06:30).  The following commands are all equivalent in this regard:


```rst
scenedetect -i my_video.mp4 -st 00:05:00 -et 00:06:30
```

```rst
scenedetect -i my_video.mp4 -st 300s -et 390s
```

```rst
scenedetect -i my_video.mp4 -st 300s -dt 90s
```

```rst
scenedetect -i my_video.mp4 -st 300s -dt 2700
```

```rst
scenedetect -i my_video.mp4 -st 9000 -et 99:99:99.999 -dt 2700
```

This demonstrates the different timecode formats, interchanging end time with duration and vice-versa, and precedence of setting duration over end time.


## Saving Image Previews of Detected Scenes

PySceneDetect can automatically save the beginning and ending frame of each detected scene by using the `-si` (`--save-images`) flag.  If set, the first and last frames of each scene will be saved in the current working directory, using the filename of the input video.

Files marked `IN` represent the starting frame of the scene, and those marked `OUT` represent the last frame (e.g. `testvideo.mp4.Scene-4-OUT.jpg`).  Note that frames are only saved on detected scene boundaries, thus there will be no `IN` frame for the first scene, and likewise, there will be no `OUT` frame for the last scene.


## Improving Processing Speed/Performance

Assuming the input video is of a high enough resolution, a significant performance gain can be achieved by sub-sampling (down-scaling) the input image by a specific integer factor (2x, 3x, 4x, 5x...).  This factor represents how many pixels are "skipped" in both the x- and y- directions, effectively down-scaling the image (using nearest-neighbor sampling) by the factor specified (the new resolution being `W/factor x H/factor` if the old resolution is `W x H`).

Another method that can be used to gain a performance boost is frame skipping.  This method, however, reduces frame-accurate scene cuts, so it should only be used with high FPS material (ideally > 60 FPS), at low values (try not to exceed a value of `1` or `2` if using `--frameskip`), in cases where this is acceptable.  For example, if we skip every other frame (e.g. using `--frameskip 1`), the processing speed should roughly double.  When frame skipping is enabled, skipped frames are cached in memory so a precise scene boundary can still be computed.

If set too large, enough frames may be skipped each time that the threshold is met during every iteration, continually triggering scene changes.  This is because frame skipping essentially raises the threshold between frames in the same scene (making them more likely to appear as *cuts*) while not affecting the threshold between frames of different scenes.  This makes the two harder to distinguish, and can cause additional false scene cuts to be detected.  While this can be compensated for by raising the threshold value, this increases the probability of missing a real/true scene cut.
