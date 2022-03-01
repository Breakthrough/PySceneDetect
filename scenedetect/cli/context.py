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
""" ``scenedetect.cli.context`` Module

This file contains the implementation of the PySceneDetect command-line
interface (CLI) context class CliContext, used for the main application
state/context and logic to run the PySceneDetect CLI.
"""

from __future__ import print_function
import logging
import os
import time
from string import Template
from typing import Dict, List, Tuple, Optional, Union

import click
import cv2

from scenedetect.backends import AVAILABLE_BACKENDS, VideoStreamCv2
from scenedetect.cli.config import ConfigRegistry, ConfigLoadFailure
from scenedetect.frame_timecode import FrameTimecode, MAX_FPS_DELTA
import scenedetect.detectors
from scenedetect.platform import (check_opencv_ffmpeg_dll, get_and_create_path,
                                  get_cv2_imwrite_params, init_logger)
from scenedetect.scene_manager import (SceneManager, save_images, write_scene_list,
                                       write_scene_list_html)
from scenedetect.stats_manager import StatsManager, StatsFileCorrupt
from scenedetect.video_stream import VideoStream, VideoOpenFailure
from scenedetect.video_splitter import (is_mkvmerge_available, is_ffmpeg_available,
                                        split_video_mkvmerge, split_video_ffmpeg)

USER_CONFIG = ConfigRegistry()

VERBOSITY_CHOICES = click.Choice(['debug', 'info', 'warning', 'error'])
BACKEND_CHOICES = click.Choice([key for key in AVAILABLE_BACKENDS.keys()])


def parse_timecode(value: Union[str, int, FrameTimecode], frame_rate: float) -> FrameTimecode:
    """Parses a user input string into a FrameTimecode assuming the given framerate.

    If value is None, None will be returned instead of processing the value.

    Raises:
        click.BadParameter
     """
    if value is None:
        return None
    try:
        return FrameTimecode(timecode=value, fps=frame_rate)
    except (ValueError, TypeError):
        #pylint: disable=raise-missing-from
        raise click.BadParameter(
            'timecode must be in frames (1234), seconds (123.4s), or HH:MM:SS (00:02:03.400)')


def contains_sequence_or_url(video_path: str) -> bool:
    """Checks if the video path is a URL or image sequence."""
    return '%' in video_path or '://' in video_path


def check_split_video_requirements(use_mkvmerge: bool) -> None:
    # type: (bool) -> None
    """ Validates that the proper tool is available on the system to perform the split-video
    command, which depends on if -m/--mkvmerge is set (if not, defaults to ffmpeg).

    Arguments:
        use_mkvmerge: True if -m/--mkvmerge is set, False otherwise.

    Raises: click.BadParameter if the proper video splitting tool cannot be found.
    """

    if (use_mkvmerge and not is_mkvmerge_available()) or not is_ffmpeg_available():
        error_strs = [
            "{EXTERN_TOOL} is required for split-video{EXTRA_ARGS}.".format(
                EXTERN_TOOL='mkvmerge' if use_mkvmerge else 'ffmpeg',
                EXTRA_ARGS=' -m/--mkvmerge' if use_mkvmerge else '')
        ]
        error_strs += ["Install one of the above tools to enable the split-video command."]
        if not use_mkvmerge and is_mkvmerge_available():
            error_strs += ['You can also specify `-m/--mkvmerge` to use mkvmerge for splitting.']
        elif use_mkvmerge and is_ffmpeg_available():
            error_strs += ['You can also specify `-c/--copy` to use ffmpeg stream copying.']
        error_str = '\n'.join(error_strs)
        raise click.BadParameter(error_str, param_hint='split-video')


class CliContext:
    """ Context of the command-line interface passed between the various sub-commands.

    After processing the main program options in `parse_options`, the CLI will set the options
    passed for each sub-command.  After preparing the commands, their actions are executed by
    the `process_input` method.

    The only other module which should directly access/modify the properties of this class is
    `scenedetect.cli.__init__` (file scenedetect/cli/__init__.py).
    """

    def __init__(self):
        self.logger = logging.getLogger('pyscenedetect')
        self.config = USER_CONFIG

        self.options_processed: bool = False # True when CLI option parsing is complete.
        self.process_input_flag: bool = True # If False, skips video processing.

        self.video_stream: VideoStream = None
        self.base_timecode: FrameTimecode = None
        self.scene_manager: SceneManager = None
        self.stats_manager: StatsManager = None

        # Main `scenedetect` Options
        self.output_directory: str = None        # -o/--output
        self.quiet_mode: bool = False            # -q/--quiet or -v/--verbosity quiet
        self.stats_file_path: str = None         # -s/--stats
        self.drop_short_scenes: bool = False     # --drop-short-scenes
        self.min_scene_len: FrameTimecode = None # -m/--min-scene-len
        self.frame_skip: int = 0                 # -fs/--frame-skip

        # `time` Command Options
        self.time: bool = False
        self.start_time: FrameTimecode = None # time -s/--start
        self.end_time: FrameTimecode = None   # time -e/--end
        self.duration: FrameTimecode = None   # time -d/--duration

        # `save-images` Command Options
        self.save_images: bool = False
        self.image_extension: str = 'jpg' # save-images -j/--jpeg, -w/--webp, -p/--png
        self.image_directory: str = None  # save-images -o/--output
        self.image_param: int = None      # save-images -q/--quality if -j/-w,
                                          #   otherwise -c/--compression if -p
        self.image_name_format: str = (   # save-images -f/--name-format
            '$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER')
        self.num_images: int = 3          # save-images -n/--num-images
        self.frame_margin: int = 1        # save-images -m/--frame-margin
        self.scale: float = None          # save-images -s/--scale
        self.height: int = None           # save-images -h/--height
        self.width: int = None            # save-images -w/--width

        # `split-video` Command Options
        self.split_video: bool = False
        self.split_mkvmerge: bool = False # split-video -m/--mkvmerge
        self.split_args: str = None       # split-video -a/--override-args, -c/--copy
        self.split_directory: str = None  # split-video -o/--output
        self.split_name_format: str = (   # split-video -f/--filename
            '$VIDEO_NAME-Scene-$SCENE_NUMBER')
        self.split_quiet: bool = False    # split-video -q/--quiet

        # `list-scenes` Command Options
        self.list_scenes: bool = False
        self.print_scene_list: bool = False     # list-scenes -q/--quiet
        self.scene_list_directory: str = None   # list-scenes -o/--output
        self.scene_list_name_format: str = None # list-scenes -f/--filename
        self.scene_list_output: bool = False    # list-scenes -n/--no-output
        self.skip_cuts: bool = False            # list-scenes -s/--skip-cuts

        # `export-html` Command Options
        self.export_html: bool = False
        self.html_name_format: str = None     # export-html -f/--filename
        self.html_include_images: bool = True # export-html --no-images
        self.image_width: int = None          # export-html -w/--image-width
        self.image_height: int = None         # export-html -h/--image-height

        # Internal variables
        self._check_input_open_failed = False # Used to avoid excessive log messages

    def parse_options(self, input_path: str, output: Optional[str], framerate: float,
                      stats_file: Optional[str], downscale: Optional[int], frame_skip: int,
                      min_scene_len: str, drop_short_scenes: bool, backend: str, quiet: bool,
                      logfile: Optional[str], config: Optional[str], stats: Optional[str],
                      verbosity: str):
        """ Parse Options: Parses all global options/arguments passed to the main
        scenedetect command, before other sub-commands (e.g. this function processes
        the [options] when calling scenedetect [options] [commands [command options]].

        This method calls the _init_video_stream(), _open_stats_file(), and
        check_input_open() methods, which may raise a click.BadParameter exception.

        Raises:
            click.BadParameter
        """

        # TODO(v1.0): Make the stats value optional (e.g. allow -s only), and allow use of
        # $VIDEO_NAME macro in the name.  Default to $VIDEO_NAME.csv.

        logging.disable(logging.NOTSET)

        verbosity = getattr(logging, verbosity.upper()) if verbosity is not None else None
        init_logger(log_level=verbosity, show_stdout=not quiet, log_file=logfile)
        self.logger.info('PySceneDetect %s', scenedetect.__version__)

        # TODO(#247): Need to set verbosity default to None and allow the case where quiet-mode=True
        # in the config, but -v debug is specified.
        self.quiet_mode = True if quiet else False
        self.output_directory = output

        # Replace the user configuration if -c/--config was specified.
        # TODO: Don't modify USER_CONFIG, just create a new one in CliContext and reference this one
        # when required.
        if config:
            try:
                new_config = ConfigRegistry(config)
            except ConfigLoadFailure as ex:
                for (log_level, log_str) in ex.init_log:
                    self.logger.log(log_level, log_str)
                self.logger.error("Failed to load config file!\n")
                raise click.BadParameter(
                    'Failed to read config file, see log for details.',
                    param_hint='-c/--config') from ex

            self.config = new_config
        for (log_level, log_str) in self.config.get_init_log():
            self.logger.log(log_level, log_str)
        self.logger.debug("Current configuration:\n%s", str(self.config.config_dict))

        if stats is not None and frame_skip != 0:
            self.options_processed = False
            error_strs = [
                'Unable to detect scenes with stats file if frame skip is not 1.',
                '  Either remove the -fs/--frame-skip option, or the -s/--stats file.\n'
            ]
            self.logger.error('\n'.join(error_strs))
            raise click.BadParameter(
                '\n  Combining the -s/--stats and -fs/--frame-skip options is not supported.',
                param_hint='frame skip + stats file')

        if self.output_directory is not None:
            self.logger.info('Output directory set:\n  %s', self.output_directory)

        self.logger.debug('Parsing program options.')

        # Have to load the input video to obtain a time base before parsing timecodes.
        if input_path is None:
            return
        self._init_video_stream(input_path=input_path, framerate=framerate, backend=backend)

        self.min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate)
        self.drop_short_scenes = drop_short_scenes
        self.frame_skip = frame_skip

        # Open StatsManager if --stats is specified.
        if stats_file:
            self._open_stats_file(file_path=stats_file)

        self.logger.debug('Initializing SceneManager.')
        self.scene_manager = SceneManager(self.stats_manager)
        if downscale is None:
            self.scene_manager.auto_downscale = True
        else:
            try:
                self.scene_manager.auto_downscale = False
                self.scene_manager.downscale = downscale
            except ValueError as ex:
                self.logger.debug(str(ex))
                raise click.BadParameter(str(ex), param_hint='downscale factor')
        self.options_processed = True

    def process_input(self):
        # type: () -> None
        """ Process Input: Processes input video(s) and generates output as per CLI commands.

        Run after all command line options/sub-commands have been parsed.
        """
        if not self.process_input_flag:
            self.logger.debug('Skipping processing (process_input_flag is False).')
            return
        if not self.options_processed:
            self.logger.debug('Skipping processing, CLI options were not parsed successfully.')
            return
        self.logger.debug('Processing input...')
        self.check_input_open()
        if self.scene_manager.get_num_detectors() == 0:
            self.logger.error(
                'No scene detectors specified (detect-content, detect-threshold, etc...),\n'
                ' or failed to process all command line arguments.')
            return

        # Display a warning if the video codec type seems unsupported (#86).
        if isinstance(self.video_stream, VideoStreamCv2):
            if int(abs(self.video_stream.capture.get(cv2.CAP_PROP_FOURCC))) == 0:
                self.logger.error(
                    'Video codec detection failed, output may be incorrect.\nThis could be caused'
                    ' by using an outdated version of OpenCV, or using codecs that currently are'
                    ' not well supported (e.g. VP9).\n'
                    'As a workaround, consider re-encoding the source material before processing.\n'
                    'For details, see https://github.com/Breakthrough/PySceneDetect/issues/86')

        self.logger.info('Detecting scenes...')
        perf_start_time = time.time()
        if self.start_time is not None:
            self.video_stream.seek(target=self.start_time)
        num_frames = self.scene_manager.detect_scenes(
            video=self.video_stream,
            duration=self.duration,
            end_time=self.end_time,
            frame_skip=self.frame_skip,
            show_progress=not self.quiet_mode)

        # Handle case where video failure is most likely due to multiple audio tracks (#179).
        if num_frames <= 0:
            self.logger.critical(
                'Failed to read any frames from video file. This could be caused by the video'
                ' having multiple audio tracks. If so, try installing the PyAV backend:\n'
                '      pip install av\n'
                'Or remove the audio tracks by running either:\n'
                '      ffmpeg -i input.mp4 -c copy -an output.mp4\n'
                '      mkvmerge -o output.mkv input.mp4\n'
                'For details, see https://pyscenedetect.readthedocs.io/en/latest/faq/')
            return

        perf_duration = time.time() - perf_start_time
        self.logger.info('Processed %d frames in %.1f seconds (average %.2f FPS).', num_frames,
                         perf_duration,
                         float(num_frames) / perf_duration)

        # Handle -s/--stats option.
        self._save_stats()

        # Get list of detected cuts/scenes from the SceneManager to generate the required output
        # files, based on the given commands (list-scenes, split-video, save-images, etc...).
        cut_list = self.scene_manager.get_cut_list()
        scene_list = self.scene_manager.get_scene_list(start_in_scene=True)

        # Handle --drop-short-scenes.
        if self.drop_short_scenes and self.min_scene_len > 0:
            scene_list = [s for s in scene_list if (s[1] - s[0]) >= self.min_scene_len]

        # Ensure we don't divide by zero.
        if scene_list:
            self.logger.info(
                'Detected %d scenes, average shot length %.1f seconds.', len(scene_list),
                sum([(end_time - start_time).get_seconds() for start_time, end_time in scene_list])
                / float(len(scene_list)))
        else:
            self.logger.info('No scenes detected.')

        # Handle list-scenes command.
        self._list_scenes(scene_list, cut_list)

        # Handle save-images command.
        image_filenames = self._save_images(scene_list)

        # Handle export-html command.
        self._export_html(scene_list, cut_list, image_filenames)

        # Handle split-video command.
        self._split_video(scene_list)

    def check_input_open(self):
        # type: () -> None
        """Ensure self.video_stream was initialized (i.e. -i/--input was specified),
        otherwise raises an exception.

        Raises:
            click.BadParameter if self.video_stream was not initialized.
        """
        if self.video_stream is None:
            if not self._check_input_open_failed:
                self.logger.error('Error: No input video was specified.')
            self._check_input_open_failed = True
            raise click.BadParameter('Input video not set.', param_hint='-i/--input')

    def add_detector(self, detector):
        """ Add Detector: Adds a detection algorithm to the CliContext's SceneManager. """
        self.check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False
        try:
            self.scene_manager.add_detector(detector)
        except scenedetect.stats_manager.FrameMetricRegistered:
            raise click.BadParameter(
                message='Cannot specify detection algorithm twice.', param_hint=detector.cli_name)
        self.options_processed = options_processed_orig

    def _init_video_stream(self, input_path: str, framerate: Optional[float], backend: str):
        self.base_timecode = None
        try:
            if not backend in AVAILABLE_BACKENDS:
                raise click.BadParameter(
                    'Specified backend is not available on this system!', param_hint='-b/--backend')
            self.logger.debug('Using backend: %s / %s', backend,
                              AVAILABLE_BACKENDS[backend].__name__)
            self.video_stream = AVAILABLE_BACKENDS[backend](input_path, framerate)
            self.base_timecode = self.video_stream.base_timecode
        except VideoOpenFailure as ex:
            dll_okay, dll_name = check_opencv_ffmpeg_dll()
            if dll_okay:
                self.logger.error('Backend failed to open video: %s', str(ex))
            else:
                self.logger.error(
                    'Error: OpenCV dependency %s not found.'
                    ' Ensure that you installed the Python OpenCV module, and that the'
                    ' %s file can be found to enable video support.', dll_name, dll_name)
                # Add additional output message in red.
                click.echo(
                    click.style(
                        '\nOpenCV dependency missing, video input/decoding not available.\n',
                        fg='red'))
            raise click.BadParameter('Failed to open video!', param_hint='-i/--input')
        except IOError as ex:
            raise click.BadParameter('Input error:\n\n\t%s\n' % str(ex), param_hint='-i/--input')

        if self.video_stream.frame_rate < MAX_FPS_DELTA:
            raise click.BadParameter(
                'Failed to obtain framerate for input video. Manually specify framerate with the'
                ' -f/--framerate option, or try re-encoding the file.',
                param_hint='-i/--input')

    def _open_stats_file(self, file_path: str):
        """Initializes this object's StatsManager, loading any existing stats from disk.
        If the file does not already exist, all directories leading up to it's eventual location
        will be created here."""
        self.stats_file_path = get_and_create_path(file_path, self.output_directory)
        self.stats_manager = StatsManager()

        self.logger.info('Loading frame metrics from stats file: %s',
                         os.path.basename(self.stats_file_path))
        try:
            self.stats_manager.load_from_csv(self.stats_file_path)
        except StatsFileCorrupt:
            error_info = (
                'Could not load frame metrics from stats file - file is either corrupt,'
                ' or not a valid PySceneDetect stats file. If the file exists, ensure that'
                ' it is a valid stats file CSV, otherwise delete it and run PySceneDetect'
                ' again to re-generate the stats file.')
            error_strs = ['Could not load stats file.', 'Failed to parse stats file:', error_info]
            self.logger.error('\n'.join(error_strs))
            # pylint: disable=raise-missing-from
            raise click.BadParameter(
                '\n  Could not load given stats file, see above output for details.',
                param_hint='input stats file')

    def save_images_command(self, num_images: int, output: Optional[str], name_format: str,
                            jpeg: bool, webp: bool, quality: int, png: bool, compression: int,
                            frame_margin: int, scale: float, height: int, width: int):
        """ Save Images Command: Parses all options/arguments passed to the save-images command,
        or with respect to the CLI, this function processes [save-images options] when calling:
        scenedetect [global options] save-images [save-images options] [other commands...].

        Raises:
            click.BadParameter
        """
        self.check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False

        if contains_sequence_or_url(self.video_stream.path):
            error_str = '\nThe save-images command is incompatible with image sequences/URLs.'
            self.logger.error(error_str)
            raise click.BadParameter(error_str, param_hint='save-images')

        num_flags = sum([1 if flag else 0 for flag in [jpeg, webp, png]])
        if num_flags <= 1:

            # Ensure the format exists (default is JPEG).
            extension = 'jpg'
            if png:
                extension = 'png'
            elif webp:
                extension = 'webp'
            valid_params = get_cv2_imwrite_params()
            if not extension in valid_params or valid_params[extension] is None:
                error_strs = [
                    'Image encoder type %s not supported.' % extension.upper(),
                    'The specified encoder type could not be found in the current OpenCV module.',
                    'To enable this output format, please update the installed version of OpenCV.',
                    'If you build OpenCV, ensure the the proper dependencies are enabled. '
                ]
                self.logger.debug('\n'.join(error_strs))
                raise click.BadParameter('\n'.join(error_strs), param_hint='save-images')

            self.save_images = True
            self.image_directory = output
            self.image_extension = extension
            self.image_param = compression if png else quality
            self.image_name_format = name_format
            self.num_images = num_images
            self.frame_margin = frame_margin
            self.scale = scale
            self.height = height
            self.width = width

            image_type = 'JPEG' if self.image_extension == 'jpg' else self.image_extension.upper()
            image_param_type = ''
            if self.image_param:
                image_param_type = 'Compression' if image_type == 'PNG' else 'Quality'
                image_param_type = ' [%s: %d]' % (image_param_type, self.image_param)
            self.logger.info('Image output format set: %s%s', image_type, image_param_type)
            if self.image_directory is not None:
                self.logger.info('Image output directory set:\n  %s',
                                 os.path.abspath(self.image_directory))
            self.options_processed = options_processed_orig
        else:
            self.logger.error('Multiple image type flags set for save-images command.')
            raise click.BadParameter(
                'Only one image type (JPG/PNG/WEBP) can be specified.', param_hint='save-images')

    def _save_stats(self) -> None:
        """Handles saving the statsfile if -s/--stats was specified."""
        if self.stats_file_path is not None:
            # We check if the save is required in order to reduce unnecessary log messages.
            if self.stats_manager.is_save_required():
                self.logger.info('Saving frame metrics to stats file: %s',
                                 os.path.basename(self.stats_file_path))
                self.stats_manager.save_to_csv(
                    path=self.stats_file_path, base_timecode=self.video_stream.base_timecode)
            else:
                self.logger.debug('No frame metrics updated, skipping update of the stats file.')

    def _list_scenes(self, scene_list: List[Tuple[FrameTimecode, FrameTimecode]],
                     cut_list: List[FrameTimecode]) -> None:
        """Handles the `list-scenes` command."""
        if self.scene_list_output:
            scene_list_filename = Template(
                self.scene_list_name_format).safe_substitute(VIDEO_NAME=self.video_stream.name)
            if not scene_list_filename.lower().endswith('.csv'):
                scene_list_filename += '.csv'
            scene_list_path = get_and_create_path(
                scene_list_filename, self.scene_list_directory
                if self.scene_list_directory is not None else self.output_directory)
            self.logger.info('Writing scene list to CSV file:\n  %s', scene_list_path)
            with open(scene_list_path, 'wt') as scene_list_file:
                write_scene_list(
                    output_csv_file=scene_list_file,
                    scene_list=scene_list,
                    include_cut_list=not self.skip_cuts,
                    cut_list=cut_list)

        if self.print_scene_list:
            self.logger.info(
                """Scene List:
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
%s
-----------------------------------------------------------------------
""", '\n'.join([
                    ' |  %5d  | %11d | %s | %11d | %s |' %
                    (i + 1, start_time.get_frames(), start_time.get_timecode(),
                     end_time.get_frames(), end_time.get_timecode())
                    for i, (start_time, end_time) in enumerate(scene_list)
                ]))

        if cut_list:
            self.logger.info('Comma-separated timecode list:\n  %s',
                             ','.join([cut.get_timecode() for cut in cut_list]))

    # TODO(v0.6): Test save-images output matches the frames from v0.5.x.
    def _save_images(
            self, scene_list: List[Tuple[FrameTimecode,
                                         FrameTimecode]]) -> Optional[Dict[int, List[str]]]:
        """Handles the `save-images` command."""
        if not self.save_images:
            return None

        image_output_dir = self.output_directory
        if self.image_directory is not None:
            image_output_dir = self.image_directory

        return save_images(
            scene_list=scene_list,
            video=self.video_stream,
            num_images=self.num_images,
            frame_margin=self.frame_margin,
            image_extension=self.image_extension,
            encoder_param=self.image_param,
            image_name_template=self.image_name_format,
            output_dir=image_output_dir,
            show_progress=not self.quiet_mode,
            scale=self.scale,
            height=self.height,
            width=self.width)

    def _export_html(self, scene_list: List[Tuple[FrameTimecode,
                                                  FrameTimecode]], cut_list: List[FrameTimecode],
                     image_filenames: Optional[Dict[int, List[str]]]) -> None:
        """Handles the `export-html` command."""
        if not self.export_html:
            return

        html_filename = Template(
            self.html_name_format).safe_substitute(VIDEO_NAME=self.video_stream.name)
        if not html_filename.lower().endswith('.html'):
            html_filename += '.html'
        html_path = get_and_create_path(
            html_filename,
            self.image_directory if self.image_directory is not None else self.output_directory)
        self.logger.info('Exporting to html file:\n %s:', html_path)
        if not self.html_include_images:
            image_filenames = None
        write_scene_list_html(
            html_path,
            scene_list,
            cut_list,
            image_filenames=image_filenames,
            image_width=self.image_width,
            image_height=self.image_height)

    def _split_video(self, scene_list: List[Tuple[FrameTimecode, FrameTimecode]]) -> None:
        """Handles the `split-video` command."""
        if not self.split_video:
            return

        output_path_template = self.split_name_format
        # Add proper extension to filename template if required.
        dot_pos = output_path_template.rfind('.')
        extension_length = 0 if dot_pos < 0 else len(output_path_template) - (dot_pos + 1)
        # If using mkvmerge, force extension to .mkv.
        if self.split_mkvmerge and not output_path_template.endswith('.mkv'):
            output_path_template += '.mkv'
        # Otherwise, if using ffmpeg, only add an extension if one doesn't exist.
        elif not 2 <= extension_length <= 4:
            output_path_template += '.mp4'
        output_path_template = get_and_create_path(
            output_path_template,
            self.split_directory if self.split_directory is not None else self.output_directory)
        # Ensure the appropriate tool is available before handling split-video.
        check_split_video_requirements(self.split_mkvmerge)
        if self.split_mkvmerge:
            split_video_mkvmerge(
                self.video_stream.path,
                scene_list,
                output_path_template,
                show_output=not (self.quiet_mode or self.split_quiet),
            )
        else:
            split_video_ffmpeg(
                self.video_stream.path,
                scene_list,
                output_path_template,
                arg_override=self.split_args,
                show_progress=not self.quiet_mode,
                show_output=not (self.quiet_mode or self.split_quiet),
            )
        if scene_list:
            self.logger.info('Video splitting completed, individual scenes written to disk.')
