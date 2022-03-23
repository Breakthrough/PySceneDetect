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
implementations. In addition to creating backend objects directly, the :py:func:`open_video`
can be used to open a video with a specified backend, falling back to OpenCV if not available.
All backends available on the current system can be found via :py:data:`AVAILABLE_BACKENDS`.


===============================================================
Usage Example
===============================================================

Assuming we have a file `video.mp4` in our working directory, we can load it and iterate through
all of the frames:

.. code:: python

    from scenedetect.backends import open_video
    video = open_video('video.mp4')
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
    video = open_video('video.mp4', backend='opencv')

If the specified ``backend`` is not available, OpenCV will be used as a fallback. Other keyword
arguments passed to :py:func:`open_video` will be forwarded to the specified backend.
Lastly, we can import and use specific backend directly:

.. code:: python

    # Manually importing and constructing a backend:
    from scenedetect.backends.opencv import VideoStreamCv2
    video = VideoStreamCv2('video.mp4')

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
"""All available backends that :py:func:`open_video` can consider for the `backend`
parameter. These backends must support construction with the following signature:

    BackendType(path: str, framerate: Optional[float])
"""


def open_video(
    path: str,
    framerate: Optional[float] = None,
    backend: Optional[str] = None,
    **kwargs,
) -> VideoStream:
    """Opens a video at the given path. If `backend` is specified but not available on the current
    system, OpenCV (`VideoStreamCv2`) will be used as a fallback.

    Arguments:
        path: Path to video file to open.
        framerate: Overrides detected framerate if set.
        backend: Name of specific to use if possible. See :py:data:`AVAILABLE_BACKENDS` for
            backends available on the current system. If the backend fails to open the video,
            OpenCV will be attempted to be used as a fallback.
        kwargs: Optional named arguments to pass to the specified `backend` constructor for
            overriding backend-specific options.

    Returns:
        VideoStream backend object created with the specified video path.

    Raises:
        :py:class:`VideoOpenFailure`: Constructing the VideoStream fails. If multiple backends have
            been attempted, the error from the first backend will be returned.
    """
    # Try to open the video with the specified backend.
    last_error = None
    if backend is not None and backend != 'opencv' and backend in AVAILABLE_BACKENDS:
        try:
            logger.debug('Opening video with %s...', AVAILABLE_BACKENDS[backend].__name__)
            return AVAILABLE_BACKENDS[backend](path, framerate, **kwargs)
        except VideoOpenFailure as ex:
            logger.debug('Failed to open video: %s', str(ex))
            logger.debug('Falling back to OpenCV.')
            last_error = ex
    else:
        logger.debug('Backend %s not available, falling back to OpenCV.', backend)

    # OpenCV backend must be available.
    logger.debug('Opening video with %s...', VideoStreamCv2.__name__)
    try:
        return VideoStreamCv2(path, framerate, **kwargs)
    except VideoOpenFailure as ex:
        logger.debug('Failed to open video: %s', str(ex))
        if last_error is None:
            last_error = ex

    # If we get here, either the specified backend or the OpenCV backend threw an exception, so
    # make sure we propagate it.
    assert last_error is not None
    raise last_error
