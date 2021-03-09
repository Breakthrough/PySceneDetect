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

""" ``scenedetect`` Module

This is the main PySceneDetect module, containing imports of all classes
so they can be directly accessed from the scenedetect module in addition
to being directly imported (e.g. `from scenedetect import FrameTimecode`
is the same as `from scenedetect.frame_timecode import FrameTimecode`).

This file also contains the PySceneDetect version string (displayed when calling
'scenedetect version'), the about string for license/copyright information
(when calling 'scenedetect about').
"""

# Commonly used classes for easier use directly from the scenedetect namespace (e.g.
# scenedetect.SceneManager instead of scenedetect.scene_manager.SceneManager).
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_manager import VideoManager
from scenedetect.stats_manager import StatsManager

# We also bring the detectors into the main scenedetect package namespace
# for convenience as well. Examples still reference the full package.
from scenedetect.detectors import ThresholdDetector
from scenedetect.detectors import ContentDetector
from scenedetect.detectors import AdaptiveDetector


# Used for module identification and when printing version & about info
# (e.g. calling `scenedetect version` or `scenedetect about`).
__version__ = 'v0.5.6a0'

# About & copyright message string shown for the 'about' CLI command (scenedetect about).

ABOUT_STRING = """
Site/Updates: https://github.com/Breakthrough/PySceneDetect/
Documentation: http://pyscenedetect.readthedocs.org/

Copyright (C) 2014-2021 Brandon Castellano. All rights reserved.

PySceneDetect is released under the BSD 3-Clause license. See the
included LICENSE file or visit the PySceneDetect website for details.
This software uses the following third-party components:

  > NumPy [Copyright (C) 2018, Numpy Developers]
  > OpenCV [Copyright (C) 2018, OpenCV Team]
  > click [Copyright (C) 2018, Armin Ronacher]
  > simpletable [Copyright (C) 2014 Matheus Vieira Portela]

This software may also invoke the following third-party executables:

  > FFmpeg [Copyright (C) 2018, Fabrice Bellard]
  > mkvmerge [Copyright (C) 2005-2016, Matroska]

If included with your distribution of PySceneDetect, see the included
LICENSE-FFMPEG and LICENSE-MKVMERGE or visit:
  [ https://pyscenedetect.readthedocs.io/en/latest/copyright/ ]

FFmpeg and mkvmerge are distributed only with certain PySceneDetect
releases, in order to allow for automatic video splitting capability.
If they were not included with your distribution, they can usually be
installed from your operating system's package manager, or downloaded
from the following URLs:

    FFmpeg:   [ https://ffmpeg.org/download.html ]
    mkvmerge: [ https://mkvtoolnix.download/downloads.html ]
        (Note that mkvmerge is a part of the mkvtoolnix package.)

Once installed, ensure the respective program can be accessed from the
same location running PySceneDetect by calling the `ffmpeg` or
`mkvmerge` command from a terminal/command prompt.

PySceneDetect will automatically use whichever program is available on
the computer, depending on the specified command-line options.

Additionally, certain Windows distributions may include a compiled
Python distribution. For license information regarding the distributed
version of Python, see the included LICENSE-PYTHON file for details,
or visit the following URL: [ https://docs.python.org/3/license.html ]

THE SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
"""
