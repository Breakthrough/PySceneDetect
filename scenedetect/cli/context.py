# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses Numpy, OpenCV, click, pytest, mkvmerge, and ffmpeg. See
# the included LICENSE-* files, or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.cli.context Module

This file contains the implementation of the PySceneDetect command-line
interface (CLI) context class CliContext, used for the main application
state/context and logic to run the PySceneDetect CLI.
"""

# Standard Library Imports
from __future__ import print_function
import sys
import string
import logging
import os

# Third-Party Library Imports
import cv2
import click

# PySceneDetect Library Imports
import scenedetect.detectors

from scenedetect.frame_timecode import FrameTimecode

from scenedetect.scene_manager import SceneManager
from scenedetect.scene_manager import write_scene_list

from scenedetect.stats_manager import StatsManager
from scenedetect.stats_manager import StatsFileCorrupt
from scenedetect.stats_manager import StatsFileFramerateMismatch

from scenedetect.video_manager import VideoManager
from scenedetect.video_manager import VideoOpenFailure
from scenedetect.video_manager import VideoFramerateUnavailable
from scenedetect.video_manager import VideoParameterMismatch
from scenedetect.video_manager import InvalidDownscaleFactor
from scenedetect.video_manager import VideoDecodingInProgress
from scenedetect.video_manager import VideoDecoderNotStarted


class CliContext(object):
    def __init__(self):
        # Optional[SceneManager]: SceneManager to manage storing of detected cuts in a video,
        #                         and convert them 
        self.scene_manager = None
        # Optional[VideoManager]: VideoManager to manage decoding of video(s).
        self.video_manager = None
        # Optional[FrameTimecode]: FrameTimecode time base, also holds framerate (e.g. by
        #                          calling self.base_timecode.get_framerate()).
        self.base_timecode = None
        self.start_frame = 0

        self.stats_manager = StatsManager()
        self.stats_file_path = None # Optional[str]: Path to stats file.
        self.stats_file = None

        self.output_directory = None
        self.process_input_flag = True
        

    def cleanup(self):
        try:
            logging.debug('CliContext: Cleaning up.')
        finally:
            if self.video_manager is not None:
                self.video_manager.release()


    def _open_stats_file(self):
        
        if self.stats_file_path is not None:
            # If an output directory is defined and the stats file path is a single
            # filename (i.e. not an absolute/relative path), open the file handle
            # in the output directory instead of the working directory.
            if self.output_directory is not None and os.path.split(self.stats_file_path)[0]:
                self.stats_file_path = os.path.join(
                    self.output_directory, self.stats_file_path)
            if os.path.exists(self.stats_file_path):
                logging.info('CliContext: Found stats file %s, loading frame metrics.',
                    os.path.basename(self.stats_file_path))
                try:
                    self.stats_file = open(self.stats_file_path, 'r')
                    self.stats_manager.load_from_csv(self.stats_file, self.base_timecode)
                except StatsFileCorrupt:
                    error_strs = [
                        'could not load stats file.', 'Failed to parse stats file:',
                        'Could not load frame metrics from stats file, file is corrupt or not a'
                        ' valid PySceneDetect stats file. If the file exists, ensure that it is'
                        ' a valid stats file CSV, otherwise delete it and run PySceneDetect again'
                        ' to re-generate the stats file.']
                    logging.error('\n'.join(error_strs))
                    raise click.BadParameter('\n'.join(error_strs), param_hint='input stats file')
                except StatsFileFramerateMismatch as ex:
                    error_strs = [
                        'could not load stats file.', 'Failed to parse stats file:',
                        'Framerate differs between stats file (%.2f FPS) and input'
                        ' video%s (%.2f FPS)' % (
                            ex.stats_file_fps,
                            's' if self.video_manager.get_num_videos() > 1 else '',
                            ex.base_timecode_fps),
                        'Ensure the correct stats file path was given, or delete and re-generate'
                        ' the stats file.']
                    logging.error('\n'.join(error_strs))
                    raise click.BadParameter('\n'.join(error_strs), param_hint='input stats file')
                finally:
                    if self.stats_file is not None:
                        self.stats_file.close()


    def process_input(self):
        
        logging.debug('CliContext: Processing input...')

        if not self.process_input_flag:
            logging.debug('CliContext: Input processing skipped.')
            return

        self.check_input_open()
        
        # Init SceneManager.
        self.scene_manager = SceneManager(self.stats_manager)

        # Run SceneManager here (cleanup [stop/release] happens even if except. thrown).
        self.scene_manager.add_detector(scenedetect.detectors.ContentDetector())

        self.video_manager.start()
        self.scene_manager.detect_scenes(
            frame_source=self.video_manager, start_time=self.start_frame)

        # testing
        with open('testfile.csv', 'w') as test_file:
            write_scene_list(test_file, self.scene_manager.get_scene_list(
                self.video_manager.get_base_timecode()
            ))


    def check_input_open(self):
        if self.video_manager is None or not self.video_manager.get_num_videos() > 0:
            error_strs = ["no input video(s) specified.",
                          "Make sure '--input VIDEO' is specified at the start of the command."]
            error_str = '\n'.join(error_strs)
            logging.error('CliContext: %s', error_str)
            raise click.BadParameter(error_str, param_hint='input video')


    def parse_options(self, input_list, output_dir, framerate, stats_file_path, downscale):
        """ Parse Options: Parses all CLI arguments passed to scenedetect [options]. """
        if not input_list and framerate is None:
            return

        logging.debug('CliContext: Parsing program options.')

        self.output_directory = output_dir
        self.stats_file_path = stats_file_path
        self.base_timecode = None
        
        logging.debug('CliContext: Initializing VideoManager.')
        video_manager_initialized = False
        try:
            self.video_manager = VideoManager(
                video_files=input_list, framerate=framerate)
            video_manager_initialized = True
            self.base_timecode = self.video_manager.get_base_timecode()
            self.video_manager.set_downscale_factor(downscale)
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
        except InvalidDownscaleFactor as ex:
            self.process_input_flag = False
            error_strs = ['Downscale value is not > 0.', str(ex)]
            logging.error('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='downscale factor')

        # Ensure VideoManager is initialized, and open StatsManager if --stats is specified.
        if not video_manager_initialized:
            self.video_manager = None
            logging.info('CliContext: VideoManager not initialized.')
        else:
            logging.debug('CliContext: VideoManager initialized.')
            if self.stats_file_path is not None:
                self.check_input_open()
                self._open_stats_file()

    def time_command(self, start=None, duration=None, end=None):
        
        logging.debug('CliContext: Setting video time:\n    start: %s, duration: %s, end: %s',
            start, duration, end)

        self.check_input_open()

        if duration is not None and end is not None:
            raise click.BadParameter(
                'Only one of --duration/-d or --end/-e can be specified, not both.',
                param_hint='time')

        self.video_manager.set_duration(start_time=start, duration=duration, end_time=end)
        
        if start is not None:
            self.start_frame = start.get_frames()

