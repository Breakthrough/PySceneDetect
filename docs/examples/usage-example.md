
# Getting Started

## Detecting and Splitting Scenes in a Movie Clip

As a concrete example to become familiar with PySceneDetect, let's use the following short clip from the James Bond movie, GoldenEye (Copyright &copy; 1995 MGM):

[https://www.youtube.com/watch?v=OMgIPnCnlbQ](https://www.youtube.com/watch?v=OMgIPnCnlbQ)

You can [download the clip from here](https://github.com/Breakthrough/PySceneDetect/raw/resources/tests/goldeneye/goldeneye.mp4) (may have to right-click and save-as, put the video in your working directory as `goldeneye.mp4`).  We will first demonstrate using the default parameters, then how to find the optimal threshold/sensitivity for a given video, and lastly, using the PySceneDetect output to split the video into individual scenes/clips.


## Content-Aware Detection with Default Parameters

In this case, we want to split this clip up into each individual scene - at each location where a fast cut occurs.  This means we need to use content-aware detecton mode (`-d content`).  Using the following command, let's run PySceneDetect on the video using the default threshold/sensitivity:

```rst
scenedetect --input goldeneye.mp4 detect-content list-scenes save-images
```

Running the above command, in the working directory, you should see a file `goldeneye.scenes.csv`, as well as thumbnails for the start/middle/end of each scene as `goldeneye-XXXX-00/01.jpg` (the output directory can be specified with the `-o/--output` option after the `save-images` command, or after `scenedetect` to specify the output for all files).  The results should appear as follows:


|   Scene #    |  Start Time   |    Preview    |
| ------------ | ------------- | ------------- |
|       1      |  00:00:03.502 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-01.jpg" width="480" />  |
|       2      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-02.jpg" width="480" />  |
|       3      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-03.jpg" width="480" />  |
|       4      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-04.jpg" width="480" />  |
|       5      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-05.jpg" width="480" />  |
|       6      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-06.jpg" width="480" />  |
|       7      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-07.jpg" width="480" />  |
|       8      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-08.jpg" width="480" />  |
|       9      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-09.jpg" width="480" />  |
|      10      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-10.jpg" width="480" />  |
|      11      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-11.jpg" width="480" />  |
|      12      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-12.jpg" width="480" />  |
|      13      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-13.jpg" width="480" />  |
|      14      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-14.jpg" width="480" />  |
|      15      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-15.jpg" width="480" />  |
|      16      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-16.jpg" width="480" />  |
|      17      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-17.jpg" width="480" />  |
|      18      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-18.jpg" width="480" />  |
|      19      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-19.jpg" width="480" />  |
|      20      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-20.jpg" width="480" />  |


Note that this is *almost* perfect - however, one of the scene cuts/breaks in scene 17 was not detected.  We will now generate a statistics file for the `goldeneye.mp4` video to determine the optimal detection threshold (`--threshold 27` ends up being the optimal value for `goldeneye.mp4` when using `detect-content`, versus the default value of `30`).  Finally, we will use the output from PySceneDetect to split the original video into individual files/clips.


## Finding Optimal Threshold/Sensitivity Value

We now know that a threshold of `30` does not work in all cases for our video, as per scene 17 detected above (note the last image is from a different scene):

<img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-30/ge-scene-17.jpg" width="720" /> 

We can determine the proper threshold in this case by generating a statistics file (with the `-s` / `--stats` option) for the video `goldeneye.mp4`, and looking at the behaviour of the values where we expect the scene break/cut to occur in scene 17:

scenedetect --input goldeneye.mp4 --stats goldeneye.stats.csv detect-content list-scenes save-images

After examining the file and determining an optimal value of 27 for `detect-content`, we can set the threshold for the detector via:

scenedetect --input goldeneye.mp4 --stats goldeneye.stats.csv detect-content --threshold 27 list-scenes save-images

Note that specifying the same `--stats` file again will make parsing the scenes significantly quicker, as the frame metrics stored in this file are re-used as a cache instead of computing them again. Finally, our updated scene list appears as follows (similar entries skipped for brevity):


|   Scene #    |  Start Time   |    Preview    |
| ------------ | ------------- | ------------- |
|     ...      |      ...      |     ...       |
|      16      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-27/ge-scene-16.jpg" width="480" />  |
|      17      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-27/ge-scene-17.jpg" width="480" />  |
|      18      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-27/ge-scene-18.jpg" width="480" />  |
|      19      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-27/ge-scene-19.jpg" width="480" />  |
|      20      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-27/ge-scene-20.jpg" width="480" />  |
|      21      |  00:00:04.144 | <img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/resources/tests/goldeneye/d-content-t-27/ge-scene-21.jpg" width="480" />  |


Now the missing scene (scene number 18, in this case) has been detected properly, and our scene list is larger now due to the added cuts.


## Splitting/Cutting Video into Clips

The last step to automatically split the input file into clips is to specify the `split-video` command.  This will pass a list of the detected scene timecodes to `ffmpeg` if installed, splitting the input video into scenes.

You may also want to use the `-c/--copy` option to ensure that no re-encoding is performed (using `mkvmerge` instead), at the expense of frame-accurate scene cuts, since when copying, cuts can sometimes only be generated on keyframes.  You can also pass the `-h/--high-quality` option to ensure the output videos are visually identical to the input (at the expense of longer processing time and greater filesize).

Thus, to generate a sequence of files `goldeneye-scene-001.mp4`, `goldeneye-scene-002.mp4`, `goldeneye-scene-003.mp4`..., our full command becomes:


```rst
scenedetect -i goldeneye.mp4 -o output_dir detect-content -t 27 list-scenes save-images split-video
```

The scene number `-001` will be added to the output filename automatically.

