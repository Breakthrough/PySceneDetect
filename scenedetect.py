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
# Copyright (C) 2013-2014 Brandon Castellano <http://www.bcastell.com>.
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


VERSION_STRING = '0.1.0-alpha'
ABOUT_STRING   = """
PySceneDetect %s
-----------------------------------------------
http://www.bcastell.com/projects/pyscenedetect
https://github.com/Breakthrough/PySceneDetect
-----------------------------------------------
Copyright (C) 2013-2014 Brandon Castellano
License: BSD 2-Clause (see the included LICENSE file for details, or
         visit < http://www.bcastell.com/projects/pyscenedetect >).
This software uses the following third-party components:
  > NumPy    [Copyright (C) 2005-2013, Numpy Developers]
  > OpenCV   [Copyright (C) 2014, Itseez]
THE SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.

""" % VERSION_STRING


def analyze_video_threshold(cap, threshold, min_percent, block_size, show_output = True):
    """ Performs threshold analysis on video to find fades in/out of scenes.

    Args:
        cap:            An *opened* OpenCV VideoCapture object.
        threshold:      8-bit intensity threshold, from 0-255.
        min_percent:    Minimum %% of pixels that must fall under the threshold
                        to trigger a fade out (or over to trigger a fade in).
        block_size:     Number of rows to sum pixels of at once.  Can be tuned
                        for performance, depending on image size.
        show_output:    True to print updates while detecting, False otherwise.

    Returns:
        A list of tuples in the form (fade type, time, frame number) where
        fade type is 0 for fade-out and 1 for fade-in, and time/frame number
        is the position of the fade in the video, in milliseconds/frames.
    """
    print 'Performing threshold analysis (intensity %d, min %d%%)...' % (
        threshold, min_percent )

    fade_list      = []
    fade_names     = ("OUT", "IN ")
    min_percent    = min_percent / 100.0
    last_frame_amt = None

    if show_output:
        print ''
        print '----------------------------------------'
        print ' FADE TYPE |     TIME     |   FRAME #   '
        print '----------------------------------------'

    while True:
        # Get next frame from video.
        (rv, im) = cap.read()
        if not rv:   # im is a valid image if and only if rv is true
            break

        # Compute minimum number of pixels required to trigger a fade.
        curr_frame_amt   = 0    # Current number of pixels above/below the threshold.
        curr_frame_row   = 0    # Current row offset in frame being processed.
        num_pixel_values = float(im.shape[0] * im.shape[1] * im.shape[2])
        min_pixels       = int(num_pixel_values * (1.0 - min_percent))

        while curr_frame_row < im.shape[0]:
            curr_frame_amt += numpy.sum(
                im[curr_frame_row : curr_frame_row + block_size,:,:] > threshold )
            if curr_frame_amt > min_pixels:
                break
            curr_frame_row += block_size

        if last_frame_amt == None:
            last_frame_amt = curr_frame_amt
            continue

        fade_type = None

        # Detect fade out to black.
        if curr_frame_amt < min_pixels and last_frame_amt >= min_pixels:
            fade_type = 0
        # Detect fade in from black.
        elif curr_frame_amt >= min_pixels and last_frame_amt < min_pixels:
            fade_type = 1

        if not fade_type == None:
            pos_msec   = cap.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
            pos_frames = cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)
            fade_list.append((fade_type, pos_msec, pos_frames))
            if show_output:
                print "  %s      | %9d ms | %10d" % (
                    fade_names[fade_type], pos_msec, pos_frames )

        last_frame_amt = curr_frame_amt

    if show_output:
        print '-----------------------------------------'
        print ''

    return fade_list


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
    def _type_check(value):
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
    return _type_check


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
    parser.add_argument('-t', '--threshold',  metavar = 'intensity',
        type = int_type_check(0, 255, 'intensity'), default = 8,
        help = '8-bit intensity value, from 0-255, to use as a fade in/out detection threshold.')
    parser.add_argument('-m', '--minpercent', metavar = 'percent',
        type = int_type_check(0, 100, 'percentage'), default = 95,
        help = 'Amount of pixels in a frame, from 0-100%%, that must fall under [intensity].')
    parser.add_argument('-b', '--blocksize',  metavar = 'rows',
        type = int_type_check(1, None, 'number of rows'), default = 32,
        help = 'Number of rows in frame to check at once, can be tuned for performance.')
    parser.add_argument('-s', '--startindex', metavar = 'offset',
        type = int, default = 0,
        help = 'Starting index for chapter/scene output.')
    parser.add_argument('-p', '--startpos', metavar = 'position',
        choices = [ 'in', 'mid', 'out' ], default = 'out',
        help = 'Where the timecode/frame number for a given scene should start relative to the fades [in, mid, or out].')

    return parser


def main():
    """ Program entry point.

    Handles high-level interfacing of video and scene detection / output.
    """
    # Get command line arguments directly from the CLI parser defined above.
    args = get_cli_parser().parse_args()
    # Attempt to open the passed video file as an OpenCV VideoCapture object.
    cap = cv2.VideoCapture()
    cap.open(args.input.name)
    if not cap.isOpened():
        print 'FATAL ERROR - could not open video %s.' % args.input.name
        print 'cap.isOpened() is not True after calling cap.open(..)'
        return
    else:
        print ''
        print 'Parsing video %s...' % args.input.name

    # Print video parameters (resolution, FPS, etc...)
    video_width  = cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)
    video_height = cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)
    video_fps    = cap.get(cv2.cv.CV_CAP_PROP_FPS)
    print "Video Resolution / Framerate: %d x %d / %2.3f FPS" % (
        video_width, video_height, video_fps )

    start_time = cv2.getTickCount()  # Record the time we started processing.

    # Perform threshold analysis on video, get list of fades in/out.
    fade_list = analyze_video_threshold( cap,
        args.threshold, args.minpercent, args.blocksize )

    # Get # of frames based on position of last frame we read.
    frame_count = cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)

    # Compute & display number of frames, runtime, and average framerate.
    total_runtime = float(cv2.getTickCount() - start_time) / cv2.getTickFrequency()
    avg_framerate = float(frame_count) / total_runtime
    print "Read %d frames in %4.2f seconds (avg. %4.1f FPS)." % (
        frame_count, total_runtime, avg_framerate )

    #
    cap.release()
    print ""


if __name__ == "__main__":
    main()

