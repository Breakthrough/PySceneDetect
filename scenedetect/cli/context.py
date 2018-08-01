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

from scenedetect.video_splitter import is_mkvmerge_available
from scenedetect.video_splitter import is_ffmpeg_available
from scenedetect.video_splitter import split_video_mkvmerge
from scenedetect.video_splitter import split_video_ffmpeg

from scenedetect.platform import get_cv2_imwrite_params


def get_plural(val_list):
    return 's' if len(val_list) > 1 else ''

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
        # Properties for main scenedetect command options (-i, -s, etc...) and CliContext logic.
        self.options_processed = False          # True when CLI option parsing is complete.
        self.scene_manager = None               # detect-content, detect-threshold, etc...
        self.video_manager = None               # -i/--input, -d/--downscale
        self.base_timecode = None               # -f/--framerate
        self.start_frame = 0                    # time -s/--start [start_frame]
        self.stats_manager = StatsManager()     # -s/--stats
        self.stats_file_path = None             # -s/--stats [stats_file_path]
        self.output_directory = None            # -o/--output [output_directory]
        self.quiet_mode = False                 # -q/--quiet or -v/--verbosity quiet
        self.frame_skip = 0                     # -fs/--frame-skip [frame_skip]
        # Properties for save-images command.
        self.save_images = False                # save-images command
        self.image_extension = 'jpg'            # save-images -j/--jpeg, -w/--webp, -p/--png
        self.image_directory = None             # save-images -o/--output [image_directory]
        self.image_param = None                 # save-images -q/--quality if -j/-w, -c/--compression if -p
        self.num_images = 2                     # save-images -n/--num-images
        self.imwrite_params = get_cv2_imwrite_params()
        # Properties for split-video command.
        self.split_video = False                # split-video command
        self.split_mkvmerge = False             # split-video -m/--mkvmerge (or split-video without ffmpeg)
        self.split_args = None                  # split-video -f/--ffmpeg-args [split_args]
        self.split_directory = None             # split-video -o/--output [split_directory]
        self.split_quiet = False                # split-video -q/--quiet
        # Properties for list-scenes command.
        self.list_scenes = False                # list-scenes command
        self.print_scene_list = False           # list-scenes --quiet/-q
        self.scene_list_path = None             # list-scenes -o [scene_list_path]

        

    def cleanup(self):
        try:
            logging.debug('Cleaning up...\n\n')
        finally:
            if self.video_manager is not None:
                self.video_manager.release()


    def _generate_images(self, scene_list, image_prefix, output_dir=None):
        # type: (List[Tuple[FrameTimecode, FrameTimecode]) -> None

        if self.num_images != 2:
            raise NotImplementedError()

        if not scene_list:
            return
        if not self.options_processed:
            return
        self.check_input_open()

        imwrite_param = []
        if self.image_param is not None:
            imwrite_param = [self.imwrite_params[self.image_extension], self.image_param]
        click.echo(imwrite_param)

        # Reset video manager and downscale factor.
        self.video_manager.release()
        self.video_manager.reset()
        self.video_manager.set_downscale_factor(1)
        self.video_manager.start()

        # Setup flags and init progress bar if available.
        completed = True
        logging.info('Generating output images (%d per scene)...', self.num_images)
        progress_bar = None
        if tqdm and not self.quiet_mode:
            progress_bar = tqdm(
                total=len(scene_list) * 2, unit='images')

        for i, (start_time, end_time) in enumerate(scene_list):
            # TODO: Interpolate timecodes if num_frames_per_scene != 2.
            self.video_manager.seek(start_time)
            self.video_manager.grab()
            ret_val, frame_im = self.video_manager.retrieve()
            if ret_val:
                cv2.imwrite(
                    self.get_output_file_path(
                        '%s-Scene-%03d-00.%s' % (image_prefix, i + 1, self.image_extension),
                        output_dir=output_dir), frame_im, imwrite_param)
            else:
                completed = False
                break
            if progress_bar:
                progress_bar.update(1)
            self.video_manager.seek(end_time)
            self.video_manager.grab()
            ret_val, frame_im = self.video_manager.retrieve()
            if ret_val:
                cv2.imwrite(
                    self.get_output_file_path(
                        '%s-Scene-%03d-01.%s' % (image_prefix, i + 1, self.image_extension),
                        output_dir=output_dir), frame_im, imwrite_param)
            else:
                completed = False
                break
            if progress_bar:
                progress_bar.update(1)
                
        if not completed:
            logging.error('Could not generate all output images.')


    def get_output_file_path(self, file_path, output_dir=None):
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
        # type: () -> None
        """ Process Input: Processes input video(s) and generates output as per CLI commands.
        
        Run after all command line options/sub-commands have been parsed.
        """
        logging.debug('Processing input...')
        if not self.options_processed:
            logging.debug('Skipping processing, CLI options were not parsed successfully.')
            return
        self.check_input_open()
        if not self.scene_manager.get_num_detectors() > 0:
            logging.error('No scene detectors specified (detect-content, detect-threshold, etc...).')
            return

        # Handle scene detection commands (detect-content, detect-threshold, etc...).
        self.video_manager.start()
        base_timecode = self.video_manager.get_base_timecode()

        start_time = time.time()
        logging.info('Detecting scenes...')

        num_frames = self.scene_manager.detect_scenes(
            frame_source=self.video_manager, start_time=self.start_frame,
            frame_skip=self.frame_skip, show_progress=not self.quiet_mode)

        duration = time.time() - start_time
        logging.info('Processed %d frames in %.1f seconds (average %.2f FPS).',
                     num_frames, duration, float(num_frames)/duration)

        # Handle -s/--statsfile option.
        if self.stats_file_path is not None:
            if self.stats_manager.is_save_required():
                with open(self.stats_file_path, 'wt') as stats_file:
                    logging.info('Saving frame metrics to stats file: %s',
                                 os.path.basename(self.stats_file_path))
                    self.stats_manager.save_to_csv(
                        stats_file, base_timecode)
            else:
                logging.debug('No frame metrics updated, skipping update of the stats file.')
        
        # Get list of detected cuts and scenes from the SceneManager to generate the required output
        # files with based on the given commands (list-scenes, split-video, save-images, etc...).
        cut_list = self.scene_manager.get_cut_list(base_timecode)
        scene_list = self.scene_manager.get_scene_list(base_timecode)
        video_paths = self.video_manager.get_video_paths()
        video_name = os.path.basename(video_paths[0])
        if video_name.rfind('.') >= 0:
            video_name = video_name[:video_name.rfind('.')]

        # Handle list-scenes command.
        # Handle `list-scenes -o`.
        if self.scene_list_path is not None:
            with open(self.scene_list_path, 'wt') as scene_list_file:
                write_scene_list(scene_list_file, cut_list, scene_list)
        # Handle `list-scenes`.
        logging.info('Detected %d scenes, average shot length %.1f seconds.',
                     len(scene_list),
                     sum([(end_time - start_time).get_seconds()
                          for start_time, end_time in scene_list]) / float(len(scene_list)))
        if self.print_scene_list:
            logging.info(""" Scene List:
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
%s
-----------------------------------------------------------------------
""", '\n'.join(
    [' |  %5d  | %11d | %s | %11d | %s |' % (
        i+1,
        start_time.get_frames(), start_time.get_timecode(),
        end_time.get_frames(), end_time.get_timecode())
     for i, (start_time, end_time) in enumerate(scene_list)]))


        if cut_list:
            logging.info('Comma-separated timecode list:\n  %s',
                         ','.join([cut.get_timecode() for cut in cut_list]))

        # Handle save-images command.
        if self.save_images:
            self._generate_images(scene_list=scene_list, image_prefix=video_name,
                                  output_dir=self.image_directory)

        # Handle split-video command.
        if self.split_video:
            output_file_name = self.get_output_file_path(
                video_name, output_dir=self.split_directory)
            mkvmerge_available = is_mkvmerge_available()
            ffmpeg_available = is_ffmpeg_available()
            if mkvmerge_available and (self.split_mkvmerge or not ffmpeg_available):
                if not self.split_mkvmerge:
                    logging.info('ffmpeg not found.')
                logging.info('Splitting input video%s using mkvmerge...',
                             's' if len(video_paths) > 1 else '')
                split_video_mkvmerge(video_paths, scene_list, output_file_name,
                                     suppress_output=self.quiet_mode or self.split_quiet)
            elif ffmpeg_available:
                logging.info('Splitting input video%s using ffmpeg...',
                    's' if len(video_paths) > 1 else '')
                split_video_ffmpeg(video_paths, scene_list,
                    output_file_name, arg_override=self.split_args,
                    hide_progress=self.quiet_mode or self.split_quiet,
                    suppress_output=self.quiet_mode or self.split_quiet)
            else:
                error_strs = ["ffmpeg/mkvmerge is required for video splitting.",
                    "Install one of the above tools to enable the split-video command."]
                error_str = '\n'.join(error_strs)
                logging.debug(error_str)
                raise click.BadParameter(error_str, param_hint='split-video')
                
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
        options_processed_orig = self.options_processed
        self.options_processed = False
        try:
            self.scene_manager.add_detector(detector)
        except scenedetect.stats_manager.FrameMetricRegistered:
            raise click.BadParameter(message='Cannot specify detection algorithm twice.',
                                     param_hint=detector.cli_name)
        self.options_processed = options_processed_orig


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
            error_strs = ['could not open video%s.' % get_plural(ex.file_list),
                'Failed to open the following video file%s:' % get_plural(ex.file_list)]
            error_strs += ['  %s' % file_name[0] for file_name in ex.file_list]
            logging.error('\n'.join(error_strs[1:]))
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
            self.stats_file_path = self.get_output_file_path(stats_file)
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
        self.check_input_open()
        
        self.print_scene_list = True if quiet_mode is None else not quiet_mode
        self.scene_list_path = self.get_output_file_path(output_path)
        if self.scene_list_path is not None:
            logging.info('Output scene list CSV file set:\n  %s', self.scene_list_path)


    def save_images_command(self, num_images, output, jpeg, webp, quality, png, compression):
        self.check_input_open()

        num_flags = sum([True if flag else False for flag in [jpeg, webp, png]])
        if num_flags <= 1:
            
            # Ensure the format exists.
            extension = 'jpg'   # Default is jpg.
            if png:
                extension = 'png'
            elif webp: 
                extension = 'webp'
            if not extension in self.imwrite_params or self.imwrite_params[extension] is None:
                error_strs = ['Image encoder type %s not supported.' % extension.upper(),
                'The specified encoder type could not be found in the current OpenCV module.',
                'To enable this output format, please update the installed version of OpenCV.',
                'If you build OpenCV, ensure the the proper dependencies are enabled. ']
                logging.error('\n'.join(error_strs))
                raise click.BadParameter('Specified output image format not supported.', param_hint='save-images')

            self.save_images = True
            self.image_directory = output
            self.image_extension = extension
            self.image_param = compression if png else quality
            self.num_images = num_images
        else:
            self.options_processed = False
            logging.error('Multiple image type flags set for save-images command.')
            raise click.BadParameter('Only one image type (JPG/PNG/WEBP) can be specified.', param_hint='save-images')

