# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the above pages for details.
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

from typing import List, Optional, Tuple

# Commonly used classes/functions exported under the `scenedetect` namespace for brevity.
from scenedetect.scene_manager import SceneManager, save_images
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_stream import VideoStream
from scenedetect.backends import open_video, AVAILABLE_BACKENDS
from scenedetect.stats_manager import StatsManager
from scenedetect.detectors import ContentDetector, AdaptiveDetector, ThresholdDetector

# Used for module identification and when printing version & about info
# (e.g. calling `scenedetect version` or `scenedetect about`).
__version__ = 'v0.6-dev'
# About & copyright message string shown for the 'about' CLI command (scenedetect about).

ABOUT_STRING = """
Site/Updates: https://github.com/Breakthrough/PySceneDetect/
Documentation: http://pyscenedetect.readthedocs.org/

Copyright (C) 2014-2022 Brandon Castellano. All rights reserved.

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


def detect_scenes(
    video_path: str,
    threshold: Optional[int] = None,
    stats_file_path: Optional[str] = None,
    show_progress: bool = False) -> List[Tuple[FrameTimecode, FrameTimecode]]:
    """High level function that performs scene content-aware scene detection on a given
    video path, and returns a list of scenes (pairs of FrameTimecodes).

    Arguments:
        TODO(v0.6)

    Raises:
        TODO(v0.6)
    """

    video = open_video(video_path)
    if stats_file_path:
        stats_manager = StatsManager()
        stats_manager.load_from_csv(stats_file_path)
        scene_manager = SceneManager(stats_manager)
    else:
        stats_manager = None
        scene_manager = SceneManager()

    if threshold is not None:
        scene_manager.add_detector(ContentDetector(threshold=threshold))
    else:
        scene_manager.add_detector(ContentDetector())

    scene_manager.detect_scenes(video=video, show_progress=show_progress)
    if not stats_manager is None:
        stats_manager.save_to_csv(path=stats_file_path, base_timecode=video.base_timecode)
    return scene_manager.get_scene_list()
