
# Advanced Examples

These examples show some advanced processing techniques, and demonstrate the use of certain more specific command line arguments.  

## Example Three: Improving Processing Speed

Assuming the input video is of a high enough resolution, a significant performance gain can be achieved by sub-sampling (down-scaling) the input image by a specific integer factor (2x, 3x, 4x, 5x...).  This factor represents how many pixels are "skipped" in both the x- and y- directions, effectively down-scaling the image (using nearest-neighbor sampling) by the factor specified (the new resolution being `W/factor x H/factor` if the old resolution is `W x H`).

Another method that can be used to gain a performance boost is frame skipping.  While this reduces frame-accurate frame cuts, it allows for a significant performance gain in cases where this is acceptable.  For example, if we skip every other frame (e.g. `--frameskip 1`), the processing speed will roughly double, but the detected scene cuts.

If set too large, enough frames may be skipped each time that the threshold is met during every iteration, continually triggering scene changes.  This is because frame skipping essentially raises the threshold between frames in the same scene (making them more likely to appear as *cuts*) while not affecting the threshold between frames of different scenes.  This makes the two harder to distinguish, and can cause additional false scene cuts to be detected.  While this can be compensated for by raising the threshold value, this increases the probability of missing a real/true scene cut.


 the time codes that are output may be shifted by up to +/- 1 frame (or whatever other value frame skip is set to).



## Example Four: Statistical Analysis


