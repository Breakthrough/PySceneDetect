# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2019 Brandon Castellano <http://www.bcastell.com>.
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

""" Module: ``scenedetect.platform``

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
import sys
import os
import platform
import struct
import csv

# Third-Party Library Imports
import cv2

# pylint: disable=unused-import


##
## Python 2/3 Queue/queue Library (scenedetect.platform.queue)
##

if sys.version_info[0] == 2:
    import Queue as queue
else:
    import queue


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


##
## OpenCV 2.x Compatibility Fix
##

# Compatibility fix for OpenCV v2.x (copies CAP_PROP_* properties from the
# cv2.cv namespace to the cv2 namespace, as the cv2.cv namespace was removed
# with the release of OpenCV 3.0).
# pylint: disable=c-extension-no-member
if cv2.__version__[0] == '2' or not (
        cv2.__version__[0].isdigit() and int(cv2.__version__[0]) >= 3):
    cv2.CAP_PROP_FRAME_WIDTH = cv2.cv.CV_CAP_PROP_FRAME_WIDTH
    cv2.CAP_PROP_FRAME_HEIGHT = cv2.cv.CV_CAP_PROP_FRAME_HEIGHT
    cv2.CAP_PROP_FPS = cv2.cv.CV_CAP_PROP_FPS
    cv2.CAP_PROP_POS_MSEC = cv2.cv.CV_CAP_PROP_POS_MSEC
    cv2.CAP_PROP_POS_FRAMES = cv2.cv.CV_CAP_PROP_POS_FRAMES
    cv2.CAP_PROP_FRAME_COUNT = cv2.cv.CV_CAP_PROP_FRAME_COUNT
# pylint: enable=c-extension-no-member


##
## OpenCV DLL Check Function (Windows Only)
##

def check_opencv_ffmpeg_dll():
    # type: () -> bool
    """ Check OpenCV FFmpeg DLL: Checks if OpenCV video I/O support is available,
    on Windows only, by checking for the appropriate opencv_ffmpeg*.dll file.

    On non-Windows systems always returns True, or for OpenCV versions that do
    not follow the X.Y.Z version numbering pattern. Thus there may be false
    positives (True) with this function, but not false negatives (False).
    In those cases, PySceneDetect will report that it could not open the
    video file, and for Windows users, also gives an additional warning message
    that the error may be due to the missing DLL file.

    Returns:
        (bool) True if OpenCV video support is detected (e.g. the appropriate
        opencv_ffmpegXYZ.dll file is in PATH), False otherwise.
    """
    if platform.system() == 'Windows' and (
            cv2.__version__[0].isdigit() and cv2.__version__.find('.') > 0):
        is_64_bit_str = '_64' if struct.calcsize("P") == 8 else ''
        dll_filename = 'opencv_ffmpeg{OPENCV_VERSION}{IS_64_BIT}.dll'.format(
            OPENCV_VERSION=cv2.__version__.replace('.', ''),
            IS_64_BIT=is_64_bit_str)
        return any([os.path.exists(os.path.join(path_path, dll_filename))
                    for path_path in os.environ['PATH'].split(';')]), dll_filename
    return True


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

