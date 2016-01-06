#!/usr/bin/env python
#
#         PySceneDetect: Python-Based Video Scene Detector
#    -----------------------------------------------------------
#        [ http://www.bcastell.com/projects/pyscenedetect/ ]
#        [ https://github.com/Breakthrough/PySceneDetect/  ]
#
# This program implements an optimized threshold-based scene detection
# algorithm, generating a list of scene/chapter timecodes (or frame)
# numbers), which can be used to split the video with an external tool
# (e.g. ffmpeg, mkvmerge) into sequential parts.  Usage:
#
#   ./scenedetect.py [-h] -i VIDEO_FILE [optional args]
#
# Where -i denotes the input video, and -h shows the help message (as
# well as a list of optional arguments and descriptions).
#
#
# Copyright (C) 2013-2015 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit the following page for details:
# http://www.bcastell.com/projects/pyscenedetect
#
# This software uses Numpy and OpenCV; see the LICENSE-NUMPY and
# LICENSE-OPENCV files for details, or visit the above URL.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

import sys
import argparse

import cv2
import numpy


VERSION_STRING = '0.3-beta-dev'
ABOUT_STRING   = """
PySceneDetect %s
-----------------------------------------------
http://www.bcastell.com/projects/pyscenedetect
https://github.com/Breakthrough/PySceneDetect
-----------------------------------------------
Copyright (C) 2013-2016 Brandon Castellano
License: BSD 2-Clause (see the included LICENSE file for details, or
         visit < http://www.bcastell.com/projects/pyscenedetect >).
This software uses the following third-party components:
  > NumPy    [Copyright (C) 2005-2013, Numpy Developers]
  > OpenCV   [Copyright (C) 2016, Itseez]
THE SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.

""" % VERSION_STRING


# Compatibility fix for OpenCV < 3.0
if (cv2.__version__[0] == '2') or (not cv2.__version__[0] == '3'):
    cv2.CAP_PROP_FRAME_WIDTH = cv2.cv.CV_CAP_PROP_FRAME_WIDTH
    cv2.CAP_PROP_FRAME_HEIGHT = cv2.cv.CV_CAP_PROP_FRAME_HEIGHT
    cv2.CAP_PROP_FPS = cv2.cv.CV_CAP_PROP_FPS
    cv2.CAP_PROP_POS_MSEC = cv2.cv.CV_CAP_PROP_POS_MSEC
    cv2.CAP_PROP_POS_FRAMES = cv2.cv.CV_CAP_PROP_POS_FRAMES
    cv2.CAP_PROP_FRAME_COUNT = cv2.cv.CV_CAP_PROP_FRAME_COUNT


class SceneDetector(object):
    """Base SceneDetector class to implement a scene detection algorithm."""
    def __init__(self):
        pass


    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        """Computes/stores metrics and detects any scene changes."""

        # Prototype method, no actual detection.
        return


    def post_process(self, scene_list):
        pass


class ThresholdDetector(SceneDetector):
    """Detects fast cuts/slow fades in from and out to a given threshold level.

    Detects both fast cuts and slow fades so long as an appropriate threshold
    is chosen (especially taking into account the minimum grey/black level).
    """

## Development Notes:
#
# Three types of 'cuts':  Scene CUT, IN, OUT
#  -> technically only need CUT/IN, but what about fade bias?
#  -> thus have each detector return a CUT, FADE_IN, or FADE_OUT
#  -> allow fade bias to have 3 values - 'in', 'out', 'mid'
#     so say fade out at 1s, fade in at 2s:
#       for in, scene starts at @ 1s;  1.5s for mid;  2s for out
#
#  Logic for each case for FADES:
#    -> start above threshold, Scene 1 starts at 0s (video_start)
#    -> start below threshold, Scene 0 at 0s, Scene 1, bias between 0s and fade_in
#    -> end below threshold, Scene N+1, bias new scene between fade_out and video_end
#    -> end above threshold, Scene N
##

    def __init__(self, threshold = 12):
        super(ThresholdDetector, self).__init__()
        self.threshold = threshold
        self.fade_bias = 0.0
        self.last_frame_avg = None
        # Where the last fade (threshold crossing) was detected.
        self.last_fade = { 
            'frame': 0,         # frame number where the last detected fade is
            'type': None        # type of fade, can be either 'in' or 'out'
          }
        return

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        # Compare average intensity of current_frame and last_frame.
        # If absolute value of pixel intensity delta is above the threshold,
        # then we trigger a new scene.
        frame_avg = 0.0
        if frame_num in frame_metrics and 'frame_avg_rgb' in frame_metrics[frame_num]:
            frame_avg = frame_metrics[frame_num]['frame_avg_rgb']
        else:
            num_pixel_values = frame_img.shape[0] * frame_img.shape[1] * frame_img.shape[2]
            frame_avg = numpy.sum(frame_img[:,:,:]) / float(num_pixel_values)
            frame_metrics[frame_num]['frame_avg_rgb'] = frame_avg_rgb

        if self.last_frame_avg is not None:
            if self.last_fade['type'] == 'in' and frame_avg <= self.threshold:
                # Just faded out of a scene, wait for next fade in.
                self.last_fade['type'] = 'out'
                self.last_fade['frame'] = frame_num
            elif self.last_fade['type'] == 'out' and frame_avg > self.threshold:
                # Just faded into a new scene, compute timecode for the scene
                # split based on the fade bias.
                f_in = frame_num
                f_out = self.last_fade['frame']
                f_split = int((f_in + f_out + int(b * (f_in - f_out))) / 2)
                scene_list.append(f_split)
                self.last_fade['type'] = 'in'
                self.last_fade['frame'] = frame_num
        else:
            self.last_fade['frame'] = 0
            if frame_avg <= self.threshold:
                self.last_fade['type'] = 'out'
            else:
                self.last_fade['type'] = 'in'
        # Before returning, we keep track of the last frame average (can also
        # be used to compute fades independently of the last fade type).
        self.last_frame_avg = frame_avg
        return

    def post_process(self, scene_list):
        # If the last fade detected was a fade out, we add a corresponding new
        # scene break to indicate the end of the scene.  This is only done for
        # a fade out as scene breaks are computed during the scene's fade in.
        if self.last_fade['type'] = 'out':
            scene_list.append(self.last_fade['frame'])
        return



class HSVDetector(SceneDetector):
    """Detects fast cuts using changes in colour and intensity between frames.

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.  To detect slow fades between
    content scenes still using HSV information, use the DissolveDetector.
    """

    def __init__(self):
        super(HSVDetector, self).__init__()
        self.last_frame = None

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        # Similar to ThresholdDetector, but using the HSV colour space DIFFERENCE instead
        # of single-frame RGB/grayscale intensity (thus cannot detect slow fades with this method).
        frame_delta = 0.0

        if frame_num in frame_metrics and 'delta_hsv' in frame_metrics[frame_num]:
            frame_delta = frame_metrics[frame_num]['delta_hsv']
            pass
 
        elif self.last_frame is not None:
            frame_delta = numpy.sum( \
                numpy.abs(frame_img.astype(numpy.int32) - self.last_frame.astype(numpy.int32)) )
            frame_metrics[frame_num]['frame_delta'] = frame_delta
            pass

        self.last_frame.release()
        self.last_frame = frame_img.clone()
        return


class EdgeDetector(SceneDetector):
    """Detects fast cuts/slow fades by using edge detection on adjacent frames.

    Detects both fast cuts and slow fades, although some parameters may need to
    be modified for accurate slow fade detection.
    """
    def __init__(self):
        super(EdgeDetector, self).__init__()
        self.last_result = None

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        # Uses a high-pass filter to compare the current and last frames
        # to detect changes to the scene's contents.
        return


class DissolveDetector(SceneDetector):
    """Detects slow fades (dissolve cuts) via changes in the HSV colour space.

    Detects slow fades only; to detect fast cuts between content scenes, the
    HSVDetector should be used instead.
    """

    def __init__(self):
        super(DissolveDetector, self).__init__()
        self.last_result = None


    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        return


#
#  Ignore Cuts - Let the detector handle that.
#                Can use a lastframe flag/method to assist implementation.

#
#  When reading from the statsfile:
#    -> read only, but if needs updating, need to generate new statsfile
#    -> make new with .new on end, rename & delete old when done
#    -> keep frame metrics in memory for all frames incase of discrepency?
#       or just recompute and restore the statsfile each time (to check for accuracy)?
#
#
#


def get_timecode_string(time_msec, show_msec = True):
    """ Formats a time, in ms, into a timecode of the form HH:MM:SS.nnnnn.

    This is the default timecode format used by mkvmerge for splitting a video.

    Args:
        time_msec:      Integer representing milliseconds from start of video.
        show_msec:      If False, omits the milliseconds part from the output.
    Returns:
        A string with a formatted timecode (HH:MM:SS.nnnnn).
    """
    out_nn, timecode_str = int(time_msec), ''

    base_msec = 1000 * 60 * 60  # 1 hour in ms
    out_HH = int(out_nn / base_msec)
    out_nn -= out_HH * base_msec

    base_msec = 1000 * 60       # 1 minute in ms
    out_MM = int(out_nn / base_msec)
    out_nn -= out_MM * base_msec

    base_msec = 1000            # 1 second in ms
    out_SS = int(out_nn / base_msec)
    out_nn -= out_SS * base_msec

    if show_msec:
        timecode_str = "%02d:%02d:%02d.%d" % (out_HH, out_MM, out_SS, out_nn)
    else:
        timecode_str = "%02d:%02d:%02d" % (out_HH, out_MM, out_SS)

    return timecode_str


def int_type_check(min_val, max_val = None, metavar = None):
    """ Creates an argparse type for a range-limited integer.

    The passed argument is declared valid if it is a valid integer which
    is greater than or equal to min_val, and if max_val is specified,
    less than or equal to max_val.

    Returns:
        A function which can be passed as an argument type, when calling
        add_argument on an ArgumentParser object

    Raises:
        ArgumentTypeError: Passed argument must be integer within proper range.
    """
    if metavar == None: metavar = 'value'
    def _type_checker(value):
        value = int(value)
        valid = True
        msg   = ''
        if (max_val == None):
            if (value < min_val): valid = False
            msg = 'invalid choice: %d (%s must be at least %d)' % (
                value, metavar, min_val )
        else:
            if (value < min_val or value > max_val): valid = False
            msg = 'invalid choice: %d (%s must be between %d and %d)' % (
                value, metavar, min_val, max_val )
        if not valid:
            raise argparse.ArgumentTypeError(msg)
        return value
    return _type_checker


class AboutAction(argparse.Action):
    """ Custom argparse action for displaying raw About string. 

    Based off of argparse's default VersionAction.
    """
    def __init__( self, option_strings, version = None,
                  dest = argparse.SUPPRESS, default = argparse.SUPPRESS,
                  help = "show version number and license/copyright information"):
        super(AboutAction, self).__init__( option_strings = option_strings,
            dest = dest, default = default, nargs = 0, help = help )
        self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        parser.exit(message = version)


def get_cli_parser():
    """ Creates the PySceneDetect argparse command-line interface.

    Returns:
        An ArgumentParser object, with which parse_args() can be called.
    """
    parser = argparse.ArgumentParser(
        formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser._optionals.title = 'arguments'

    parser.add_argument('-v', '--version',
        action = AboutAction, version = ABOUT_STRING)
    parser.add_argument('-i', '--input', metavar = 'VIDEO_FILE',
        type = file, required = True,
        help = '[REQUIRED] Path to input video.')
    parser.add_argument('-o', '--output', metavar = 'SCENE_LIST',
        type = argparse.FileType('w'),
        help = 'File to store detected scenes in; comma-separated value format (.csv). Will be overwritten if exists.')
    parser.add_argument('-t', '--threshold', metavar = 'intensity',
        type = int_type_check(0, 255, 'intensity'), default = 8,
        help = '8-bit intensity value, from 0-255, to use as a fade in/out detection threshold.')
    parser.add_argument('-m', '--minpercent', metavar = 'percent',
        type = int_type_check(0, 100, 'percentage'), default = 95,
        help = 'Amount of pixels in a frame, from 0-100%%, that must fall under [intensity].')
    parser.add_argument('-b', '--blocksize', metavar = 'rows',
        type = int_type_check(1, None, 'number of rows'), default = 32,
        help = 'Number of rows in frame to check at once, can be tuned for performance.')
    parser.add_argument('-s', '--statsfile', metavar = 'STATS_FILE',
        type = argparse.FileType('w'),
        help = 'File to store video statistics data, comma-separated value format (.csv). Will be overwritten if exists.')
    #parser.add_argument('-s', '--startindex', metavar = 'offset',
    #    type = int, default = 0,
    #    help = 'Starting index for chapter/scene output.')
    #parser.add_argument('-p', '--startpos', metavar = 'position',
    #    choices = [ 'in', 'mid', 'out' ], default = 'out',
    #    help = 'Where the timecode/frame number for a given scene should start relative to the fades [in, mid, or out].')

    return parser



def main():
    """ Program entry point.

    Handles high-level interfacing of video and scene detection / output.
    """

    # Parse CLI arguments and initialize VideoCapture object.
    args = get_cli_parser().parse_args()
    cap = cv2.VideoCapture()

    # Attempt to open the passed input (video) file.
    cap.open(args.input.name)
    if not cap.isOpened():
        print 'FATAL ERROR - could not open video %s.' % args.input.name
        print 'cap.isOpened() is not True after calling cap.open(..)'
        return
    else:
        print 'Parsing video %s...' % args.input.name

    cv_frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

    frames_read = 0
    cap_closed = False

    for f in xrange(cv_frame_count):

        # Check if metrics required are computed first, store in a CSV.
        # Load as a dict, pass to parsing functions.
        # Read each frame even if stats exist, just don't process.


        (rv, im) = cap.read()
        if not rv:
            cap_closed = True
            break
        frames_read += 1
        # process frame

    # Handle any errors in frames read.
    if frames_read < cv_frame_count:
        print 'Error - not all frames could be read from video.'
    elif not cap_closed:
        # continue parsing frames.
        while True:
            (rv, im) = cap.read()
            if not rv:
                cap_closed = True
                break
            frames_read += 1
            # process frame


    # Cleanup, release all objects and close file handles.
    cap.release()


if __name__ == '__main__':
    main()
    print ''


