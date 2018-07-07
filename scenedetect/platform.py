#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
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

""" PySceneDetect scenedetect.platform Module

This file contains all platform/library/OS-specific code, intended to improve
compatibility of PySceneDetect with a wider array of software versions.

Specifically, this module adds compatibility wrappers for Python's Queue/queue
(Python 2/3, respectively) as scenedetect.platform.queue, and for OpenCV 2.x,
copies the OpenCV VideoCapture property constants from the cv2.cv namespace
directly to the cv2 namespace.  This ensures that the cv2 API is consistent
with those changes made to it in OpenCV 3.0 and above.
"""

# Standard Library Imports
from __future__ import print_function
import sys

# Third-Party Library Imports
import cv2

# Queue library
# pylint: disable=unused-import
if sys.version_info[0] == 2:
    import Queue as queue
else:
    import queue
# pylint: enable=unused-import

# Compatibility fix for OpenCV v3.0+:
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

