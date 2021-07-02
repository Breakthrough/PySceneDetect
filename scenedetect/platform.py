# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2021 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" ``scenedetect.platform`` Module

This file contains all platform/library/OS-specific compatibility fixes,
intended to improve the systems that are able to run PySceneDetect, and allow
for maintaining backwards compatibility with existing libraries going forwards.
Other helper functions related to the detection of the appropriate dependency
DLLs on Windows and getting uniform line-terminating csv reader/writer objects
are also included in this module.

With respect to the Python standard library itself and Python 2 versus 3,
this module adds compatibility wrappers for Python's Queue/queue (Python 2/3,
respectively) as scenedetect.platform.queue.

For OpenCV 2.x, the scenedetect.platform module also makes a copy of the
OpenCV VideoCapture property constants from the cv2.cv namespace directly
to the cv2 namespace.  This ensures that the cv2 API is consistent
with those changes made to it in OpenCV 3.0 and above.

This module also includes an alias for the unicode/string types in Python 2/3
as STRING_TYPE intended to help with parsing string types from the CLI parser.
"""

# Standard Library Imports
from __future__ import print_function

import csv
import os
import os.path
import platform
import struct
import subprocess
import sys

# Third-Party Library Imports
import cv2


# pylint: disable=unused-import
# pylint: disable=no-member

##
## tqdm Library (scenedetect.platform.tqdm will be tqdm object or None)
##

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# pylint: enable=unused-import


##
## click/Command-Line Interface String Type
##

# String type (used to allow FrameTimecode object to take both unicode and native
# string objects when being constructed via scenedetect.platform.STRING_TYPE).
# pylint: disable=invalid-name, undefined-variable
if sys.version_info[0] == 2:
    STRING_TYPE = unicode
else:
    STRING_TYPE = str
# pylint: enable=invalid-name, undefined-variable


# Compatibility fix for OpenCV v2.x (copies CAP_PROP_* properties from the
# cv2.cv namespace to the cv2 namespace, as the cv2.cv namespace was removed
# with the release of OpenCV 3.0).
if not 'CAP_PROP_FPS' in dir(cv2):
    cv2.CAP_PROP_FRAME_WIDTH = cv2.cv.CV_CAP_PROP_FRAME_WIDTH
    cv2.CAP_PROP_FRAME_HEIGHT = cv2.cv.CV_CAP_PROP_FRAME_HEIGHT
    cv2.CAP_PROP_FPS = cv2.cv.CV_CAP_PROP_FPS
    cv2.CAP_PROP_POS_MSEC = cv2.cv.CV_CAP_PROP_POS_MSEC
    cv2.CAP_PROP_POS_FRAMES = cv2.cv.CV_CAP_PROP_POS_FRAMES
    cv2.CAP_PROP_FRAME_COUNT = cv2.cv.CV_CAP_PROP_FRAME_COUNT
    cv2.INTER_CUBIC = cv2.cv.INTER_CUBIC


def get_aspect_ratio(cap, epsilon=0.01):
    # type: (cv2.VideoCapture, float) -> float
    """ Compatibility fix for OpenCV < v3.4.1 to get the aspect ratio
    of a video. For older versions, this function always returns 1.0.

    Argument:
        cap: cv2.VideoCapture object. Must be opened and in valid state.
        epsilon: Used to compare numerator/denominator to zero.

    Returns:
        float: Display aspect ratio CAP_PROP_SAR_NUM / CAP_PROP_SAR_DEN,
        or 1.0 if using a version of OpenCV < 3.4.1.  Also returns 1.0
        if for some reason the numerator/denominator returned is zero
        (can happen if the video was not opened correctly).
    """
    if not 'CAP_PROP_SAR_NUM' in dir(cv2):
        return 1.0
    num = cap.get(cv2.CAP_PROP_SAR_NUM)
    den = cap.get(cv2.CAP_PROP_SAR_DEN)
    # If numerator or denominator are zero, fall back to 1.0 aspect ratio.
    if abs(num) < epsilon or abs(den) < epsilon:
        return 1.0
    return num / den


##
## OpenCV DLL Check Function (Windows Only)
##

def check_opencv_ffmpeg_dll():
    # type: () -> Tuple[bool, str]
    """ Check OpenCV FFmpeg DLL: Checks if OpenCV video I/O support is available,
    on Windows only, by checking for the appropriate opencv_ffmpeg*.dll file.

    On non-Windows systems always returns True, or for OpenCV versions that do
    not follow the X.Y.Z version numbering pattern. Thus there may be false
    positives (True) with this function, but not false negatives (False).
    In those cases, PySceneDetect will report that it could not open the
    video file, and for Windows users, also gives an additional warning message
    that the error may be due to the missing DLL file.

    Returns:
        (True, DLL_NAME) if OpenCV video support is detected (e.g. the appropriate
        opencv_ffmpegXYZ.dll file is in PATH), (False, DLL_NAME) otherwise,
        where DLL_NAME is the name of the expected DLL file that OpenCV requires.
        On Non-Windows platforms, DLL_NAME will be a blank string.
    """
    if platform.system() == 'Windows' and (
            cv2.__version__[0].isdigit() and cv2.__version__.find('.') > 0):
        is_64_bit_str = '_64' if struct.calcsize("P") == 8 else ''
        dll_filename = 'opencv_ffmpeg{OPENCV_VERSION}{IS_64_BIT}.dll'.format(
            OPENCV_VERSION=cv2.__version__.replace('.', ''),
            IS_64_BIT=is_64_bit_str)
        return any([os.path.exists(os.path.join(path_path, dll_filename))
                    for path_path in os.environ['PATH'].split(';')]), dll_filename
    return True, ''


##
## OpenCV imwrite Supported Image Types & Quality/Compression Parameters
##

def _get_cv2_param(param_name):
    # type: (str) -> Union[int, None]
    if param_name.startswith('CV_'):
        param_name = param_name[3:]
    try:
        return getattr(cv2, param_name)
    except AttributeError:
        return None


def get_cv2_imwrite_params():
    # type: () -> Dict[str, Union[int, None]]
    """ Get OpenCV imwrite Params: Returns a dict of supported image formats and
    their associated quality/compression parameter.

    Returns:
        (Dict[str, int]) Dictionary of image formats/extensions ('jpg',
            'png', etc...) mapped to the respective OpenCV quality or
            compression parameter (e.g. 'jpg' -> cv2.IMWRITE_JPEG_QUALITY,
            'png' -> cv2.IMWRITE_PNG_COMPRESSION)..
    """
    return {
        'jpg': _get_cv2_param('IMWRITE_JPEG_QUALITY'),
        'png': _get_cv2_param('IMWRITE_PNG_COMPRESSION'),
        'webp': _get_cv2_param('IMWRITE_WEBP_QUALITY')
    }


##
## Python csv Module Wrapper (for StatsManager, and CliContext/list-scenes command)
##

def get_csv_reader(file_handle):
    # type: (File) -> csv.reader
    """ Returns a csv.reader object using the passed file handle. """
    return csv.reader(file_handle, lineterminator='\n')


def get_csv_writer(file_handle):
    # type: (File) -> csv.writer
    """ Returns a csv.writer object using the passed file handle. """
    return csv.writer(file_handle, lineterminator='\n')


##
## File I/O
##

def get_and_create_path(file_path, output_directory=None):
    # type: (str, Optional[str]) -> str
    """ Get & Create Path: Gets and returns the full/absolute path to file_path
    in the specified output_directory if set, creating any required directories
    along the way.

    If file_path is already an absolute path, then output_directory is ignored.

    Arguments:
        file_path (str): File name to get path for.  If file_path is an absolute
            path (e.g. starts at a drive/root), no modification of the path
            is performed, only ensuring that all output directories are created.
        output_dir (Optional[str]): An optional output directory to override the
            directory of file_path if it is relative to the working directory.

    Returns:
        (str) Full path to output file suitable for writing.

    """
    if file_path is None:
        return None
    # If an output directory is defined and the file path is a relative path, open
    # the file handle in the output directory instead of the working directory.
    if output_directory is not None and not os.path.isabs(file_path):
        file_path = os.path.join(output_directory, file_path)
    # Now that file_path is an absolute path, let's make sure all the directories
    # exist for us to start writing files there.
    try:
        os.makedirs(os.path.split(os.path.abspath(file_path))[0])
    except OSError:
        pass
    return file_path


class CommandTooLong(Exception):
    """ Raised when the length of a command line argument doesn't play nicely
    with the Windows command prompt. """
    # pylint: disable=unnecessary-pass
    pass


def invoke_command(args):
    # type: (List[str] -> None)
    """ Same as calling Python's subprocess.call() method, but explicitly
    raises a different exception when the command length is too long.

    See https://github.com/Breakthrough/PySceneDetect/issues/164 for details.

    Arguments:
        args (List[str]): List of strings to pass to subprocess.call().

    Returns:
        int: Return code of command.

    Raises:
        CommandTooLong when passed command list exceeds built in command line
        length limit on Windows.
    """
    try:
        return subprocess.call(args)
    except OSError as err:
        if os.name != 'nt':
            raise
        exception_string = str(err)
        # Error 206: The filename or extension is too long
        # Error 87:  The parameter is incorrect
        to_match = ('206', '87')
        if any([x in exception_string for x in to_match]):
            raise CommandTooLong()
        raise
