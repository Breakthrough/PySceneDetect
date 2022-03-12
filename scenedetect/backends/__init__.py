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
""" ``scenedetect.backends`` Module

This module contains concrete :py:class:`VideoStream <scenedetect.video_stream.VideoStream>`
implementations. For video files, the :py:data:`open_video` function can be used to open a
video with any available backend (or a string hinting which backend is preferred).

Backends available on the current system can be found via :py:data:`AVAILABLE_BACKENDS`.

===============================================================
Usage Example
===============================================================

Assuming we have a file `video.mp4` in our working directory, we can load it and iterate through
all of the frames:

.. code:: python

    from scenedetect.backends import open_video
    video = open_video(path='video.mp4')
    while True:
        frame = video.read()
        if frame is False:
            break
    print("Read %d frames" % video.frame_number)

If we want to use a specific backend from :py:data:`AVAILABLE_BACKENDS`, we can pass it to
:py:func:`open_video`:

.. code:: python

    # Specifying a backend via `open_video`:
    from scenedetect.backends import open_video
    video = open_video(path='video.mp4', backend='opencv')

Or we can import and use specific backend directly:

.. code:: python

    # Manually importing and constructing a backend:
    from scenedetect.backends.opencv import VideoStreamCv2
    video = VideoStreamCv2(path_or_device='video.mp4')

The ``'opencv'`` backend (:py:class:`VideoStreamCv2 <scenedetect.backends.opencv.VideoStreamCv2>`)
is guaranteed to be available.
"""

# TODO(v1.0): Consider removing and making this a namespace package so that additional backends can
# be dynamically added. The preferred approach for this should probably be:
# https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-namespace-packages

# TODO: Future VideoStream implementations under consideration:
#  - Nvidia VPF: https://developer.nvidia.com/blog/vpf-hardware-accelerated-video-processing-framework-in-python/

from logging import getLogger
from typing import Dict, List, Optional, Type

# VideoStreamCv2 must be available at minimum.
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.video_stream import VideoStream, VideoOpenFailure

try:
    from scenedetect.backends.pyav import VideoStreamAv
except ImportError:
    VideoStreamAv = None

logger = getLogger('pyscenedetect')

AVAILABLE_BACKENDS: Dict[str, Type] = {
    backend.BACKEND_NAME: backend for backend in filter(None, [
        VideoStreamCv2,
        VideoStreamAv,
    ])
}
"""All available backends that :py:func:`open_video` can consider for the `preferred_backend`
parameter. These backends must support construction with the following signature:

    BackendType(path: str, framerate: Optional[float])
"""

PREFERRED_BACKENDS: List[str] = ['pyav', 'opencv']
"""List of backend names to try, in order, when using :py:func:`open_video`."""


def open_video(path: str,
               framerate: Optional[float] = None,
               backend: Optional[str] = None) -> VideoStream:
    """Opens a video at the given path.

    Arguments:
        path: Path to video file to open.
        framerate: Overrides detected framerate if set.
        backend: Name of specific to use if possible. See :py:data:`AVAILABLE_BACKENDS` for
            available backends. If the specified backend is unavailable (or `backend` is not
            specified), the values in :py:data:`PREFERRED_BACKENDS` will be used in order.

    Returns:
        VideoStream backend object created with the specified video path.

    Raises:
        :py:class:`VideoOpenFailure`: Constructing the VideoStream fails. If multiple backends have
            been attempted, the error from the first backend will be returned.
    """
    # Try to open the video with the specified backend.
    last_error = None
    if backend is not None:
        if backend in AVAILABLE_BACKENDS:
            try:
                logger.debug('Opening video with %s...', AVAILABLE_BACKENDS[backend].__name__)
                return AVAILABLE_BACKENDS[backend](path, framerate)
            except VideoOpenFailure as ex:
                logger.debug('Failed to open video: %s', str(ex))
                logger.debug('Trying preferred backends...')
                last_error = ex
        else:
            logger.debug('Backend %s not available. Trying preferred backends...', backend)
    # Try to open the video with the preferred backends in order.
    for backend_type in PREFERRED_BACKENDS:
        if not backend_type in AVAILABLE_BACKENDS:
            continue
        try:
            backend = AVAILABLE_BACKENDS[backend_type]
            logger.debug('Opening video with %s...', backend.__name__)
            return backend(path, framerate)
        except VideoOpenFailure as ex:
            logger.debug('Failed to open video: %s', str(ex))
            if last_error is None:
                last_error = ex
    assert last_error is not None
    raise last_error
