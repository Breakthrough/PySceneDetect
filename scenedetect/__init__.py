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

# PySceneDetect Library Imports
import scenedetect.platform
import scenedetect.detectors
import scenedetect.timecodes
import scenedetect.cli

# Third-Party Library Imports
import cv2
import numpy


# Used when printing the about & copyright message below.
VERSION_STRING = 'v0.3.0-beta'

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

""" % VERSION_STRING


def detect_scenes(cap, scene_list, detector_list, stats_file = None,
                  quiet_mode = False):
    """Performs scene detection based on passed video and scene detectors.

    Args:
        cap:  An open cv2.VideoCapture object that is assumed to be at the
            first frame.  Frames are read until cap.read() returns False, and
            the cap object remains open (it can be closed with cap.release()).
        scene_list:  List to append frame numbers of any detected scene cuts.
        detector_list:  List of scene detection algorithms to run on the video.
        stats_file:  Optional.  Handle to a file, open for writing, to save the
            frame metrics computed by each detection algorithm, in CSV format.

    Returns:
        Unsigned, integer number of frames read from the passed cap object.
    """
    frames_read = 0
    frame_metrics = {}
    while True:
        (rv, im) = cap.read()
        if not rv:
            break
        if not frames_read in frame_metrics:
            frame_metrics[frames_read] = dict()
        for detector in detector_list:
            detector.process_frame(frames_read, im, frame_metrics, scene_list)
        if stats_file:
            # write frame metrics to stats_file
            pass
        frames_read += 1
    [detector.post_process(scene_list) for detector in detector_list]
    return frames_read


def main():
    """Entry point for running PySceneDetect as a program.

    Handles high-level interfacing of video and scene detection / output.
    """

    # Parse CLI arguments and initialize VideoCapture object.
    scene_detectors = scenedetect.detectors.get_available()
    timecode_formats = scenedetect.timecodes.get_available()
    args = scenedetect.cli.get_cli_parser(
        scene_detectors.keys(), timecode_formats.keys()).parse_args()
    cap = cv2.VideoCapture()

    # Attempt to open the passed input (video) file.
    cap.open(args.input.name)
    if not cap.isOpened():
        if not args.quiet_mode:
            print('[PySceneDetect] FATAL ERROR - could not open video %s.' % 
                args.input.name)
        return
    elif not args.quiet_mode:
        print('[PySceneDetect] Parsing video %s...' % args.input.name)

    # Print video parameters (resolution, FPS, etc...)
    video_width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    video_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    video_fps    = cap.get(cv2.CAP_PROP_FPS)
    if not args.quiet_mode:
        print('[PySceneDetect] Video Resolution / Framerate: %d x %d / %2.3f FPS' % (
            video_width, video_height, video_fps ))

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
    if not args.quiet_mode:
        print('[PySceneDetect] Detecting scenes (%s mode)...' % detection_method)
    scene_list = list()
    frames_read = detect_scenes(cap, scene_list, [detector],
                                args.stats_file, args.quiet_mode)
    # Print scene list if requested.
    if not args.quiet_mode:
        print('[PySceneDetect] Processing complete, found %d scenes in video.' %
            len(scene_list))
        print('[PySceneDetect] List of detected scenes:')
        if args.list_scenes:
            print ('----------------------------------------------')
            print ('    Scene #   |   Frame #                     ')
            print ('----------------------------------------------')
            for scene_idx, frame_num in enumerate(scene_list):
                print ('      %3d     |   %8d' % (scene_idx, frame_num))
            print ('----------------------------------------------')
        print('[PySceneDetect] Comma-separated timecode output:')

    # Print CSV separated timecode output.
    scene_list_msec = [(1000.0 * x) / float(video_fps) for x in scene_list]
    print([scenedetect.timecodes.get_string(x) for x in scene_list_msec]
        .__str__()[1:-1].replace("'","").replace(' ', ''))

    # Cleanup, release all objects and close file handles.
    cap.release()
    if args.stats_file: args.stats_file.close()
    return

