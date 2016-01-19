
## Scene Detection Methods/Algorithms

This page discusses the scene detection methods/algorithms available for use in PySceneDetect, including details describing the operation of the detection method, as well as relevant command-line arguments and recommended values.


### Content-Aware Detector

The content-aware scene detector (`-d content`) works the way most people think of "cuts" between scenes in a movie - given two frames, do they belong to the same scene, or different scenes?  The content-aware scene detector finds areas where the *difference* between two subsequent frames exceeds the threshold value that is set (a good value to start with is `--threshold 30`).

This allows you to detect cuts between scenes both containing content, rather than how most traditional scene detection methods work.  With a properly set threshold, this method can even detect minor, abrupt changes, such as [jump cuts](https://en.wikipedia.org/wiki/Jump_cut) in film.


### Threshold Detector

The threshold-based scene detector (`-d threshold`) is how most traditional scene detection methods work (e.g. the `ffmpeg blackframe` filter), by comparing the intensity/brightness of the current frame with a set threshold, and triggering a scene cut/break when this value crosses the threshold.  In PySceneDetect, this value is computed by averaging the R, G, and B values for every pixel in the frame, yielding a single floating point number representing the average pixel value (from 0.0 to 255.0).

