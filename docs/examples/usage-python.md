
# PySceneDetect Python Interface

In addition to being used from the command line, or through the GUI, PySceneDetect can be used in Python directly - allowing easy integration into other applications/scripts, or interactive use through a Python REPL/notebook.

## Simple Example

The below code sample shows the general usage style of how to detect scenes using PySceneDetect and custom Python code.  The end result is three separate lists:  `scene_list`, `scene_list_msec`, and `scene_list_tc`, all containing the detected scene breaks/cuts in different formats (frame #, milliseconds, and timecode string in `HH:MM:SS.nnn` format, respectively).

    import scenedetect

    scene_list = []        # Scenes will be added to this list in detect_scenes().
    path = 'my_video.mp4'  # Path to video file.

    # Usually use one detector, but multiple can be used.
    detector_list = [
        scenedetect.detectors.ThresholdDetector(threshold = 16, min_percent = 0.9)
    ]

    video_framerate, frames_read = scenedetect.detect_scenes_file(
        path, scene_list, detector_list)

    # scene_list now contains the frame numbers of scene boundaries.
    print scene_list

    # create new list with scene boundaries in milliseconds instead of frame #.
    scene_list_msec = [(1000.0 * x) / float(video_fps) for x in scene_list]

    # create new list with scene boundaries in timecode strings ("HH:MM:SS.nnn").
    scene_list_tc = [scenedetect.timecodes.get_string(x) for x in scene_list_msec]

## Scene Detection in a Python REPL

PySceneDetect can be used interactively as well.  One way to get familiar with this is to type the above example into a Python REPL line by line, viewing the output as you run through the code and making sure you understand the output/results.  In the future, functions may be added to preview the scene boundaries graphically using OpenCV's GUI functionality, to allow interactive use of PySceneDetect from the command-line without launching the full GUI.
