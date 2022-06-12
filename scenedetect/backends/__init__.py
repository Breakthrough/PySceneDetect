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
implementations. In addition to creating backend objects directly, :py:func:`scenedetect.open_video`
can be used to open a video with a specified backend, falling back to OpenCV if not available.
All backends available on the current system can be found via :py:data:`AVAILABLE_BACKENDS`.

===============================================================
Usage Example
===============================================================

Assuming we have a file `video.mp4` in our working directory, we can load it and iterate through
all of the frames:

.. code:: python

    from scenedetect import open_video
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
    from scenedetect import open_video
    video = open_video('video.mp4', backend='opencv')

If the specified ``backend`` is not available, OpenCV will be used as a fallback. Other keyword
arguments passed to :py:func:`open_video` will be forwarded to the specified backend.
Lastly, we can import and use specific backend directly:

.. code:: python

    # Manually importing and constructing a backend:
    from scenedetect.backends.opencv import VideoStreamCv2
    video = VideoStreamCv2('video.mp4')

The ``opencv`` backend (:py:class:`VideoStreamCv2 <scenedetect.backends.opencv.VideoStreamCv2>`)
is guaranteed to be available.
"""

# TODO(v1.0): Consider removing and making this a namespace package so that additional backends can
# be dynamically added. The preferred approach for this should probably be:
# https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-namespace-packages

# TODO: Future VideoStream implementations under consideration:
#  - Nvidia VPF: https://developer.nvidia.com/blog/vpf-hardware-accelerated-video-processing-framework-in-python/

from typing import Dict, Type

# VideoStreamCv2 must be available at minimum.
from scenedetect.backends.opencv import VideoStreamCv2

try:
    from scenedetect.backends.pyav import VideoStreamAv
except ImportError:
    VideoStreamAv = None

try:
    from scenedetect.backends.moviepy import VideoStreamMoviePy
except ImportError:
    VideoStreamMoviePy = None

AVAILABLE_BACKENDS: Dict[str, Type] = {
    backend.BACKEND_NAME: backend for backend in filter(None, [
        VideoStreamCv2,
        VideoStreamAv,
        VideoStreamMoviePy,
    ])
}
"""All available backends that :py:func:`scenedetect.open_video` can consider for the `backend`
parameter. These backends must support construction with the following signature:

    BackendType(path: str, framerate: Optional[float])
"""
