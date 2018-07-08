#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
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

""" PySceneDetect scenedetect.cli_context Module

This file contains the implementation of the PySceneDetect command-line
interface (CLI) context class CliContext, used for the main application
state/context and logic to run the PySceneDetect CLI.
"""

# Standard Library Imports
from __future__ import print_function
import sys
import string

# Third-Party Library Imports
import cv2
import click

# PySceneDetect Library Imports
import scenedetect

from scenedetect.frame_timecode import FrameTimecode

from scenedetect.video_manager import VideoManager
from scenedetect.video_manager import VideoOpenFailure
from scenedetect.video_manager import VideoFramerateUnavailable
from scenedetect.video_manager import VideoParameterMismatch
from scenedetect.video_manager import VideoDecodingInProgress
from scenedetect.video_manager import VideoDecoderProcessStarted
from scenedetect.video_manager import VideoDecoderProcessNotStarted


class CliContext(object):
    def __init__(self):
        self.video_manager = None
        self.framerate = None

    def cleanup(self):
        if self.video_manager is not None:
            try:
                self.video_manager.stop()
            finally:
                self.video_manager.release()


    def input_videos(self, input_list, framerate=None):
        # type: List[str], Optional[float] -> bool
        self.framerate = framerate
        #click.echo(input_list)
        #click.echo('fps=%s' % framerate)
        video_manager_initialized = False
        try:
            self.video_manager = VideoManager(
                video_files=input_list, framerate=framerate)
            video_manager_initialized = True
        except VideoOpenFailure as ex:
            click.echo('Failed to open video file(s):')
            [click.echo('  %s' % file_name[0]) for file_name in ex.file_list]
        except VideoFramerateUnavailable as ex:
            click.echo('Failed to obtain framerate for video file %s.' % ex.file_name)
            click.echo('Specify framerate manually with the -f / --framerate option.')
        except VideoParameterMismatch as ex:
            click.echo('The following video parameters do not match:')
            for param in ex.file_list:
                if param[0] == cv2.CAP_PROP_FPS:
                    param_name = 'FPS'
                if param[0] == cv2.CAP_PROP_FRAME_WIDTH:
                    param_name = 'Frame width'
                if param[0] == cv2.CAP_PROP_FRAME_HEIGHT:
                    param_name = 'Frame height'
                click.echo('  %s mismatch in video %s (got %.2f, expected %.2f)' % (
                    param_name, param[3], param[1], param[2]))
            click.echo('Specify parameter override with -p / --param-override to disable this check.')
        
        if not video_manager_initialized:
            self.video_manager = None

        return self.video_manager is None
    
