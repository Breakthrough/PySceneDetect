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
""" ``scenedetect.backends`` Module

This module contains concrete :py:class:`scenedetect.video_stream.VideoStream` implementations,
as well as high level functions to dynamically query available backends, and to open a video
file by path using any available backend.

Available concrete implementations are imported into this namespace automatically. If dependencies
for a given backend are unavailable, they will be set to None instead.

The OpenCV backend (:py:class:`scenedetect.backends.opencv.VideoStreamCv2`) is guaranteed to
always be available.
"""

#
# TODO(v1.0): Consider removing and making this a namespace package so that additional backends can
# be dynamically added. The same thing should be done for detection algorithms.
#
# TODO: Future VideoStream implementations under consideration:
#  - Nvidia VPF: https://developer.nvidia.com/blog/vpf-hardware-accelerated-video-processing-framework-in-python/
#

from typing import Dict, Iterable, List, Optional, Type

# VideoStreamCv2 must be available at minimum.
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.video_stream import VideoStream


AVAILABLE_BACKENDS: Dict[str, Type] = {
    backend.BACKEND_NAME: backend for backend in filter(None, [
        VideoStreamCv2,
    ])
}
"""All available backends that open_video can consider for the `preferred_backend` argument.
These backends must support construction via BackendType(path, framerate)."""

PREFERRED_BACKENDS: Iterable[Type] = list(filter(None, []))
"""List of backend types to try when using `open_video` in order if a preferred backend is not
specified, or the specified `preferred_backend` is unavailable."""


def get_available_backends() -> Dict[str, Type]:
    """Returns a dictionary of backend names to their respective type.

    This function is only intended for use for opening files. To open a device or image sequence,
    use a specific backend type directly.
    """
    return


def open_video(path: str,
               framerate: Optional[float] = None,
               preferred_backend: Optional[str] = None) -> VideoStream:
    """Opens a video at the given path.

    Arguments:
        path: Path to video file to open.
        framerate: Overrides detected framerate if set.
        preferred_backend: Backend name to use if available. See AVAILABLE_BACKENDS for available
            backend names which can be specified. If unavailable or not set, PREFERRED_BACKENDS
            will be used in order. If no PREFERRED_BACKENDS are available, VideoStreamCv2 will be
            used as a fall-back.

    Returns:
        Concrete VideoStream object pointing to opened video.

    Raises:
        VideoOpenFailure if constructing the VideoStream fails.
    """
    # TODO(v0.6): If a backend results in a failure to open the video, the next preferred backend
    # should be used if possible.
    if preferred_backend in AVAILABLE_BACKENDS:
        return AVAILABLE_BACKENDS[preferred_backend](path, framerate)
    for backend in PREFERRED_BACKENDS:
        if backend is not None:
            return backend(path, framerate)
