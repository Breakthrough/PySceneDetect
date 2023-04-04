
# Getting Started

As a concrete example to become familiar with PySceneDetect, let's use the following short clip from the James Bond movie, GoldenEye (Copyright &copy; 1995 MGM):

[https://www.youtube.com/watch?v=OMgIPnCnlbQ](https://www.youtube.com/watch?v=OMgIPnCnlbQ)

You can [download the clip from here](https://github.com/Breakthrough/PySceneDetect/raw/resources/tests/resources/goldeneye/goldeneye.mp4) (may have to right-click and save-as, put the video in your working directory as `goldeneye.mp4`).


## Content-Aware Detection

In this case, we want to split this clip up into each individual scene - at each location where a fast cut occurs.  This means we need to use content-aware detecton mode (`detect-content`) or adaptive mode (`detect-adaptive`).  If the video instead contains fade-in/fade-out transitions you want to find, you can use `detect-threshold` instead.

Using the following command, let's run PySceneDetect on the video, and also save a scene list CSV file and some images of each scene:

```rst
scenedetect --input goldeneye.mp4 detect-adaptive list-scenes save-images
```

Running the above command, in the working directory, you should see a file `goldeneye.scenes.csv`, as well as individual frames for the start/middle/end of each scene as `goldeneye-XXXX-00/01.jpg`.  The results should appear as follows:


|   Scene #    |  Start Time   |    Preview    |
| ------------ | ------------- | ------------- |
|       1      |  00:00:00.000 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-001-01.jpg" width="480" />  |
|       2      |  00:00:03.754 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-002-01.jpg" width="480" />  |
|       3      |  00:00:08.759 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-003-01.jpg" width="480" />  |
|       4      |  00:00:10.802 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-004-01.jpg" width="480" />  |
|       5      |  00:00:15.599 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-005-01.jpg" width="480" />  |
|       6      |  00:00:27.110 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-006-01.jpg" width="480" />  |
|       7      |  00:00:34.117 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-007-01.jpg" width="480" />  |
|       8      |  00:00:36.536 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-008-01.jpg" width="480" />  |
|      ...     |       ...      |       ...      |
|      18      |  00:01:06.316 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-018-01.jpg" width="480" />  |
|      19      |  00:01:10.779 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-019-01.jpg" width="480" />  |
|      20      |  00:01:18.036 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-020-01.jpg" width="480" />  |
|      21      |  00:01:19.913 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-021-01.jpg" width="480" />  |
|      22      |  00:01:21.999 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-022-01.jpg" width="480" />  |


## Splitting Video into Clips

The `split-video` command can be used to automatically split the input video using `ffmpeg` or `mkvmerge`. For example:

```rst
scenedetect -i goldeneye.mp4 detect-adaptive split-video
```

Type `scenedetect help split-video` for a full list of options which can be specified for video splitting, including high quality mode (`-hq/--high-quality`) or copy mode (`-c/--copy`).


## Tweaking Detection Parameters

Detectors take a variety of parameters, which can be [configured via command-line](http://scenedetect.com/projects/Manual/en/latest/cli/detectors.html) or by [using a config file](http://scenedetect.com/projects/Manual/en/latest/cli/config_file.html). If the default parameters do not produce correct results, you can generate a stats file using the `-s` / `--stats` option.

For example, with `detect-content`, if the default threshold of `27` does not produce correct results, we can determine the proper threshold by first generating a stats file:

```rst
scenedetect --input goldeneye.mp4 --stats goldeneye.stats.csv detect-adaptive
```

We can then plot the values of the `content_val` column:

<img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/master/docs/img/goldeneye-stats.png" alt="goldeneye.mp4 statistics graph" />

The peaks in values correspond to the scene breaks in the input video. In some cases the threshold may need to be raised or lowered accordingly.
