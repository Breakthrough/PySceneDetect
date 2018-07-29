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
# This software uses the Numpy, OpenCV, click, tqdm, and pytest libraries.
# See the included LICENSE files or one of the above URLs for more information.
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
import logging
import os
import time

# Third-Party Library Imports
import click
import cv2
from scenedetect.platform import tqdm

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

from scenedetect.video_splitter import split_video_ffmpeg
from scenedetect.video_splitter import split_video_mkvmerge


class CliContext(object):
    """ Context of the command-line interface passed between the various sub-commands.

    Pools all options, processing the main program options as they come in (e.g. those
    not passed to a command), followed by parsing each sub-command's options, preparing
    the actions to be executed in the process_input() method, which is called after the
    whole command line has been processed (successfully nor not).
    
    This class and the cli.__init__ module make up the bulk of the PySceneDetect
    application logic for the command line.  
    """
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

        self.output_directory = None
        self.options_processed = False

        self.print_scene_list = False
        self.scene_list_path = None # Optional[str]: Path to stats file.

        self.quiet_mode = False
        self.frame_skip = 0

        self.split_video = False
        self.split_mkvmerge = False
        self.split_args = None
        

    def cleanup(self):
        try:
            logging.debug('Cleaning up...\n\n')
        finally:
            if self.video_manager is not None:
                self.video_manager.release()


    def _generate_images(self, scene_list, num_frames_per_scene=2):


        # type: (List[Tuple[FrameTimecode, FrameTimecode]) -> None
        if not scene_list:
            return
        if not self.options_processed:
            return
        self.check_input_open()
        
        self.video_manager.release()
        self.video_manager.reset()
        self.video_manager.set_downscale_factor(1)
        self.video_manager.start()

        completed = True
        logging.info('Generating output images (%d per scene)...', num_frames_per_scene)
        progress_bar = None
        if tqdm:
            progress_bar = tqdm(
                total=len(scene_list) * 2, unit='images')

        for i, (start_time, end_time) in enumerate(scene_list):
            # Need to interpolate timecodes if num_frames_per_scene > 2.
            self.video_manager.seek(start_time)
            self.video_manager.grab()
            ret_val, frame_im = self.video_manager.retrieve()
            if ret_val:
                cv2.imwrite(self._get_output_file_path('Scene-%03d-00.jpg' % (i)), frame_im)
            else:
                completed = False
                break
            progress_bar.update(1)
            self.video_manager.seek(end_time)
            self.video_manager.grab()
            ret_val, frame_im = self.video_manager.retrieve()
            if ret_val:
                cv2.imwrite(self._get_output_file_path('Scene-%03d-01.jpg' % (i)), frame_im)
            else:
                completed = False
                break
            progress_bar.update(1)
                
        if not completed:
            logging.error('Could not generate all output images.')


    def _get_output_file_path(self, file_path, output_dir=None):
        # type: (str, Optional[str]) -> str
        '''Returns path to output file_path passed as argument, and creates directories if necessary.'''
        if file_path is None:
            return None
        output_dir = self.output_directory if output_dir is None else output_dir
        # If an output directory is defined and the file path is a relative path, open
        # the file handle in the output directory instead of the working directory.
        if output_dir is not None and not os.path.isabs(file_path):
            file_path = os.path.join(output_dir, file_path)
        # Now that file_path is an absolute path, let's make sure all the directories
        # exist for us to start writing files there.
        os.makedirs(os.path.split(os.path.abspath(file_path))[0], exist_ok=True)
        return file_path

    def _open_stats_file(self):
        
        if self.stats_file_path is not None:
            if os.path.exists(self.stats_file_path):
                logging.info('Loading frame metrics from stats file: %s',
                    os.path.basename(self.stats_file_path))
                try:
                    with open(self.stats_file_path, 'rt') as stats_file:
                        self.stats_manager.load_from_csv(stats_file, self.base_timecode)
                except StatsFileCorrupt:
                    error_strs = [
                        'Could not load stats file.', 'Failed to parse stats file:',
                        'Could not load frame metrics from stats file - file is corrupt or not a'
                        ' valid PySceneDetect stats file. If the file exists, ensure that it is'
                        ' a valid stats file CSV, otherwise delete it and run PySceneDetect again'
                        ' to re-generate the stats file.']
                    logging.error('\n'.join(error_strs))
                    raise click.BadParameter('\n  Could not load given stats file, see above output for details.', param_hint='input stats file')
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
                    raise click.BadParameter(
                        'framerate differs between given stats file and input video(s).',
                        param_hint='input stats file')


    def process_input(self):
        
        logging.debug('Processing input...')

        if not self.options_processed:
            logging.debug('Skipping processing, CLI options were not parsed successfully.')
            return

        self.check_input_open()

        if not self.scene_manager.get_num_detectors() > 0:
            logging.error('No scene detectors specified (detect-content, detect-threshold, etc...).')
            return


        self.video_manager.start()

        base_timecode = self.video_manager.get_base_timecode()

        start_time = time.time()
        logging.info('Detecting scenes...')
        num_frames = self.scene_manager.detect_scenes(
            frame_source=self.video_manager, start_time=self.start_frame,
            frame_skip=self.frame_skip, show_progress=not self.quiet_mode)
        end_time = time.time()
        duration = end_time - start_time
        logging.info('Processed %d frames in %.1f seconds (average %.2f FPS).', num_frames,
            duration, num_frames/duration)

        if self.stats_file_path is not None:
            if self.stats_manager.is_save_required():
                with open(self.stats_file_path, 'wt') as stats_file:
                    logging.info('Saving frame metrics to stats file: %s',
                        os.path.basename(self.stats_file_path))
                    self.stats_manager.save_to_csv(
                        stats_file, base_timecode)
            else:
                logging.debug('No frame metrics updated, skipping update of the stats file.')
        

        cut_list = self.scene_manager.get_cut_list(base_timecode)
        scene_list = self.scene_manager.get_scene_list(base_timecode)

        if self.scene_list_path is not None:
            with open(self.scene_list_path, 'wt') as scene_list_file:
                write_scene_list(scene_list_file, cut_list, scene_list)

        if self.print_scene_list:
            logging.info("""Detected %d scenes, scene list:

-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
%s
-----------------------------------------------------------------------
""", len(scene_list), '\n'.join(
    [' |  %5d  | %11d | %s | %11d | %s |' % (
        i+1,
        start_time.get_frames(), start_time.get_timecode(),
        end_time.get_frames(), end_time.get_timecode())
     for i, (start_time, end_time) in enumerate(scene_list)]))

        else:
            logging.info('Detected %d scenes.', len(scene_list))

        if cut_list:
            logging.info('Comma-separated timecode list:\n  %s',
                         ','.join([cut.get_timecode() for cut in cut_list]))

        # TODO: Add getter for VideoManager _video_file_paths property.
        if self.split_video:
            output_file_name = self._get_output_file_path(
                os.path.basename(self.video_manager._video_file_paths[0]))
            if output_file_name.rfind('.') >= 0:
                output_file_name = output_file_name[:output_file_name.rfind('.')]
            if self.split_mkvmerge:
                logging.info('Splitting input video%s using mkvmerge...',
                    's' if len(self.video_manager._video_file_paths) > 1 else '')
                split_video_mkvmerge(self.video_manager._video_file_paths, scene_list,
                    output_file_name)
            else:
                logging.info('Splitting input video%s using ffmpeg...',
                    's' if len(self.video_manager._video_file_paths) > 1 else '')
                split_video_ffmpeg(self.video_manager._video_file_paths, scene_list,
                    output_file_name, arg_override=self.split_args)
            logging.info('Video splitting completed, individual scenes written to disk.')


    def check_input_open(self):
        if self.video_manager is None or not self.video_manager.get_num_videos() > 0:
            error_strs = ["No input video(s) specified.",
                          "Make sure '--input VIDEO' is specified at the start of the command."]
            error_str = '\n'.join(error_strs)
            logging.debug(error_str)
            raise click.BadParameter(error_str, param_hint='input video')


    def add_detector(self, detector):
        self.check_input_open()
        self.options_processed = False
        try:
            self.scene_manager.add_detector(detector)
        except scenedetect.stats_manager.FrameMetricRegistered:
            raise click.BadParameter(message='Cannot specify detection algorithm twice.',
                                     param_hint=detector.cli_name)
        self.options_processed = True


    def _init_video_manager(self, input_list, framerate, downscale):

        self.base_timecode = None

        logging.debug('Initializing VideoManager.')
        video_manager_initialized = False
        try:
            self.video_manager = VideoManager(
                video_files=input_list, framerate=framerate, logger=logging)
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
            error_strs = ['Downscale value is not > 0.', str(ex)]
            logging.error('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='downscale factor')
        return video_manager_initialized


    def parse_options(self, input_list, framerate, stats_file, downscale, frame_skip):
        """ Parse Options: Parses all CLI arguments passed to scenedetect [options]. """
        if not input_list:
            return

        logging.debug('Parsing program options.')

        self.frame_skip = frame_skip

        video_manager_initialized = self._init_video_manager(
            input_list=input_list, framerate=framerate, downscale=downscale)

        # Ensure VideoManager is initialized, and open StatsManager if --stats is specified.
        if not video_manager_initialized:
            self.video_manager = None
            logging.info('VideoManager not initialized.')
        else:
            logging.debug('VideoManager initialized.')
            self.stats_file_path = self._get_output_file_path(stats_file)
            if self.stats_file_path is not None:
                self.check_input_open()
                self._open_stats_file()

        # Init SceneManager.
        self.scene_manager = SceneManager(self.stats_manager)

        self.options_processed = True

                
    def time_command(self, start=None, duration=None, end=None):
        
        logging.debug('Setting video time:\n    start: %s, duration: %s, end: %s',
            start, duration, end)

        self.check_input_open()

        if duration is not None and end is not None:
            raise click.BadParameter(
                'Only one of --duration/-d or --end/-e can be specified, not both.',
                param_hint='time')

        self.video_manager.set_duration(start_time=start, duration=duration, end_time=end)
        
        if start is not None:
            self.start_frame = start.get_frames()


    def list_scenes_command(self, output_path, quiet_mode):
        self.print_scene_list = True if quiet_mode is None else not quiet_mode
        self.scene_list_path = self._get_output_file_path(output_path)
        if self.scene_list_path is not None:
            logging.info('Output scene list CSV file set:\n  %s', self.scene_list_path)


    def save_images_command(self, output_path, quality, resolution):
        pass

