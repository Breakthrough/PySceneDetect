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

from logging import getLogger
from typing import List, Optional, Tuple, Union

# OpenCV is a required package, but we don't have it as an explicit dependency since we
# need to support both opencv-python and opencv-python-headless. Include some additional
# context with the exception if this is the case.
try:
    import cv2 as _
except ModuleNotFoundError as ex:
    raise ModuleNotFoundError(
        "OpenCV could not be found, try installing opencv-python:\n\npip install opencv-python",
        name='cv2',
    ) from ex

# Commonly used classes/functions exported under the `scenedetect` namespace for brevity.
from scenedetect.scene_manager import SceneManager, save_images
from scenedetect.scene_detector import SceneDetector
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_stream import VideoStream, VideoOpenFailure
from scenedetect.backends import AVAILABLE_BACKENDS, VideoStreamCv2, VideoStreamAv
from scenedetect.stats_manager import StatsManager, StatsFileCorrupt
from scenedetect.detectors import ContentDetector, AdaptiveDetector, ThresholdDetector
from scenedetect.video_splitter import split_video_ffmpeg, split_video_mkvmerge
from scenedetect.platform import init_logger

# [DEPRECATED] DO NOT USE.
from scenedetect.video_manager import VideoManager

# Used for module identification and when printing version & about info
# (e.g. calling `scenedetect version` or `scenedetect about`).
__version__ = 'v0.6.1-dev0'
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

logger = getLogger('pyscenedetect')


def open_video(
    path: str,
    framerate: Optional[float] = None,
    backend: str = 'opencv',
    **kwargs,
) -> VideoStream:
    """Open a video at the given path. If `backend` is specified but not available on the current
    system, OpenCV (`VideoStreamCv2`) will be used as a fallback.

    Arguments:
        path: Path to video file to open.
        framerate: Overrides detected framerate if set.
        backend: Name of specific backend to use, if possible. See
            :py:data:`scenedetect.backends.AVAILABLE_BACKENDS` for backends available on the current
            system. If the backend fails to open the video, OpenCV will be used as a fallback.
        kwargs: Optional named arguments to pass to the specified `backend` constructor for
            overriding backend-specific options.

    Returns:
        :py:class:`VideoStream` backend object created with the specified video path.

    Raises:
        :py:class:`VideoOpenFailure`: Constructing the VideoStream fails. If multiple backends have
            been attempted, the error from the first backend will be returned.
    """
    # Try to open the video with the specified backend.
    last_error = None
    if backend in AVAILABLE_BACKENDS:
        backend_type = AVAILABLE_BACKENDS[backend]
        try:
            logger.debug('Opening video with %s...', backend_type.BACKEND_NAME)
            return backend_type(path, framerate, **kwargs)
        except VideoOpenFailure as ex:
            logger.warning('Failed to open video with %s: %s', backend_type.BACKEND_NAME, str(ex))
            if backend == VideoStreamCv2.BACKEND_NAME:
                raise
            last_error = ex
    else:
        logger.warning('Backend %s not available.', backend)
    # Fallback to OpenCV if `backend` could not open the video or is unavailable.
    backend_type = VideoStreamCv2
    logger.warning('Trying another backend: %s', backend_type.BACKEND_NAME)
    try:
        return backend_type(path, framerate)
    except VideoOpenFailure as ex:
        logger.debug('Failed to open video: %s', str(ex))
        if last_error is None:
            last_error = ex
    # If we get here, either the specified backend or the OpenCV backend threw an exception, so
    # make sure we propagate it.
    assert last_error is not None
    raise last_error


def detect(
    video_path: str,
    detector: SceneDetector,
    stats_file_path: Optional[str] = None,
    show_progress: bool = False,
    start_time: Optional[Union[str, float, int]] = None,
    end_time: Optional[Union[str, float, int]] = None,
) -> List[Tuple[FrameTimecode, FrameTimecode]]:
    """Perform scene detection on a given video `path` using the specified `detector`.

    Arguments:
        video_path: Path to input video (absolute or relative to working directory).
        detector: A `SceneDetector` instance (see :py:mod:`scenedetect.detectors` for a full list
            of detectors).
        stats_file_path: Path to save per-frame metrics to for statistical analysis or to
            determine a better threshold value.
        show_progress: Show a progress bar with estimated time remaining. Default is False.
        start_time: Starting point in video, in the form of a timecode ``HH:MM:SS[.nnn]`` (`str`),
            number of seconds ``123.45`` (`float`), or number of frames ``200`` (`int`).
        end_time: Starting point in video, in the form of a timecode ``HH:MM:SS[.nnn]`` (`str`),
            number of seconds ``123.45`` (`float`), or number of frames ``200`` (`int`).

    Returns:
        List of scenes (pairs of :py:class:`FrameTimecode` objects).

    Raises:
        :py:class:`VideoOpenFailure`: `video_path` could not be opened.
        :py:class:`StatsFileCorrupt`: `stats_file_path` is an invalid stats file
        ValueError: `start_time` or `end_time` are incorrectly formatted.
        TypeError: `start_time` or `end_time` are invalid types.
    """
    video = open_video(video_path)
    if start_time is not None:
        start_time = video.base_timecode + start_time
        video.seek(start_time)
    if end_time is not None:
        end_time = video.base_timecode + end_time
    # To reduce memory consumption when not required, we only add a StatsManager if we
    # need to save frame metrics to disk.
    scene_manager = SceneManager(StatsManager() if stats_file_path else None)
    scene_manager.add_detector(detector)
    scene_manager.detect_scenes(
        video=video,
        show_progress=show_progress,
        end_time=end_time,
    )
    if not scene_manager.stats_manager is None:
        scene_manager.stats_manager.save_to_csv(stats_file_path)
    return scene_manager.get_scene_list()
