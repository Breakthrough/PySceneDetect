
# Getting Started

## Usage (Command Line)

Show help information and summary of command-line arguments:

```rst
scenedetect --help
```

Perform content-aware scene detection on a video `my_video.mp4`:

```rst
scenedetect -i my_video.mp4 -d content -t 30
```

In order to effectively use PySceneDetect, you should become familiar with the basic command line options (especially the detection method `-d` / `--detector` and threshold value `-t` / `--threshold`).  Descriptions for all command-line arguments can be obtained by running PySceneDetect with the `-h` / `--help` flag.


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


## Saving Images from Start/End of Scenes

PySceneDetect can automatically save the beginning and ending frame of each detected scene by using the `-si` (`--save-images`) flag.  If set, the first and last frames of each scene will be saved in the current working directory, using the filename of the input video.

Files marked `IN` represent the starting frame of the scene, and those marked `OUT` represent the last frame (e.g. `testvideo.mp4.Scene-4-OUT.jpg`).  Note that frames are only saved on detected scene boundaries, thus there will be no `IN` frame for the first scene, and likewise, there will be no `OUT` frame for the last scene.

