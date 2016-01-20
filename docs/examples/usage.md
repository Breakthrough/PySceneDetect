
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

Below is a visual example of the parameters used in threshold mode (click for full-view):

![parameters in threshold mode](img/params.png)

## Example

## Second Example


