# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
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
from scenedetect.scene_detector import SceneDetector
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_stream import VideoStream, VideoOpenFailure
from scenedetect.backends import open_video, AVAILABLE_BACKENDS
from scenedetect.stats_manager import StatsManager, StatsFileCorrupt
from scenedetect.detectors import ContentDetector, AdaptiveDetector, ThresholdDetector
from scenedetect.video_splitter import split_video_ffmpeg, split_video_mkvmerge

# Used for module identification and when printing version & about info
# (e.g. calling `scenedetect version` or `scenedetect about`).
__version__ = 'v0.6-dev3'
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
  [ https://scenedetect.com/copyright/ ]

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

# pylint: disable=line-too-long
def detect(video_path: str,
           detector: SceneDetector,
           stats_file_path: Optional[str] = None,
           show_progress: bool = False) -> List[Tuple[FrameTimecode, FrameTimecode]]:
    """Perform scene detection on a given video `path` using the specified `detector`.

    Arguments:
        video_path: Path to input video (absolute or relative to working directory).
        detector: A `SceneDetector` instance (`ContentDetector`, `ThresholdDetector`, etc...).
            See :py:mod:`scenedetect.detectors` for a full list of detection algorithms.
        stats_file_path: Path to save per-frame metrics to for statistical analysis or to
            determine a better threshold value.
        show_progress: Show a progress bar with estimated time remaining. Default is False.

    Returns:
        List of scenes (pairs of :py:class:`FrameTimecode` objects).

    Raises:
        :py:class:`VideoOpenFailure`: `video_path` could not be opened.
        :py:class:`StatsFileCorrupt`: `stats_file_path` is an invalid stats file
    """
    video = open_video(video_path)
    if stats_file_path:
        scene_manager = SceneManager(StatsManager())
    else:
        scene_manager = SceneManager()
    scene_manager.add_detector(detector)
    scene_manager.detect_scenes(video=video, show_progress=show_progress)
    if not scene_manager.stats_manager is None:
        scene_manager.stats_manager.save_to_csv(
            path=stats_file_path, base_timecode=video.base_timecode)
    return scene_manager.get_scene_list()
