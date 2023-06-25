
# PySceneDetect Command-Line Usage

This page outlines the most commonly used command-line options for using PySceneDetect. Basic usage of PySceneDetect (`scenedetect`) is:

```rst
scenedetect [global options] [commands + command options]
```

You can also print the usage/help manual of PySceneDetect with the `help` command:

```rst
scenedetect help
```

<div class="important">
The complete PySceneDetect Command-Line Interface (CLI) Reference <span class="fa fa-book"> can be found in the <a href="http://scenedetect.com/projects/Manual/en/latest/" alt="Manual Link">PySceneDetect Manual</a>, located at <a href="http://scenedetect.com/projects/Manual/en/latest/" alt="Manual Link">scenedetect.com/projects/Manual/en/latest/</a>.
</div>


## Quick Example

Split the input video wherever a new scene is detected:

```rst
scenedetect -i video.mp4 detect-adaptive split-video
```

Print a table of detected scenes to the terminal, and save an image
at the start, middle, and end frame of each scene:

```rst
scenedetect -i video.mp4 detect-adaptive list-scenes -n save-images
```

Skip the first 10 seconds of the input video:

```rst
scenedetect -i video.mp4 time -s 10s detect-adaptive
```

There are many other options and commands.  To show a summary of available options/arguments, and a list of all commands:

```rst
scenedetect help
```

You can also type `help command` where `command` is a specific command (e.g. `list-scenes`, `detect-adaptive`).  Also, to show a complete help listing for every command:

```rst
scenedetect help all
```

## Getting Started

To start off, let's perform adaptive scene detection on a video `my_video.mp4` ([example](usage-example.md)) with the default threshold, and display a list of detected scenes:

```rst
scenedetect --input my_video.mp4 detect-adaptive list-scenes
```

Next, the same, but also split the input video into individual clips (starting from `my_video-Scene-001.mp4`):

```rst
scenedetect --input my_video.mp4 detect-adaptive list-scenes split-video
```

The `split-video` command requires either `ffmpeg` or `mkvmerge` to be available, depending on the options used.  You can override the exact arguments passed to `ffmpeg`:

```rst
scenedetect --input my_video.mp4 detect-adaptive list-scenes split-video --args "-c:v libx264 -crf 20 -c:a aac"
```

You can also specify `-h` / `--high-quality` to produces near lossless results, or `-p`/`--preset` and `-crf`/`--rate-factor` (call `scenedetect help split-video` for details). If either `-c`/`--copy` or `-m`/`--mkvmerge` is specified, codec copying mode is used, at the expense of frame accurate cuts.  Optionally, you can also specify the x264 `-p`/`--preset` and `-crf`/`--rate-factor` (call `scenedetect help split-video` for details).

Note that descriptions for all command-line arguments, as well as their default values, can be obtained by running `scenedetect help` for global options, `scenedetect help [command]` for a specific command, or `help all` for a complete help and command listing.


## Detection Methods

There are two main detection methods PySceneDetect uses: `detect-threshold` (comparing each frame to a set black level, useful for detecting cuts and fades to/from black), and `detect-content` (compares each frame sequentially looking for changes in content, useful for detecting fast cuts between video scenes, although slower to process).  There also is `detect-adaptive`, which uses the same frame score as `detect-content` but compares the ratio of each frame score to its neighbors.

Each mode has slightly different parameters, and is described in detail below. Most detector parameters can also be [set with a config file](http://scenedetect.com/projects/Manual/en/latest/cli/config_file.html).

In general, use `detect-threshold` mode if you want to detect scene boundaries using fades/cuts in/out to black.  If the video uses a lot of fast cuts between content, and has no well-defined scene boundaries, you should use the `detect-adaptive` or  `detect-content` modes.  Once you know what detection mode to use, you can try the parameters recommended below, or generate a statistics file (using the `-s` / `--stats` flag) in order to determine the correct paramters - specifically, the proper threshold value.


### Content-Aware Detection

Unlike threshold mode, content-aware mode looks at the *difference* between each pair of adjacent frames, triggering a scene break when this difference exceeds the threshold value.  The default threshold value (`-t` / `--threshold`), which is good for a first try when using content-aware mode (`detect-content`), is `27`.

```rst
scenedetect -i my_video.mp4 -s my_video.stats.csv list-scenes detect-content
```

Is the equivalent of:

```rst
scenedetect -i my_video.mp4 -s my_video.stats.csv list-scenes detect-content -t 27
```

Remember to supply the `list-scenes` command, after all main program options, to show which scenes were generated, as well as optionally the `save-images` command to save images for each scene, and/or the `split-video` command to split the input video automatically.

The optimal threshold can be determined by generating a stats file (`-s`), opening it with a spreadsheet editor (e.g. Excel), and examining the `content_val` column.  This value should be very small between similar frames, and grow large when a big change in content is noticed (look at the values near frame numbers/times where you know a scene change occurs).  The threshold value should be set so that most scenes fall below the threshold value, and scenes where changes occur should *exceed* the threshold value (thus triggering a scene change).

You can supply the same stats file in subsequent calls to `scenedetect` with different threshold values to speed the processing time up significantly when experimenting with different values on the **same** video (or set of videos).  You *can* use multiple detectors with the same stats file, so long as you supply the *exact* same `-i` / `--input` video file(s) each time.

*Remember*: once a stats file is created, it can only be used with the **same** input video.  If you want to process a different input video (or set of videos), change the name of the stats file supplied to `-s` / `--stats`, or delete the existing stats file on disk.


### Threshold Detection

Threshold-based mode is what most traditional scene detection programs use, which looks at the average intensity of the *current* frame, triggering a scene break when the intensity falls below the threshold (or crosses back upwards).  The default threshold when using the `detect-threshold` is `12` (e.g. `detect-threshold` is the same as `detect-threshold --threshold 12` when the `-t` / `--threshold` option is not supplied), which is a good value to try when detecting fade outs to black on most videos.

```rst
scenedetect -i my_video.mp4 -s my_video.stats.mp4 detect-threshold
```

```rst
scenedetect -i my_video.mp4 -s my_video.stats.mp4 detect-threshold -t 12
```

The optimal threshold can be determined by generating a statsfile (`-s`), opening it with a spreadsheet editor (e.g. Excel), and examining the `average_rgb` column.  These values represent the average intensity of the pixels for that particular frame (taken by averaging the R, G, and B values over the whole frame).  The threshold value should be set so that the average intensity of most frames in content scenes lie above the threshold value, and scenes where scene changes/breaks occur should fall *under* the threshold value (thus triggering a scene change).


### Adaptive Detection

The `detect-adaptive` mode compares each frame's score as calculated by `detect-content` with its neighbors. This score is what forms the `adaptive_ratio` metric in the statsfile. You can also configure the amount of neighboring frames via the `frame-window` option, as well as the minimum change in `content_val` score using `min-content-val`.


## Actions / Commands

After setting the detection method(s), there are several commands that can be used.  Type `scenedetect help [command]` for help/arguments of a specific command listed below:

 - `time`: Used to set input video duration/length or start/end time (discussed below).
 - `list-scenes`: Print and save a list of all scenes in table and CSV format.
 - `split-video`: Split input video into scenes automatically.
 - `save-images`: Save images from the video for each scene.
 - `export-html`: Exports scene list to an HTML file.
 - `help`: Print help for PySceneDetect or a particular command. No processing is done if present.
 - `version`: Print PySceneDetect release version. No processing is done if present.
 - `about`: Print PySceneDetect license agreement and application information. No processing is done if present.

You can also type `scenedetect help all` for the full CLI reference or [view it here](../reference/command-line.md).


## Seeking, Duration, and Setting Start / Stop Times

Specifying the `time` command allows control over what portion of the video PySceneDetect processes.  The `time` command accepts three options: start time (`-s` / `-start`), end time (`-e` / `-end`), and duration (`-d` / `--duration`).  Specifying both end time and duration is redundant, and in this case, duration overrides end time.  Timecodes can be given in three formats:  exact frame number (e.g. `12345`), number of seconds followed by `s` (e.g. `123s`, `123.45s`), or standard format (HH:MM:SS[.nnn], e.g. `12:34:56`, `12:34:56.789`).

For example, let's say we have a video shot at 30 FPS, and want to analyze only the segment from the 5 to the 6.5 minute mark in the video (we want to analyze the 90 seconds [2700 frames] between 00:05:00 and 00:06:30).  The following commands are all thus equivalent in this regard (assuming we are using the content detector):

```rst
scenedetect -i my_video.mp4 time --start 00:05:00 --end 00:06:30 detect-adaptive
```

```rst
scenedetect -i my_video.mp4 time --start 300s --end 390s detect-adaptive
```

```rst
scenedetect -i my_video.mp4 time --start 300s --duration 90s detect-adaptive
```

```rst
scenedetect -i my_video.mp4 time --start 300s --duration 2700 detect-adaptive
```

This demonstrates the different timecode formats, interchanging end time with duration and vice-versa, and precedence of setting duration over end time.


## Saving Image Previews of Detected Scenes

PySceneDetect can automatically save the beginning and ending frame of each detected scene by using the `save-images` command.  If present, the first and last frames of each scene will be saved in the current working directory, using the filename of the input video.

Files marked `00` represent the starting frame of the scene, and those marked `01` represent the last frame (e.g. `testvideo.mp4.Scene-4-01.jpg`).  By default, two images are generated.

Coming soon: If more are specified via the `-n` flag, they will start from `00` (the first frame) and be evenly spaced throughout the scene until the last frame, which will be numbered `N-1`.


## Improving Processing Speed/Performance

The following arguments are global program options, and need to be applied before any commands (e.g. `detect-content`, `list-scenes`).  They can be used to achieve performance gains for some source material with a variable loss of accuracy.

Assuming the input video is of a high enough resolution, a significant performance gain can be achieved by sub-sampling (down-scaling) the input image by a specific integer factor (2x, 3x, 4x, 5x...).  This is applied automatically to some degree based on the input video size, but can be overriden manually with the `-d` / `--downscale` option.

This factor represents how many pixels are "skipped" in both the x- and y- directions, effectively down-scaling the image (using nearest-neighbor sampling) by the factor specified (the new resolution being `W/factor x H/factor` if the old resolution is `W x H`).

Another method that can be used to gain a performance boost is frame skipping.  This method, however, severely reduces frame-accurate scene cuts, so it should only be used with high FPS material (ideally > 60 FPS), at low values (try not to exceed a value of `1` or `2` if using `-fs` / `--frame-skip`), in cases where this is acceptable.  Using the frame skip option also disallows the use of a stats file, which offsets the speed gain if the same video needs to be processed multiple times (e.g. to determine the optimal threshold).

The option still remains, however, for the set of cases where it is still required.  For example, if we skip every other frame (e.g. using `--frame-skip 1`), the processing speed should roughly double.

If set too large, enough frames may be skipped each time that the threshold is met during every iteration, continually triggering scene changes.  This is because frame skipping essentially raises the threshold between frames in the same scene (making them more likely to appear as *cuts*) while not affecting the threshold between frames of different scenes.

This makes the two harder to distinguish, and can cause additional false scene cuts to be detected.  While this can be compensated for by raising the threshold value, this increases the probability of missing a real/true scene cut - thus, the use of the `-fs` / `--frame-skip` option is discouraged.
