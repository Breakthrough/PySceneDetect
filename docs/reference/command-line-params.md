
## PySceneDetect CLI Reference


<div class="warning">
All information on this page can be obtained on the command line by running the command <tt>scenedetect help all</tt>, <tt>scenedetect help</tt> to get started, or <tt>scenedetect help [commmand]</tt> for information about a particular command.
<br /><br />
The complete PySceneDetect CLI Reference 📚 for the <tt>scenedetect</tt> command can be found in the <a href="http://pyscenedetect-manual.readthedocs.io/" alt="Manual Link">PySceneDetect Manual</a>, located at <a href="http://pyscenedetect-manual.readthedocs.io/" alt="Manual Link">pyscenedetect-manual.readthedocs.io/</a>.  This page will eventually be deprecated in favor of the manual.
</div>


The PySceneDetect command-line interface is grouped into commands which
can be combined together, each containing its own set of arguments:

```md
scenedetect ([options]) [command] ([options]) ([...other command(s)...])
```

Where [command] is the name of the command, and ([options]) are the
arguments/options associated with the command, if any. Options
associated with the scenedetect command below (e.g. --input,
--framerate) must be specified before any commands. The order of
commands is not strict, but each command should only be specified once.

Commands can also be combined, for example, running the 'detect-content'
and 'list-scenes' (specifying options for the latter):

```md
scenedetect -i vid0001.mp4 detect-content list-scenes -n
```
A list of all commands is printed below. Help for a particular command
can be printed by specifying 'help [command]', or 'help all' to print
the help information for every command.

Lastly, there are several commands used for displaying application
version and copyright information (e.g. scenedetect about):

 - `version`: Displays the version of PySceneDetect being used.
 - `about`:   Displays PySceneDetect license and copyright information.


## Global Options

```md
PySceneDetect Option/Command List:
----------------------------------------------------

Usage: scenedetect [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

  For example:

  scenedetect -i video.mp4 -s video.stats.csv detect-content list-scenes

  Note that the following options represent [OPTIONS] above. To list the
  optional [ARGS] for a particular COMMAND, type `scenedetect help COMMAND`.
  You can also combine commands (e.g. scenedetect [...] detect-content save-
  images --png split-video).

Options:
  -i, --input VIDEO      [Required] Input video file. May be specified
                         multiple times to concatenate several videos
                         together. Also supports image sequences and URLs.
  -o, --output DIR       Output directory for all files (stats file, output
                         videos, images, log files, etc...).
  -f, --framerate FPS    Force framerate, in frames/sec (e.g. -f 29.97).
                         Disables check to ensure that all input videos have
                         the same framerates.
  -d, --downscale N      Integer factor to downscale frames by (e.g. 2, 3,
                         4...), where the frame is scaled to width/N x
                         height/N (thus -d 1 implies no downscaling). Each
                         increment speeds up processing by a factor of 4 (e.g.
                         -d 2 is 4 times quicker than -d 1). Higher values can
                         be used for high definition content with minimal
                         effect on accuracy. [default: 2 for SD, 4 for 720p, 6
                         for 1080p, 12 for 4k]
  -fs, --frame-skip N    Skips N frames during processing (-fs 1 skips every
                         other frame, processing 50% of the video, -fs 2
                         processes 33% of the frames, -fs 3 processes 25%,
                         etc...). Reduces processing speed at expense of
                         accuracy.  [default: 0]
  -m, --min-scene-len TIMECODE
                         Minimum size/length of any scene. TIMECODE can
                         be specified as exact number of frames, a time
                         in seconds followed by s, or a timecode in the
                         format HH:MM:SS or HH:MM:SS.nnn [default: 0.6s]
  --drop-short-scenes    Drop scenes shorter than `--min-scene-len`
                         instead of combining them with neighbors
  -s, --stats CSV        Path to stats file (.csv) for writing frame metrics
                         to. If the file exists, any metrics will be
                         processed, otherwise a new file will be created. Can
                         be used to determine optimal values for various scene
                         detector options, and to cache frame calculations in
                         order to speed up multiple detection runs.
  -v, --verbosity LEVEL  Level of debug/info/error information to show.
                         Setting to none will suppress all output except that
                         generated by actions (e.g. timecode list output).
  -l, --logfile LOG      Path to log file for writing application logging
                         information, mainly for debugging. Make sure to set
                         "-il debug" as well if you are submitting a bug
                         report.
  -q, --quiet            Suppresses all output of PySceneDetect except for
                         those from the specified commands. Equivalent to
                         setting "--info-level none", and overrides the
                         current info-level, even if --info-level/-il is
                         specified.
  -h, --help             Show this message and exit.

```


## Command List

```md
Commands:
  about             Print license/copyright info.
  detect-content    Perform content detection algorithm on input...
  detect-threshold  Perform threshold detection algorithm on...
  export-html       Exports scene list to a HTML file.
  help              Print help for command (help [command]).
  list-scenes       Prints scene list and outputs to a CSV file.
  save-images       Create images for each detected scene.
  split-video       Split input video using ffmpeg or...
  time              Set start/end/duration of input video.
  version           Print version of PySceneDetect.
```


## `time` Command

```md
PySceneDetect time Command
----------------------------------------------------
Usage: scenedetect time [OPTIONS]

  Set start/end/duration of input video.

  Time values can be specified as frames (NNNN), seconds (NNNN.NNs), or as a
  timecode (HH:MM:SS.nnn). For example, to start scene detection at 1
  minute, and stop after 100 seconds:

  time --start 00:01:00 --duration 100s

  Note that --end and --duration are mutually exclusive (i.e. only one of
  the two can be set). Lastly, the following is an example using absolute
  frame numbers to process frames 0 through 1000:

  time --start 0 --end 1000

Options:
  -s, --start TIMECODE     Time in video to begin detecting scenes. TIMECODE
                           can be specified as exact number of frames (-s 100
                           to start at frame 100), time in seconds followed by
                           s (-s 100s to start at 100 seconds), or a timecode
                           in the format HH:MM:SS or HH:MM:SS.nnn (-s 00:01:40
                           to start at 1m40s).  [default: 0]
  -d, --duration TIMECODE  Maximum time in video to process. TIMECODE format
                           is the same as other arguments. Mutually exclusive
                           with --end / -e.
  -e, --end TIMECODE       Time in video to end detecting scenes. TIMECODE
                           format is the same as other arguments. Mutually
                           exclusive with --duration / -d.
  -h, --help               Show this message and exit.
```


## `detect-content` Command

```md
PySceneDetect detect-content Command
----------------------------------------------------
Usage: scenedetect detect-content [OPTIONS]

  Perform content detection algorithm on input video.

  detect-content

  detect-content --threshold 27.5

Options:
  -t, --threshold VAL         Threshold value (float) that the delta_hsv frame
                              metric must exceed to trigger a new scene.
                              Refers to frame metric delta_hsv_avg in stats
                              file.  [default: 30.0]
  -h, --help                  Show this message and exit.
```


## `detect-threshold` Command

```md
PySceneDetect detect-threshold Command
----------------------------------------------------
Usage: scenedetect detect-threshold [OPTIONS]

  Perform threshold detection algorithm on input video.

  detect-threshold

  detect-threshold --threshold 15

Options:
  -t, --threshold VAL         Threshold value (integer) that the delta_rgb
                              frame metric must exceed to trigger a new scene.
                              Refers to frame metric delta_rgb in stats file.
                              [default: 12]
  -f, --fade-bias PERCENT     Percent (%) from -100 to 100 of timecode skew
                              for where cuts should be placed. -100 indicates
                              the start frame, +100 indicates the end frame,
                              and 0 is the middle of both.  [default: 0]
  -l, --add-last-scene        If set, if the video ends on a fade-out, an
                              additional scene will be generated for the last
                              fade out position.
  -p, --min-percent PERCENT   Percent (%) from 0 to 100 of amount of pixels
                              that must meet the threshold value in orderto
                              trigger a scene change.  [default: 95]
  -b, --block-size N          Number of rows in image to sum per iteration
                              (can be tuned for performance in some cases).
                              [default: 8]
  -h, --help                  Show this message and exit.
```


## `list-scenes` Command

```md
PySceneDetect list-scenes Command
----------------------------------------------------
Usage: scenedetect list-scenes [OPTIONS]

  Prints scene list and outputs to a CSV file. The default filename is
  $VIDEO_NAME-Scenes.csv.

Options:
  -o, --output DIR      Output directory to save videos to. Overrides global
                        option -o/--output if set.
  -f, --filename NAME   Filename format to use for the scene list CSV file.
                        You can use the $VIDEO_NAME macro in the file name.
                        Note that you may have to wrap the name using single
                        quotes.  [default: $VIDEO_NAME-Scenes.csv]
  -n, --no-output-file  Disable writing scene list CSV file to disk.  If set,
                        -o/--output and -f/--filename are ignored.
  -q, --quiet           Suppresses output of the table printed by the list-
                        scenes command.
  -s, --skip-cuts       Skips outputting the cutting list as the first row in
                        the CSV file. Set this option if compliance with RFC
                        4810 is required.
```


## `save-images` Command

```md
PySceneDetect save-images Command
----------------------------------------------------
Usage: scenedetect save-images [OPTIONS]

  Create images for each detected scene.

Options:
  -o, --output DIR      Output directory to save images to. Overrides global
                        option -o/--output if set.
  -f, --filename NAME   Filename format, *without* extension, to use when
                        saving image files. You can use the $VIDEO_NAME,
                        $SCENE_NUMBER, $IMAGE_NUMBER, and $FRAME_NUMBER macros in the file
                        name. Note that you may have to wrap the format in
                        single quotes.  [default: $VIDEO_NAME-
                        Scene-$SCENE_NUMBER-$IMAGE_NUMBER]
  -n, --num-images N    Number of images to generate. Will always include
                        start/end frame, unless N = 1, in which case the image
                        will be the frame at the mid-point in the scene.
  -j, --jpeg            Set output format to JPEG. [default]
  -w, --webp            Set output format to WebP.
  -q, --quality Q       JPEG/WebP encoding quality, from 0-100 (higher
                        indicates better quality). For WebP, 100 indicates
                        lossless. [default: JPEG: 95, WebP: 100]  [0<=x<=100]
  -p, --png             Set output format to PNG.
  -c, --compression C   PNG compression rate, from 0-9. Higher values produce
                        smaller files but result in longer compression time.
                        This setting does not affect image quality, only file
                        size. [default: 3]  [0<=x<=9]
  -m, --frame-margin N  Number of frames to ignore at the beginning and end of
                        scenes when saving images [default: 1]
  -s  --scale S         Optional factor by which saved images are rescaled. A
                        scaling factor of 1 would not result in rescaling. A
                        value <1 results in a smaller saved image, while a
                        value >1 results in an image larger than the original.
                        This value is ignored if either the height, -h, or
                        width, -w, values are specified.
  -h  --height H        Optional value for the height of the saved images.
                        Specifying both the height and width, -w, will resize
                        images to an exact size, regardless of aspect ratio.
                        Specifying only height will rescale the image to that
                        number of pixels in height while preserving the aspect
                        ratio.
  -w  --width W         Optional value for the width of the saved images.
                        Specifying both the width and height, -h, will resize
                        images to an exact size, regardless of aspect ratio.
                        Specifying only width will rescale the image to that
                        number of pixels wide while preserving the aspect ratio.
```


## `split-video` Command

```md
PySceneDetect split-video Command
----------------------------------------------------
Usage: scenedetect split-video [OPTIONS]

  Split input video using ffmpeg or mkvmerge.

Options:
  -o, --output DIR          Output directory to save videos to. Overrides
                            global option -o/--output if set.
  -f, --filename NAME       File name format, to use when saving image files.
                            You can use the $VIDEO_NAME and $SCENE_NUMBER
                            macros in the file name. Note that you may have
                            to wrap the name using single quotes.
                            [default: $VIDEO_NAME-Scene-$SCENE_NUMBER]
  -h, --high-quality        Encode video with higher quality, overrides -f
                            option if present. Equivalent to specifying
                            --rate-factor 17 and --preset slow.
  -a, --args ARGS  Override codec arguments/options passed to FFmpeg
                            when splitting and re-encoding scenes. Use double
                            quotes (") around specified arguments. Must
                            specify at least audio/video codec to use
                            (e.g. -a "-c:v [...] and -c:a [...]").
                            [default: "-c:v libx264 -preset veryfast
                            -crf 22 -c:a copy"]
  -q, --quiet               Suppresses output from external video splitting
                            tool.
  -c, --copy                Copy instead of re-encode using mkvmerge instead
                            of ffmpeg for splitting videos. All other
                            arguments except -o/--output and -q/--quiet are
                            ignored in this mode, and output files will be
                            named $VIDEO_NAME-$SCENE_NUMBER.mkv. Significantly
                            faster when splitting videos, however, output
                            videos sometimes may not be split exactly,
                            especially if the scenes are very short in length,
                            or the input video is heavily compressed. This can
                            lead to smaller scenes being merged with others,
                            or scene boundaries being shifted in time - thus
                            when using this option, the number of videos
                            written may not match the number of scenes that
                            was detected.
  -crf, --rate-factor RATE  Video encoding quality (x264 constant rate
                            factor), from 0-100, where lower values represent
                            better quality, with 0 indicating lossless.
                            [default: 22, if -h/--high-quality is set: 17]
  -p, --preset LEVEL        Video compression quality preset (x264 preset).
                            Can be one of: ultrafast, superfast, veryfast,
                            faster, fast, medium, slow, slower, and veryslow.
                            Faster modes take less time to run, but the output
                            files may be larger. [default: veryfast, if
                            -h/--high quality is set: slow]
```


## `export-html` Command

```md
PySceneDetect export-html Command
----------------------------------------------------
Usage: scenedetect.py export-html [OPTIONS]

  Exports scene list to a HTML file. Requires save-images by default.

Options:
  -f, --filename NAME        Filename format to use for the scene list HTML
                             file. You can use the $VIDEO_NAME macro in the
                             file name. Note that you may have to wrap the
                             the format name using single quotes.
                             [default: $VIDEO_NAME-Scenes.html]
  --no-images                Export the scene list including or excluding the
                             saved images.
  -w, --image-width pixels   Width in pixels of the images in the resulting
                             HTML table.
  -h, --image-height pixels  Height in pixels of the images in the resulting
                             HTML table.
```
