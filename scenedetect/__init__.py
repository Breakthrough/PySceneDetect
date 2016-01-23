#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains all code for the main `scenedetect` module. 
#
# Copyright (C) 2012-2016 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy and OpenCV; see the LICENSE-NUMPY and
# LICENSE-OPENCV files or visit one of above URLs for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

# Standard Library Imports
from __future__ import print_function
import sys
import argparse
import time

# PySceneDetect Library Imports
import scenedetect.platform
import scenedetect.detectors
import scenedetect.timecodes
import scenedetect.cli

# Third-Party Library Imports
import cv2
import numpy


# Used for module identification and when printing copyright & version info.
__version__ = 'v0.3.1-beta'

# About & copyright message string shown for the -v / --version CLI argument.
ABOUT_STRING   = """PySceneDetect %s
-----------------------------------------------
https://github.com/Breakthrough/PySceneDetect
http://www.bcastell.com/projects/pyscenedetect
-----------------------------------------------
Copyright (C) 2012-2016 Brandon Castellano
License: BSD 2-Clause (see the included LICENSE file for details,
  or visit < http://www.bcastell.com/projects/pyscenedetect >).

This software uses the following third-party components:
  > NumPy [Copyright (C) 2005-2013, Numpy Developers]
  > OpenCV [Copyright (C) 2016, Itseez]

THE SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.

""" % __version__


def detect_scenes_file(path, scene_list, detector_list, stats_file = None,
                  downscale_factor = 0, frame_skip = 0, quiet_mode = False,
                  perf_update_rate = -1):
    """Performs scene detection on passed file using given scene detectors.

    Essentially wraps detect_scenes while handling all OpenCV interaction.

    Args:
        path:  A string containing the filename of the video to open.
        scene_list:  List to append frame numbers of any detected scene cuts.
        detector_list:  List of scene detection algorithms to run on the video.
        stats_file:  Optional. Handle to a file, open for writing, to save the
            frame metrics computed by each detection algorithm, in CSV format.
        quiet_mode:  Optional. Suppresses any console output (inluding errors).
        perf_update_rate:  Optional. Prints updates every [perf_update_rate]
            seconds with the current processing speed, in frames/second.
        downscale_factor:  Optional.  Number of pixels to skip in both x- and y
            directions, downscaling the image for improved performance.
            Integer number >= 2, otherwise disabled.
        frame_skip:  Optional.  Number of frames to skip during each iteration,
            useful for higher FPS videos to improve performance.
            Unsigned integer number larger than zero, otherwise disabled.

    Returns:
        Tuple containing (video_fps, frames_read), where video_fps is a float
        of the video file's framerate, and frames_read is a positive, integer
        number of frames read from the video file.  Both values are set to -1
        if the file could not be opened.

    """

    cap = cv2.VideoCapture()
    frames_read = -1
    video_fps = -1

    # Attempt to open the passed input (video) file.
    cap.open(path)
    if not cap.isOpened():
        if not quiet_mode:
            print('[PySceneDetect] FATAL ERROR - could not open video %s.' % 
                path)
        return frames_read
    elif not quiet_mode:
        print('[PySceneDetect] Parsing video %s...' % path)

    # Print video parameters (resolution, FPS, etc...)
    video_width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    video_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    video_fps    = cap.get(cv2.CAP_PROP_FPS)
    if not quiet_mode:
        print('[PySceneDetect] Video Resolution / Framerate: %d x %d / %2.3f FPS' % (
            video_width, video_height, video_fps ))
        if downscale_factor >= 2:
            print('[PySceneDetect] Subsampling Enabled (%dx, Resolution = %d x %d)' % (
                downscale_factor, video_width / downscale_factor, video_height / downscale_factor ))
        print('Verify that the above parameters are correct'
            ' (especially framerate, use --force-fps to correct if required).')

    # Perform scene detection on cap object (modifies scene_list).
    frames_read = detect_scenes(cap, scene_list, detector_list, stats_file,
                                downscale_factor, frame_skip, quiet_mode,
                                perf_update_rate)

    # Cleanup and return number of frames we read.
    cap.release()
    return (video_fps, frames_read)


def detect_scenes(cap, scene_list, detector_list, stats_file = None,
                  downscale_factor = 0, frame_skip = 0, quiet_mode = False,
                  perf_update_rate = -1):
    """Performs scene detection based on passed video and scene detectors.

    Args:
        cap:  An open cv2.VideoCapture object that is assumed to be at the
            first frame.  Frames are read until cap.read() returns False, and
            the cap object remains open (it can be closed with cap.release()).
        scene_list:  List to append frame numbers of any detected scene cuts.
        detector_list:  List of scene detection algorithms to run on the video.
        stats_file:  Optional. Handle to a file, open for writing, to save the
            frame metrics computed by each detection algorithm, in CSV format.
        quiet_mode:  Optional. Suppresses any console output (inluding errors).
        perf_update_rate:  Optional. Prints updates every [perf_update_rate]
            seconds with the current processing speed, in frames/second.
        downscale_factor:  Optional. Indicates at what factor each frame will
            be downscaled/reduced before processing (improves performance).
            For example, if downscale_factor = 2, and the input is 1024 x 400,
            each frame will be reduced to 512 x 200 ( = 1024/2 x 400/2).
            Integer number >= 2, otherwise disabled (i.e. scale = 1).
        frame_skip:  Optional.  Number of frames to skip during each iteration,
            useful for higher FPS videos to improve performance.
            Unsigned integer number larger than zero, otherwise disabled.

    Returns:
        Unsigned, integer number of frames read from the passed cap object.
    """
    frames_read = 0
    frame_metrics = {}

    perf_show = True
    perf_last_update_time = time.time()
    perf_last_framecount = 0
    perf_curr_rate = 0
    if perf_update_rate > 0:
        perf_update_rate = float(perf_update_rate)
    else:
        perf_show = False

    if not downscale_factor >= 2: downscale_factor = 0
    if not frame_skip > 0: frame_skip = 0

    while True:
        # If frameskip is set, we drop the required number of frames first.
        if frame_skip > 0:
            for i in range(frame_skip):
                (rv, im) = cap.read()
                if not rv:
                    break
                frames_read += 1

        (rv, im) = cap.read()
        if not rv:
            break
        if not frames_read in frame_metrics:
            frame_metrics[frames_read] = dict()
        for detector in detector_list:
            if downscale_factor > 0:
                detector.process_frame(
                    frames_read, im[::downscale_factor,::downscale_factor,:],
                    frame_metrics, scene_list)
            else:
                detector.process_frame(
                    frames_read, im, frame_metrics, scene_list)
        if stats_file:
            # write frame metrics to stats_file
            pass
        frames_read += 1
        # periodically show processing speed/performance
        if not quiet_mode and perf_show:
            curr_time = time.time()
            if (curr_time - perf_last_update_time) > perf_update_rate:
                delta_t = curr_time - perf_last_update_time
                delta_f = frames_read - perf_last_framecount
                if delta_t > 0: # and delta_f > 0: # delta_f will always be > 0
                    perf_curr_rate = delta_f / delta_t
                else:
                    perf_curr_rate = 0.0
                perf_last_update_time = curr_time
                perf_last_framecount = frames_read
                print("[PySceneDetect] Current Processing Speed: %3.1f FPS" % perf_curr_rate)

    [detector.post_process(scene_list) for detector in detector_list]
    return frames_read


def main():
    """Entry point for running PySceneDetect as a program.

    Handles high-level interfacing of video and scene detection / output.
    """

    # Parse CLI arguments.
    scene_detectors = scenedetect.detectors.get_available()
    timecode_formats = scenedetect.timecodes.get_available()
    args = scenedetect.cli.get_cli_parser(
        scene_detectors.keys(), timecode_formats.keys()).parse_args()

    # Load SceneDetector with proper arguments based on passed detector (-d).
    # TODO: Add minimum scene length as a variable argument.
    detection_method = args.detection_method.lower()
    detector = None
    if (detection_method == 'content'):
        detector = scene_detectors['content'](args.threshold, args.min_scene_len)
    elif (detection_method == 'threshold'):
        detector = scene_detectors['threshold'](
            args.threshold, args.min_percent/100.0, args.min_scene_len,
            block_size = args.block_size)
    
    # Perform scene detection using specified mode.
    start_time = time.time()
    if not args.quiet_mode:
        print('[PySceneDetect] Detecting scenes (%s mode)...' % detection_method)
    scene_list = list()
    video_fps, frames_read = detect_scenes_file(
                                path = args.input.name,
                                scene_list = scene_list,
                                detector_list = [detector],
                                stats_file = args.stats_file,
                                downscale_factor = args.downscale_factor,
                                frame_skip = args.frame_skip,
                                quiet_mode = args.quiet_mode
                            )
    elapsed_time = time.time() - start_time
    perf_fps = float(frames_read) / elapsed_time
    # Print performance (average framerate), and scene list if requested.
    if not args.quiet_mode:
        print('[PySceneDetect] Processing complete, found %d scenes in video.' %
            len(scene_list))
        print('[PySceneDetect] Processed %d frames in %3.1f secs (avg. %3.1f FPS).' % (
            frames_read, elapsed_time, perf_fps))
        print('[PySceneDetect] List of detected scenes:')
        if args.list_scenes:
            print ('----------------------------------------------')
            print ('    Scene #   |   Frame #                     ')
            print ('----------------------------------------------')
            for scene_idx, frame_num in enumerate(scene_list):
                print ('      %3d     |   %8d' % (scene_idx, frame_num))
            print ('----------------------------------------------')
        print('[PySceneDetect] Comma-separated timecode output:')

    # Create new list with scene cuts in milliseconds (original uses exact
    # frame numbers) based on the video's framerate.
    scene_list_msec = [(1000.0 * x) / float(video_fps) for x in scene_list]

    # Print CSV separated timecode output for use in other programs.
    print([scenedetect.timecodes.get_string(x) for x in scene_list_msec]
        .__str__()[1:-1].replace("'","").replace(' ', ''))

    # Cleanup, release all objects and close file handles.
    if args.stats_file: args.stats_file.close()
    return

