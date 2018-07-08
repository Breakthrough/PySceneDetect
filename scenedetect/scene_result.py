
# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains the SceneResult class, which is used by the SceneManager
# and returned when obtaining the scene list/dict.  It holds the parameters
# of each scene (e.g. start/end frame, thumbnails).
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy, OpenCV, and click; see the included LICENSE-
# files for copyright information, or visit one of the above URLs.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.scene_result Module

This module implements the SceneResult object, which represents a distinct scene
detected from a sequence of frames, and the parameters associated with it.
"""

class SceneResult(object):

    def __init__(self, start_frame, end_frame, start_frame_im = None, end_frame_im = None):
        # type: (FrameTimecode, FrameTimecode, Optional[numpy.ndarray], Optional[numpy.ndarray])
        """ Scene Result

        Holds parameters for a given scene which was detected in a video file
        (i.e. a sequence of frames).  Includes information such as start/end
        FrameTimecodes, and optionally, the start/end frame images.
        """
        self.start_frame = start_frame
        self.end_frame = end_frame
        # Need to add 1 frame to duration, e.g. for a 1-frame scene where
        # start_frame and end_frame are the same, duration should be 1.
        
        self.duration = end_frame - start_frame + 1
        # Don't store frame_im's, do a second pass to generate thumbnails.
        #self.start_frame_im = start_frame_im
        #self.end_frame_im = end_frame_im



