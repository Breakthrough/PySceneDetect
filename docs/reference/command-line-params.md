
Currently, this page contains the output of running PySceneDetect with the `--help` flag.  In the future, it will contain expanded definitions and inline examples for those options in the output below.

```md
usage: scenedetect.py [-h] [-v] -i VIDEO_FILE [-o SCENE_LIST] [-t intensity]
                      [-m NUM_FRAMES] [-p percent] [-b rows] [-s STATS_FILE]
                      [-d detection_method] [-l] [-q]

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
  -m NUM_FRAMES, --min-scene-length NUM_FRAMES
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
```

