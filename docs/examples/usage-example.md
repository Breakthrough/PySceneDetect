
# Getting Started

## Detecting and Splitting Scenes in a Movie Clip

As a concrete example to become familiar with PySceneDetect, let's use the following short clip from the James Bond movie, GoldenEye (Copyright &copy; 1995 MGM):

[https://www.youtube.com/watch?v=OMgIPnCnlbQ](https://www.youtube.com/watch?v=OMgIPnCnlbQ)

You can [download the clip from here](https://github.com/Breakthrough/PySceneDetect/raw/resources/tests/resources/goldeneye/goldeneye.mp4) (may have to right-click and save-as, put the video in your working directory as `goldeneye.mp4`).  We will first demonstrate using the default parameters, then how to find the optimal threshold/sensitivity for a given video, and lastly, using the PySceneDetect output to split the video into individual scenes/clips.


## Content-Aware Detection with Default Parameters

In this case, we want to split this clip up into each individual scene - at each location where a fast cut occurs.  This means we need to use content-aware detecton mode (`detect-content`) or adaptive mode (`detect-adaptive`).  The alternative is to detect fade-in/fade-out using `detect-threshold`.

Using the following command, let's run PySceneDetect on the video using the default threshold/sensitivity:

```rst
scenedetect --input goldeneye.mp4 detect-content list-scenes save-images
```

Running the above command, in the working directory, you should see a file `goldeneye.scenes.csv`, as well as thumbnails for the start/middle/end of each scene as `goldeneye-XXXX-00/01.jpg` (the output directory can be specified with the `-o/--output` option after the `save-images` command, or after `scenedetect` to specify the output for all files).  The results should appear as follows:


|   Scene #    |  Start Time   |    Preview    |
| ------------ | ------------- | ------------- |
|       1      |  00:00:00.000 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-001-01.jpg" width="480" />  |
|       2      |  00:00:03.754 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-002-01.jpg" width="480" />  |
|       3      |  00:00:08.759 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-003-01.jpg" width="480" />  |
|       4      |  00:00:10.802 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-004-01.jpg" width="480" />  |
|       5      |  00:00:15.599 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-005-01.jpg" width="480" />  |
|       6      |  00:00:27.110 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-006-01.jpg" width="480" />  |
|       7      |  00:00:34.117 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-007-01.jpg" width="480" />  |
|       8      |  00:00:36.536 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-008-01.jpg" width="480" />  |
|       9      |  00:00:42.501 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-009-01.jpg" width="480" />  |
|      10      |  00:00:44.002 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-010-01.jpg" width="480" />  |
|      11      |  00:00:45.837 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-011-01.jpg" width="480" />  |
|      12      |  00:00:48.966 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-012-01.jpg" width="480" />  |
|      13      |  00:00:51.134 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-013-01.jpg" width="480" />  |
|      14      |  00:00:52.552 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-014-01.jpg" width="480" />  |
|      15      |  00:00:53.428 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-015-01.jpg" width="480" />  |
|      16      |  00:00:55.639 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-016-01.jpg" width="480" />  |
|      17      |  00:00:56.932 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-017-01.jpg" width="480" />  |
|      18      |  00:01:10.779 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-018-01.jpg" width="480" />  |
|      19      |  00:01:18.036 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-019-01.jpg" width="480" />  |
|      20      |  00:01:19.913 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-020-01.jpg" width="480" />  |
|      21      |  00:01:21.999 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-021-01.jpg" width="480" />  |


Note that this is *almost* perfect - however, one of the scene cuts/breaks in scene 17 was not detected (yielding a total of 21 scenes).  To find the proper threshold, we need to generate a statistics file.


## Finding Optimal Threshold/Sensitivity Value

We now know that a threshold of `30` does not work in all cases for our video, which is clear if we look at the generated images for scene 17 (note the last image is from a different scene):

<img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-017-01.jpg" width="720" />
<br/>
<img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-017-02.jpg" width="720" />
<br/>
<img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-30/goldeneye-Scene-017-03.jpg" width="720" />

We can determine the proper threshold in this case by generating a statistics file (with the `-s` / `--stats` option) for the video `goldeneye.mp4`, and looking at the behaviour of the values where we expect the scene break/cut to occur in scene 17:

```rst
scenedetect --input goldeneye.mp4 --stats goldeneye.stats.csv detect-content list-scenes save-images
```

After examining the file and determining an optimal value of 27 for `detect-content`, we can set the threshold for the detector via:

```rst
scenedetect --input goldeneye.mp4 --stats goldeneye.stats.csv detect-content --threshold 27 list-scenes save-images
```

Note that specifying the same `--stats` file again will make parsing the scenes significantly quicker, as the frame metrics stored in this file are re-used as a cache instead of computing them again. Finally, our updated scene list appears as follows (similar entries skipped for brevity):


|   Scene #    |  Start Time   |    Preview    |
| ------------ | ------------- | ------------- |
|     ...      |      ...      |     ...       |
|      17      |  00:00:56.932 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-017-01.jpg" width="480" />  |
|      18      |  00:01:06.316 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-018-01.jpg" width="480" />  |
|      19      |  00:01:10.779 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/resources/goldeneye/d-content-t-27/goldeneye-Scene-019-01.jpg" width="480" />  |
|     ...      |      ...      |     ...       |

Now the missing scene (scene number 18, in this case) has been detected properly, and our scene list is larger now due to the added cuts.  There should be a total of 22 detected scenes now.


## Splitting/Cutting Video into Clips

The last step to automatically split the input file into clips is to specify the `split-video` command.  This will pass a list of the detected scene timecodes to `ffmpeg` if installed, splitting the input video into scenes.

You may also want to use the `-c/--copy` option to ensure that no re-encoding is performed (using `mkvmerge` instead), at the expense of frame-accurate scene cuts, since when copying, cuts can sometimes only be generated on keyframes.  You can also pass the `-hq/--high-quality` option to ensure the output videos are visually identical to the input (at the expense of longer processing time and greater filesize).

Thus, to generate a sequence of files `goldeneye-scene-001.mp4`, `goldeneye-scene-002.mp4`, `goldeneye-scene-003.mp4`..., our full command becomes:


```rst
scenedetect -i goldeneye.mp4 -o output_dir detect-content -t 27 list-scenes save-images split-video
```

The scene number `-001` will be added to the output filename automatically.

