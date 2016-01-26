
Currently, this page contains the output of running PySceneDetect with the `--help` flag.  In the future, it will contain expanded definitions and inline examples for those options in the output below.

```md
usage: scenedetect.py [-h] [-v] -i VIDEO_FILE [-o SCENE_LIST] [-t intensity]
                      [-m num_frames] [-p percent] [-b rows] [-s STATS_FILE]
                      [-d detection_method] [-l] [-q] [-st time] [-dt time]
                      [-et time] [-df factor] [-fs num_frames] [-si]

arguments:
  -h, --help            show this help message and exit
  -v, --version         show version number and license/copyright information
  -i VIDEO_FILE, --input VIDEO_FILE
                        [REQUIRED] Path to input video. (default: None)
  -o SCENE_LIST, --output SCENE_LIST
                        File to store detected scenes in using the specified
                        timecodeformat as comma-separated values (.csv). File
                        will be overwritten if already exists. (default: None)
  -t intensity, --threshold intensity
                        8-bit intensity value, from 0-255, to use as the black
                        level in threshold detection mode, or as the change
                        tolerance threshold in content-aware detection mode.
                        (default: 12)
  -m num_frames, --min-scene-length num_frames
                        Minimum length, in frames, before another scene cut
                        can be generated. (default: 15)
  -p percent, --min-percent percent
                        Amount of pixels in a frame, from 0-100%, that must
                        fall under [intensity]. Only applies to threshold
                        detection. (default: 95)
  -b rows, --block-size rows
                        Number of rows in frame to check at once, can be tuned
                        for performance. Only applies to threshold detection.
                        (default: 32)
  -s STATS_FILE, --statsfile STATS_FILE
                        File to store video statistics data, comma-separated
                        value format (.csv). Will be overwritten if exists.
                        (default: None)
  -d detection_method, --detector detection_method
                        Type of scene detection method/algorithm to use;
                        detectors available: [threshold, content]. (default:
                        threshold)
  -l, --list-scenes     Output the final scene list in human-readable format
                        as a table, in addition to CSV. (default: False)
  -q, --quiet           Suppress all output except for final comma-separated
                        list of scene cuts. Useful for computing or piping
                        output directly into other programs/scripts. (default:
                        False)
  -st time, --start-time time
                        Time to seek to in video before performing detection.
                        Can be given in number of frames (12345), seconds
                        (number followed by s, e.g. 123s or 123.45s), or
                        timecode (HH:MM:SS[.nnn]). (default: None)
  -dt time, --duration time
                        Time to limit scene detection to (see -st for time
                        format). Overrides -et. (default: None)
  -et time, --end-time time
                        Time to stop scene detection at (see -st for time
                        format). (default: None)
  -df factor, --downscale-factor factor
                        Factor to downscale (shrink) image before processing,
                        to improve performance. For example, if input video
                        resolution is 1024 x 400, and factor = 2, each frame
                        is reduced to 1024/2 x 400/2 = 512 x 200 before
                        processing. (default: 1)
  -fs num_frames, --frame-skip num_frames
                        Number of frames to skip after processing a given
                        frame. Improves performance at expense of frame
                        accuracy, and may increase probability of inaccurate
                        scene cut prediction. If required, values above 1 or 2
                        are not recommended. (default: 0)
  -si, --save-images    If set, the first and last frames in each detected
                        scene will be saved to disk. Images will saved in the
                        current working directory, using the same filename as
                        the input but with the scene and frame numbers
                        appended. (default: False)
```

