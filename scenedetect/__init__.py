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

""" PySceneDetect scenedetect Module

This file contains the PySceneDetect version string (displayed when calling
'scenedetect version'), the about string for license/copyright information
(when calling 'scenedetect about'), and imports of the most frequently used
classes so they can be accessed directly from the scenedetect module.
"""

# Standard Library Imports
from __future__ import print_function
import sys
import os
import time

# Third-Party Library Imports
import cv2
import click

# PySceneDetect Library Imports
# Commonly used classes for easier use directly from the scenedetect namespace (e.g.
# scenedetect.SceneManager instead of scenedetect.scene_manager.SceneManager).
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_manager import VideoManager
from scenedetect.detectors import ThresholdDetector, ContentDetector

# Used for module identification and when printing version & about info.
# (scenedetect version and scenedetect about)
__version__ = 'v0.5-dev'

# About & copyright message string shown for the 'about' CLI command (scenedetect about).
ABOUT_STRING = """
Site/Updates: https://github.com/Breakthrough/PySceneDetect/
Documentation: http://pyscenedetect.readthedocs.org/

Copyright (C) 2012-2018 Brandon Castellano. All rights reserved.

PySceneDetect is released under the BSD 2-Clause license. See the
included LICENSE file or visit the PySceneDetect website for details.
This software uses the following third-party components:

  > NumPy [Copyright (C) 2018, Numpy Developers]
  > OpenCV [Copyright (C) 2018, OpenCV Team]
  > click [Copyright (C) 2018, Armin Ronacher]

This software can also optionally make use of the following third-party
software tools, if they are available:

  > mkvmerge [Copyright (C) 2005-2018, Matroska]
  > ffmpeg [Copyright (C) 2018, FFmpeg Team]

Certain distributions of PySceneDetect may include binary releases of
these software tools. These binaries were obtained from their
respective copyright holders, and included without modification.
Details as to obtaining a copy of the source code from the original
copyright holder can be found in the relevant LICENSE- file included
with this distribution.

THE SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
"""
