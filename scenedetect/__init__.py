#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains all code for the main `scenedetect` module. 
#
# Copyright (C) 2012-2017 Brandon Castellano <http://www.bcastell.com>.
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
import os
import argparse
import time
import csv
import subprocess

# PySceneDetect Library Imports
import scenedetect.platform
import scenedetect.detectors
import scenedetect.timecodes
import scenedetect.manager
import scenedetect.cli

# Third-Party Library Imports
import cv2
import numpy


# Used for module identification and when printing copyright & version info.
__version__ = 'v0.4'

# About & copyright message string shown for the -v / --version CLI argument.
ABOUT_STRING   = """----------------------------------------------------
PySceneDetect %s
----------------------------------------------------
Site/Updates: https://github.com/Breakthrough/PySceneDetect/
Documentation: http://pyscenedetect.readthedocs.org/

Copyright (C) 2012-2017 Brandon Castellano. All rights reserved.

PySceneDetect is released under the BSD 2-Clause license. See the
included LICENSE file or visit the PySceneDetect website for details.
This software uses the following third-party components:
  > NumPy [Copyright (C) 2005-2016, Numpy Developers]
  > OpenCV [Copyright (C) 2017, Itseez]
  > mkvmerge [Copyright (C) 2005-2016, Matroska]
THE SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
""" % __version__


def detect_scenes_file(path, scene_manager):
    """Performs scene detection on passed file using given scene detectors.

    Essentially wraps detect_scenes() while handling all OpenCV interaction.
    For descriptions of arguments and return values that are just passed to
    this function, see the detect_scenes() documentation directly.

    Args:
        path:  A string containing the filename of the video to open.
        scene_manager:  SceneManager interface to scene/detector list and other
            parts of the application state (including user-defined options).

    Returns:
        Tuple containing (video_fps, frames_read, frames_processed), where
        video_fps is a float of the video file's framerate, frames_read is a
        positive, integer number of frames read from the video file, and
        frames_processed is the actual number of frames used.  All values
        are set to -1 if the file could not be opened.
    """

    cap = cv2.VideoCapture()
    frames_read = -1
    frames_processed = -1
    video_fps = -1
    if not scene_manager.timecode_list:
        scene_manager.timecode_list = [0, 0, 0]

    # Attempt to open the passed input (video) file.
    cap.open(path)
    file_name = os.path.split(path)[1]
    if not cap.isOpened():
        if not scene_manager.quiet_mode:
            print('[PySceneDetect] FATAL ERROR - could not open video %s.' % path)
        return (video_fps, frames_read)
    elif not scene_manager.quiet_mode:
        print('[PySceneDetect] Parsing video %s...' % file_name)

    # Print video parameters (resolution, FPS, etc...)
    video_width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    video_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    video_fps    = cap.get(cv2.CAP_PROP_FPS)
    if not scene_manager.quiet_mode:
        print('[PySceneDetect] Video Resolution / Framerate: %d x %d / %2.3f FPS' % (
            video_width, video_height, video_fps))
        if scene_manager.downscale_factor >= 2:
            print('[PySceneDetect] Subsampling Enabled (%dx, Resolution = %d x %d)' % (
                scene_manager.downscale_factor,
                video_width / scene_manager.downscale_factor,
                video_height / scene_manager.downscale_factor))
        print('Verify that the above parameters are correct'
              ' (especially framerate, use --force-fps to correct if required).')

    # Convert timecode_list to absolute frames for detect_scenes() function.
    frames_list = []
    for timecode in scene_manager.timecode_list:
        if isinstance(timecode, int):
            frames_list.append(timecode)
        elif isinstance(timecode, float):
            frames_list.append(int(timecode * video_fps))
        elif isinstance(timecode, list) and len(timecode) == 3:
            secs = float(timecode[0] * 60 * 60) + float(timecode[1] * 60) + float(timecode[2])
            frames_list.append(int(secs * video_fps))
        else:
            frames_list.append(0)

    start_frame, end_frame, duration_frames = 0, 0, 0
    if len(frames_list) == 3:
        start_frame, end_frame, duration_frames = (
            frames_list[0], frames_list[1], frames_list[2])

    # Perform scene detection on cap object (modifies scene_list).
    frames_read, frames_processed = detect_scenes(
        cap, scene_manager, file_name, start_frame, end_frame, duration_frames)

    # Cleanup and return number of frames we read/processed.
    cap.release()
    return (video_fps, frames_read, frames_processed)


def detect_scenes(cap, scene_manager, image_path_prefix = '', start_frame = 0,
                  end_frame = 0, duration_frames = 0):
    """Performs scene detection based on passed video and scene detectors.

    Args:
        cap:  An open cv2.VideoCapture object that is assumed to be at the
            first frame.  Frames are read until cap.read() returns False, and
            the cap object remains open (it can be closed with cap.release()).
        scene_manager:  SceneManager interface to scene/detector list and other
            parts of the application state (including user-defined options).
        image_path_prefix:  Optional.  Filename/path to write images to.
        start_frame:  Optional.  Integer frame number to start processing at.
        end_frame:  Optional.  Integer frame number to stop processing at.
        duration_frames:  Optional.  Integer number of frames to process;
            overrides end_frame if the two values are conflicting.

    Returns:
        Tuple of integers of number of frames read, and number of frames
        actually processed/used for scene detection.
    """
    frames_read = 0
    frames_processed = 0
    frame_metrics = {}
    last_frame = None       # Holds previous frame if needed for save_images.

    perf_show = True
    perf_last_update_time = time.time()
    perf_last_framecount = 0
    perf_curr_rate = 0
    if scene_manager.perf_update_rate > 0:
        perf_update_rate = float(scene_manager.perf_update_rate)
    else:
        perf_show = False

    # set the end frame if duration_frames is set (overrides end_frame if set)
    if duration_frames > 0:
        end_frame = start_frame + duration_frames

    # If start_frame is set, we drop the required number of frames first.
    # (seeking doesn't work very well, if at all, with OpenCV...)
    while (frames_read < start_frame):
        ret_val = cap.grab()
        frames_read += 1

    stats_file_keys = []
    video_fps = cap.get(cv2.CAP_PROP_FPS)

    while True:
        # If we passed the end point, we stop processing now.
        if end_frame > 0 and frames_read >= end_frame:
            break

        # If frameskip is set, we drop the required number of frames first.
        if scene_manager.frame_skip > 0:
            for _ in range(scene_manager.frame_skip):
                ret_val = cap.grab()
                if not ret_val:
                    break
                frames_read += 1

        (ret_val, im_cap) = cap.read()
        if not ret_val:
            break
        if not frames_read in frame_metrics:
            frame_metrics[frames_read] = dict()
        im_scaled = im_cap
        if scene_manager.downscale_factor > 0:
            im_scaled = im_cap[::scene_manager.downscale_factor,::scene_manager.downscale_factor,:]
        cut_found = False
        for detector in scene_manager.detector_list:
            cut_found = detector.process_frame(frames_read, im_scaled,
                frame_metrics, scene_manager.scene_list) or cut_found
        if scene_manager.stats_writer:
            if not len(stats_file_keys) > 0:
                stats_file_keys = frame_metrics[frames_read].keys()
                if len(stats_file_keys) > 0:
                    scene_manager.stats_writer.writerow(
                        ['Frame Number'] + ['Timecode'] + stats_file_keys)
            if len(stats_file_keys) > 0:
                scene_manager.stats_writer.writerow(
                    [str(frames_read)] +
                    [scenedetect.timecodes.frame_to_timecode(frames_read, video_fps)] +
                    [str(frame_metrics[frames_read][metric]) for metric in stats_file_keys])
        frames_read += 1
        frames_processed += 1
        # periodically show processing speed/performance if requested
        if not scene_manager.quiet_mode and perf_show:
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
        # save images on scene cuts/breaks if requested (scaled if using -df)
        if scene_manager.save_images and cut_found:
            save_preview_images(
                image_path_prefix, im_cap, last_frame, len(scene_manager.scene_list))

        del last_frame
        last_frame = im_cap.copy()
    # perform any post-processing required by the detectors being used
    for detector in scene_manager.detector_list:
        detector.post_process(scene_manager.scene_list)

    if start_frame > 0:
        frames_read = frames_read - start_frame
    return (frames_read, frames_processed)


def save_preview_images(image_path_prefix, im_curr, im_last, num_scenes):
    """Called when a scene break occurs to save an image of the frames.

    Args:
        image_path_prefix: Prefix to include in image path.
        im_curr: The current frame image for the first frame in the new scene.
        im_last: The last frame of the previous scene.
        num_scenes: The index of the current/new scene (the IN frame).
    """
    # Save the last/previous frame, or the OUT frame of the last scene.
    output_name = '%s.Scene-%d-OUT.jpg' % (image_path_prefix, num_scenes)
    cv2.imwrite(output_name, im_last)
    # Save the current frame, or the IN frame of the new scene.
    output_name = '%s.Scene-%d-IN.jpg' % (image_path_prefix, num_scenes+1)
    cv2.imwrite(output_name, im_curr)


def main():
    """Entry point for running PySceneDetect as a program.

    Handles high-level interfacing of video and scene detection / output.
    """

    # Load available detection modes and timecode formats.
    scene_detectors = scenedetect.detectors.get_available()
    timecode_formats = scenedetect.timecodes.get_available()
    # Parse CLI arguments.
    args = scenedetect.cli.get_cli_parser(
        scene_detectors.keys(), timecode_formats.keys()).parse_args()
    # Use above to initialize scene manager.
    smgr = scenedetect.manager.SceneManager(args, scene_detectors)

    # Perform scene detection using specified mode.
    start_time = time.time()
    if not args.quiet_mode:
        print('[PySceneDetect] Detecting scenes (%s mode)...' % smgr.detection_method)
    video_fps, frames_read, frames_processed = detect_scenes_file(
        path = args.input.name, scene_manager = smgr)
    elapsed_time = time.time() - start_time
    perf_fps = float(frames_read) / elapsed_time

    # Create new list with scene cuts in milliseconds (original uses exact
    # frame numbers) based on the video's framerate, and then timecodes.
    scene_list_msec = [(1000.0 * x) / float(video_fps) for x in smgr.scene_list]
    scene_list_tc = [scenedetect.timecodes.get_string(x) for x in scene_list_msec]
    # Create new lists with scene cuts in seconds, and the length of each scene.
    scene_start_sec = [(1.0 * x) / float(video_fps) for x in smgr.scene_list]
    scene_len_sec = []
    if len(smgr.scene_list) > 0:
        scene_len_sec = smgr.scene_list + [frames_read]
        scene_len_sec = [(1.0 * x) / float(video_fps) for x in scene_len_sec]
        scene_len_sec = [(y - x) for x, y in zip(scene_len_sec[:-1], scene_len_sec[1:])]

    if frames_read >= 0:
        # Print performance (average framerate), and scene list if requested.
        if not args.quiet_mode:
            print('[PySceneDetect] Processing complete, found %d scenes in video.' % (
                len(smgr.scene_list)))
            print('[PySceneDetect] Processed %d / %d frames read in %3.1f secs (avg %3.1f FPS).' % (
                frames_processed, frames_read, elapsed_time, perf_fps))
            if len(smgr.scene_list) > 0:
                if args.list_scenes:
                    print('[PySceneDetect] List of detected scenes:')
                    print ('-------------------------------------------')
                    print ('  Scene #  |   Frame #   |    Timecode ')
                    print ('-------------------------------------------')
                    for scene_idx, frame_num in enumerate(smgr.scene_list):
                        print ('    %3d    |  %9d  |  %s' % (
                            scene_idx+1, frame_num, scene_list_tc[scene_idx]))
                    print ('-------------------------------------------')
                print('[PySceneDetect] Comma-separated timecode output:')

        # Print CSV separated timecode output for use in other programs.
        timecode_list_str = ','.join(scene_list_tc)
        print(timecode_list_str)

        # Output CSV file containing timecode string and list of scene timecodes.
        if args.csv_out:
            output_scene_list(args.csv_out, smgr, scene_list_tc,
                              scene_start_sec, scene_len_sec)

        if args.output and len(smgr.scene_list) > 0:
            split_input_video(args.input.name, args.output, timecode_list_str)
    # Cleanup, release all objects and close file handles.
    if args.stats_file:
        args.stats_file.close()
    if args.csv_out:
        args.csv_out.close()
    return


def split_input_video(input_path, output_path, timecode_list_str):
    """ Calls the mkvmerge command on the input video, splitting it at the
    passed timecodes, where each scene is written in sequence from 001."""
    #args.output.close()
    print('[PySceneDetect] Splitting video into clips...')
    ret_val = None
    try:
        ret_val = subprocess.call(
            ['mkvmerge',
             '-o', output_path,
             '--split', 'timecodes:%s' % timecode_list_str,
             input_path])
    except FileNotFoundError:
        print('[PySceneDetect] Error: mkvmerge could not be found on the system.'
              ' Please install mkvmerge to enable video output support.')
    if ret_val is not None:
        if ret_val != 0:
            print('[PySceneDetect] Error splitting video '
                  '(mkvmerge returned %d).' % ret_val)
        else:
            print('[PySceneDetect] Finished writing scenes to output.')


def output_scene_list(csv_file, smgr, scene_list_tc, scene_start_sec,
                      scene_len_sec):
    ''' Outputs the list of scenes in human-readable format to a CSV file
        for further analysis. '''
    # Output timecodes to CSV file if required (and scenes were found).
    #if args.output and len(smgr.scene_list) > 0:
    if csv_file and len(smgr.scene_list) > 0:
        csv_writer = csv.writer(csv_file) #args.output)
        # Output timecode scene list
        csv_writer.writerow(scene_list_tc)
        # Output detailed, human-readable scene list.
        csv_writer.writerow(["Scene Number", "Frame Number (Start)",
                             "Timecode", "Start Time (seconds)", "Length (seconds)"])
        for i, _ in enumerate(smgr.scene_list):
            csv_writer.writerow([str(i+1), str(smgr.scene_list[i]),
                                 scene_list_tc[i], str(scene_start_sec[i]),
                                 str(scene_len_sec[i])])
