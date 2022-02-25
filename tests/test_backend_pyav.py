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
""" PySceneDetect scenedetect.backend.pyav Tests

This file includes unit tests for the scenedetect.backend.pyav module that implements the
VideoStreamAv ('pyav') backend. These tests validate behaviour specific to this backend.

For VideoStream tests that validate conformance, see test_video_stream.py.
"""

from scenedetect.backends.pyav import VideoStreamAv

def test_video_stream_pyav_bytesio(test_video_file: str):
    """Test that VideoStreamAv works with a BytesIO input in addition to a path."""
    # Mode must be binary!
    video_file = open(test_video_file, mode='rb')
    stream = VideoStreamAv(path_or_io=video_file)
    assert stream.is_seekable
    stream.seek(50)
    for _ in range(10):
        assert stream.read() is not False
