#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains all code related to parsing command-line arguments.
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
import scenedetect


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


def string_type_check(valid_strings, case_sensitive = True, metavar = None):
    """ Creates an argparse type for a list of strings.

    The passed argument is declared valid if it is a valid string which exists
    in the passed list valid_strings.  If case_sensitive is False, all input 
    strings and strings in valid_strings are processed as lowercase.  Leading
    and trailing whitespace is ignored in all strings.

    Returns:
        A function which can be passed as an argument type, when calling
        add_argument on an ArgumentParser object

    Raises:
        ArgumentTypeError: Passed argument must be string within valid list.
    """
    if metavar == None: metavar = 'value'
    valid_strings = [x.strip() for x in valid_strings]
    if not case_sensitive:
        valid_strings = [x.lower() for x in valid_strings]
    def _type_checker(value):
        value = str(value)
        valid = True
        if not case_sensitive:
            value = value.lower()
        if not value in valid_strings:
            valid = False
            case_msg = ' (case sensitive)' if case_sensitive else ''
            msg = 'invalid choice: %s (valid settings for %s%s are: %s)' % (
                value, metavar, case_msg, valid_strings.__str__()[1:-1])
        if not valid:
            raise argparse.ArgumentTypeError(msg)
        return value
    return _type_checker


class AboutAction(argparse.Action):
    """Custom argparse action for displaying the PySceneDetect ABOUT_STRING. 

    Based off of the default VersionAction for displaying a string to the user.
    """
    def __init__(self, option_strings, version = None,
                 dest = argparse.SUPPRESS, default = argparse.SUPPRESS,
                 help = "show version number and license/copyright information"):
        super(AboutAction, self).__init__(option_strings = option_strings,
                                          dest = dest, default = default,
                                          nargs = 0, help = help)
        self.version = version

    def __call__(self, parser, namespace, values, option_string = None):
        version = self.version
        if version is None:
            version = parser.version
        parser.exit(message = version)


def get_cli_parser(scene_detectors_list, timecode_formats_list):
    """Creates the PySceneDetect argparse command-line interface.

    Returns:
        ArgumentParser object, which parse_args() can be called with.
    """
    parser = argparse.ArgumentParser(
        formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser._optionals.title = 'arguments'

    parser.add_argument(
        '-v', '--version',
        action = AboutAction, version = scenedetect.ABOUT_STRING)
    parser.add_argument(
        '-i', '--input', metavar = 'VIDEO_FILE',
        required = True, type = file,
        help = '[REQUIRED] Path to input video.')
    parser.add_argument(
        '-o', '--output', metavar = 'SCENE_LIST',
        type = argparse.FileType('w'),
        help = ('File to store detected scenes in using the specified timecode'
                'format as comma-separated values (.csv). '
                'File will be overwritten if already exists.'))
    parser.add_argument(
        '-t', '--threshold', metavar = 'intensity', dest = 'threshold',
        type = int_type_check(0, 255, 'intensity'), default = 12,
        help = ('8-bit intensity value, from 0-255, to use as the black level'
                ' in threshold detection mode, or as the change tolerance'
                ' threshold in content-aware detection mode.'))
    parser.add_argument(
        '-m', '--min-scene-length', metavar = 'NUM_FRAMES', dest = 'min_scene_len',
        type = int_type_check(1, None, 'NUM_FRAMES'), default = 15,
        help = 'Minimum length, in frames, before another scene cut can be generated.')
    parser.add_argument(
        '-p', '--min-percent', metavar = 'percent', dest = 'min_percent',
        type = int_type_check(0, 100, 'percentage'), default = 95,
        help = 'Amount of pixels in a frame, from 0-100%%, that must fall '
               'under [intensity]. Only applies to threshold detection.')
    parser.add_argument(
        '-b', '--block-size', metavar = 'rows', dest = 'block_size',
        type = int_type_check(1, None, 'number of rows'), default = 32,
        help = 'Number of rows in frame to check at once, can be tuned for '
               'performance. Only applies to threshold detection.')
    parser.add_argument(
        '-s', '--statsfile', metavar = 'STATS_FILE', dest = 'stats_file',
        type = argparse.FileType('w'),
        help = 'File to store video statistics data, comma-separated value '
               'format (.csv). Will be overwritten if exists.')
    parser.add_argument(
        '-d', '--detector', metavar = 'detection_method', dest = 'detection_method',
        type = string_type_check(scene_detectors_list, False, 'detection_method'),
        default = scenedetect.detectors.DETECTOR_DEFAULT,
        help = 'Type of scene detection method/algorithm to use; detectors available: %s.' % (
            scene_detectors_list.__str__().replace("'","")))
    #parser.add_argument(
    #    '-f', '--format-timecode', metavar = 'timecode_format', dest = 'timecode_format',
    #    type = string_type_check(timecode_formats_list, False, 'timecode_format'),
    #    default = scenedetect.timecodes.FORMAT_DEFAULT,
    #    help = 'Format to use for the output scene cut times; formats available: %s.' % (
    #        timecode_formats_list.__str__().replace("'","")))
    parser.add_argument(
        '-l', '--list-scenes', dest = 'list_scenes',
        action = 'store_true', default = False,
        help = 'Output the final scene list in human-readable format as a table, in addition to CSV.')
    parser.add_argument(
        '-q', '--quiet', dest = 'quiet_mode',
        action = 'store_true', default = False,
        help = ('Suppress all output except for final comma-separated list of scene cuts.'
                ' Useful for computing or piping output directly into other programs/scripts.'))
    #parser.add_argument(
    #    '-s', '--startindex', metavar = 'offset',
    #    type = int, default = 0,
    #    help = 'Starting index for chapter/scene output.')
    # Needs to be replaced with fade bias (-100% to +100%):
    #parser.add_argument(
    #    '-p', '--startpos', metavar = 'position',
    #    choices = [ 'in', 'mid', 'out' ], default = 'out',
    #    help = 'Where the timecode/frame number for a given scene should '
    #           'start relative to the fades [in, mid, or out].')

    return parser
