# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses the Numpy, OpenCV, click, tqdm, and pytest libraries.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.platform Module

This file contains all platform/library/OS-specific compatibility fixes,
intended to improve the systems that are able to run PySceneDetect, and allow
for maintaining backwards compatibility with existing libraries going forwards.

Specifically, this module adds compatibility wrappers for Python's Queue/queue
(Python 2/3, respectively) as scenedetect.platform.queue, and for OpenCV 2.x,
copies the OpenCV VideoCapture property constants from the cv2.cv namespace
directly to the cv2 namespace.  This ensures that the cv2 API is consistent
with those changes made to it in OpenCV 3.0 and above.  This module also
includes an alias for the unicode/string types in Python 2/3 as STRING_TYPE
intended to help with parsing string types from the CLI parser.
"""

# Standard Library Imports
from __future__ import print_function
import sys
import csv

# Third-Party Library Imports
import cv2


# pylint: disable=unused-import

# Python 2/3 Queue/queue library (scenedetect.platform.queue)
if sys.version_info[0] == 2:
    import Queue as queue
else:
    import queue

# tqdm Library (scenedetect.platform.tqdm will be module or None)
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# pylint: enable=unused-import


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




# Functonality for obtaining csv reader/writer handles with uniform line terminations.
def get_csv_reader(file_handle):
    # type: (File) -> csv.reader
    """ Returns a csv.reader object using the passed file handle. """
    return csv.reader(file_handle, lineterminator='\n')


def get_csv_writer(file_handle):
    # type: (File) -> csv.writer
    """ Returns a csv.writer object using the passed file handle. """
    return csv.writer(file_handle, lineterminator='\n')

