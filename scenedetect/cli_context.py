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
import logging

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
        self.stats_manager = None
        self.scene_manager = None

    def _cleanup(self):
        if self.video_manager is not None:
            try:
                self.video_manager.stop()
            finally:
                self.video_manager.release()



    def process_input(self):
        logging.debug('CliContext: Processing video(s)...')

        self._cleanup()



    def check_input_open(self):
        if self.video_manager is None or not self.video_manager._cap_list:
            error_strs = ["no input video(s) specified.",
                          "Make sure 'input -i VIDEO' is at the start of the command."]
            logging.error('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='input video')

    def input_stats(self, stats_file_path):
        if stats_file_path is not None:
            self.stats_file_path = stats_file_path
            logging.info('Stats File: %s.' % (stats_file_path))

    def input_videos(self, input_list, framerate=None):
        # type: List[str], Optional[float] -> bool
        self.framerate = framerate
        #click.echo(input_list)
        #click.echo('fps=%s' % framerate)
        video_manager_initialized = False
        try:
            print(input_list)
            self.video_manager = VideoManager(
                video_files=input_list, framerate=framerate)
            video_manager_initialized = True
            self.framerate = self.video_manager.get_framerate()
        except VideoOpenFailure as ex:
            error_strs = ['could not open video(s).', 'Failed to open video file(s):']
            error_strs += ['  %s' % file_name[0] for file_name in ex.file_list]
            logging.error('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='input video')
        except VideoFramerateUnavailable as ex:
            error_strs = ['could not get framerate from video(s)',
                          'Failed to obtain framerate for video file %s.' % ex.file_name]
            error_strs.append('Specify framerate manually with the -f / --framerate option.')
            logging.error('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='input video')
        except VideoParameterMismatch as ex:
            error_strs = ['video parameters do not match.', 'List of mismatched parameters:']
            for param in ex.file_list:
                if param[0] == cv2.CAP_PROP_FPS:
                    param_name = 'FPS'
                if param[0] == cv2.CAP_PROP_FRAME_WIDTH:
                    param_name = 'Frame width'
                if param[0] == cv2.CAP_PROP_FRAME_HEIGHT:
                    param_name = 'Frame height'
                error_strs.append('  %s mismatch in video %s (got %.2f, expected %.2f)' % (
                    param_name, param[3], param[1], param[2]))
            error_strs.append(
                'Multiple videos may only be specified if they have the same framerate and'
                ' resolution. -f / --framerate may be specified to override the framerate.')
            logging.error('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='input videos')
        
        if not video_manager_initialized:
            self.video_manager = None
            logging.info('CliContext: VideoManager not initialized.')

        return self.video_manager is None
