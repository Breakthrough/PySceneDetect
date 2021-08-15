# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2021 Brandon Castellano <http://www.bcastell.com>.
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

""" ``scenedetect.cli.context`` Module

This file contains the implementation of the PySceneDetect command-line
interface (CLI) context class CliContext, used for the main application
state/context and logic to run the PySceneDetect CLI.
"""

# Standard Library Imports
from __future__ import print_function
import logging
import os
import time
from string import Template

# Third-Party Library Imports
import click
import cv2

# PySceneDetect Library Imports
import scenedetect.detectors

from scenedetect.scene_manager import SceneManager
from scenedetect.scene_manager import save_images
from scenedetect.scene_manager import write_scene_list
from scenedetect.scene_manager import write_scene_list_html

from scenedetect.stats_manager import StatsManager
from scenedetect.stats_manager import StatsFileCorrupt

from scenedetect.video_manager import VideoManager
from scenedetect.video_manager import VideoOpenFailure
from scenedetect.video_manager import VideoFramerateUnavailable
from scenedetect.video_manager import VideoParameterMismatch
from scenedetect.video_manager import InvalidDownscaleFactor

from scenedetect.video_splitter import is_mkvmerge_available
from scenedetect.video_splitter import is_ffmpeg_available
from scenedetect.video_splitter import split_video_mkvmerge
from scenedetect.video_splitter import split_video_ffmpeg

from scenedetect.platform import get_cv2_imwrite_params
from scenedetect.platform import check_opencv_ffmpeg_dll
from scenedetect.platform import get_and_create_path

from scenedetect.frame_timecode import FrameTimecode


def parse_timecode(cli_ctx, value):
    # type: (CliContext, str) -> Union[FrameTimecode, None]
    """ Parses a user input string expected to be a timecode, given a CLI context.

    Returns:
        (FrameTimecode) Timecode set to value with the CliContext VideoManager framerate.
            If value is None, skips processing and returns None.

    Raises:
        click.BadParameter
     """
    cli_ctx.check_input_open()
    if value is None:
        return value
    try:
        timecode = FrameTimecode(
            timecode=value, fps=cli_ctx.video_manager.get_framerate())
        return timecode
    except (ValueError, TypeError):
        raise click.BadParameter(
            'timecode must be in frames (1234), seconds (123.4s), or HH:MM:SS (00:02:03.400)')


def get_plural(val_list):
    # type: (List[any]) -> str
    """ Get Plural: Helper function to return 's' if a list has more than one (1)
    element, otherwise returns ''.

    Returns:
        str: String of 's' if the length of val_list is greater than 1, otherwise ''.
    """
    return 's' if len(val_list) > 1 else ''


def contains_sequence_or_url(video_paths):
    # type: (List[str]) -> bool
    """ Checks if any of the video paths are a URL or image sequence.

    Arguments:
        video_paths: List of strings.

    Returns: bool: True if any of the video_paths are a URL or image sequence,
        False otherwise.
    """

    return any(['%' in video_path or '://' in video_path
            for video_path in video_paths])


def check_split_video_requirements(use_mkvmerge):
    # type: (bool) -> None
    """ Validates that the proper tool is available on the system to perform the split-video
    command, which depends on if -c/--copy is set (to use mkvmerge) or not (to use ffmpeg).

    Arguments:
        use_mkvmerge: True if -c/--copy is set, False otherwise.

    Raises: click.BadParameter if the proper video splitting tool cannot be found.
    """

    if (use_mkvmerge and not is_mkvmerge_available()) or not is_ffmpeg_available():
        error_strs = [
            "{EXTERN_TOOL} is required for split-video{EXTRA_ARGS}.".format(
                EXTERN_TOOL='mkvmerge' if use_mkvmerge else 'ffmpeg',
                EXTRA_ARGS=' -c/--copy' if use_mkvmerge else '')]
        error_strs += ["Install one of the above tools to enable the split-video command."]
        if not use_mkvmerge and is_mkvmerge_available():
            error_strs += [
                'You can also specify `-c/--copy` to use mkvmerge for splitting.']
        elif use_mkvmerge and is_ffmpeg_available():
            error_strs += [
                'You can also omit `-c/--copy` to use ffmpeg for splitting.']
        error_str = '\n'.join(error_strs)
        raise click.BadParameter(error_str, param_hint='split-video')



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
        self.start_frame = 0                    # time -s/--start
        self.stats_manager = None               # -s/--stats
        self.stats_file_path = None             # -s/--stats
        self.output_directory = None            # -o/--output
        self.quiet_mode = False                 # -q/--quiet or -v/--verbosity quiet
        self.frame_skip = 0                     # -fs/--frame-skip
        self.drop_short_scenes = False          # --drop-short-scenes
        self.min_scene_len = None               # -m/--min-scene-len

        # Properties for save-images command.
        self.save_images = False                # save-images command
        self.image_extension = 'jpg'            # save-images -j/--jpeg, -w/--webp, -p/--png
        self.image_directory = None             # save-images -o/--output

        self.image_param = None                 # save-images -q/--quality if -j/-w,
                                                #   -c/--compression if -p
        self.image_name_format = (              # save-images -f/--name-format
            '$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER')
        self.num_images = 3                     # save-images -n/--num-images
        self.frame_margin = 1                   # save-images -m/--frame-margin
        self.scale = None                       # save-images -s/--scale
        self.height = None                      # save-images -h/--height
        self.width = None                       # save-images -w/--width

        # Properties for split-video command.
        self.split_video = False                # split-video command
        self.split_mkvmerge = False             # split-video -c/--copy
        self.split_args = None                  # split-video -a/--override-args
        self.split_directory = None             # split-video -o/--output
        self.split_name_format = '$VIDEO_NAME-Scene-$SCENE_NUMBER'  # split-video -f/--filename
        self.split_quiet = False                # split-video -q/--quiet

        # Properties for list-scenes command.
        self.list_scenes = False                # list-scenes command
        self.print_scene_list = False           # list-scenes --quiet/-q
        self.scene_list_directory = None        # list-scenes -o/--output
        self.scene_list_name_format = None      # list-scenes -f/--filename
        self.scene_list_output = False          # list-scenes -n/--no-output
        self.skip_cuts = False                  # list-scenes -s/--skip-cuts

        # Properties for export-html command.
        self.export_html = False                # export-html command
        self.html_name_format = None            # export-html -f/--filename
        self.html_include_images = True         # export-html --no-images
        self.image_width = None                 # export-html -w/--image-width
        self.image_height = None                # export-html -h/--image-height

        # Logger for CLI output.
        self.logger = logging.getLogger('pyscenedetect')


    def cleanup(self):
        # type: () -> None
        """ Cleanup: Releases all resources acquired by the CliContext (esp. the VideoManager). """
        try:
            self.logger.debug('Cleaning up...\n\n')
        finally:
            if self.video_manager is not None:
                self.video_manager.release()


    def _open_stats_file(self):

        if self.stats_manager is None:
            self.stats_manager = StatsManager()

        if self.stats_file_path is not None:
            if os.path.exists(self.stats_file_path):
                self.logger.info('Loading frame metrics from stats file: %s',
                             os.path.basename(self.stats_file_path))
                try:
                    with open(self.stats_file_path, 'rt') as stats_file:
                        self.stats_manager.load_from_csv(stats_file)
                except StatsFileCorrupt:
                    error_info = (
                        'Could not load frame metrics from stats file - file is either corrupt,'
                        ' or not a valid PySceneDetect stats file. If the file exists, ensure that'
                        ' it is a valid stats file CSV, otherwise delete it and run PySceneDetect'
                        ' again to re-generate the stats file.')
                    error_strs = [
                        'Could not load stats file.', 'Failed to parse stats file:', error_info ]
                    self.logger.error('\n'.join(error_strs))
                    raise click.BadParameter(
                        '\n  Could not load given stats file, see above output for details.',
                        param_hint='input stats file')


    def process_input(self):
        # type: () -> None
        """ Process Input: Processes input video(s) and generates output as per CLI commands.

        Run after all command line options/sub-commands have been parsed.
        """
        self.logger.debug('Processing input...')
        if not self.options_processed:
            self.logger.debug('Skipping processing, CLI options were not parsed successfully.')
            return
        self.check_input_open()
        assert self.scene_manager.get_num_detectors() >= 0
        if self.scene_manager.get_num_detectors() == 0:
            self.logger.error(
                'No scene detectors specified (detect-content, detect-threshold, etc...),\n'
                ' or failed to process all command line arguments.')
            return

        # Display a warning if the video codec type seems unsupported (#86).
        if int(abs(self.video_manager.get(cv2.CAP_PROP_FOURCC))) == 0:
            self.logger.error(
                'Video codec detection failed, output may be incorrect.\nThis could be caused'
                ' by using an outdated version of OpenCV, or using codecs that currently are'
                ' not well supported (e.g. VP9).\n'
                'As a workaround, consider re-encoding the source material before processing.\n'
                'For details, see https://github.com/Breakthrough/PySceneDetect/issues/86')

        # Handle scene detection commands (detect-content, detect-threshold, etc...).
        self.video_manager.start()

        start_time = time.time()
        self.logger.info('Detecting scenes...')

        num_frames = self.scene_manager.detect_scenes(
            frame_source=self.video_manager, frame_skip=self.frame_skip,
            show_progress=not self.quiet_mode)

        # Handle case where video fails with multiple audio tracks (#179).
        # TODO: Using a different video backend as per #213 may also resolve this issue,
        # as well as numerous other timing related issues.
        if num_frames <= 0:
            self.logger.critical(
                'Failed to read any frames from video file. This could be caused'
                ' by the video having multiple audio tracks. If so, please try'
                ' removing the audio tracks or muxing to mkv via:\n'
                '      ffmpeg -i input.mp4 -c copy -an output.mp4\n'
                'or:\n'
                '      mkvmerge -o output.mkv input.mp4\n'
                'For details, see https://pyscenedetect.readthedocs.io/en/latest/faq/')
            return

        duration = time.time() - start_time
        self.logger.info('Processed %d frames in %.1f seconds (average %.2f FPS).',
                     num_frames, duration, float(num_frames)/duration)

        # Handle -s/--statsfile option.
        if self.stats_file_path is not None:
            if self.stats_manager.is_save_required():
                with open(self.stats_file_path, 'wt') as stats_file:
                    self.logger.info('Saving frame metrics to stats file: %s',
                                 os.path.basename(self.stats_file_path))
                    base_timecode = self.video_manager.get_base_timecode()
                    self.stats_manager.save_to_csv(
                        stats_file, base_timecode)
            else:
                self.logger.debug('No frame metrics updated, skipping update of the stats file.')

        # Get list of detected cuts and scenes from the SceneManager to generate the required output
        # files with based on the given commands (list-scenes, split-video, save-images, etc...).
        cut_list = self.scene_manager.get_cut_list()
        scene_list = self.scene_manager.get_scene_list()

        # Handle --drop-short-scenes.
        if self.drop_short_scenes and self.min_scene_len > 0:
            scene_list = [
                s for s in scene_list
                if (s[1] - s[0]) >= self.min_scene_len
            ]

        video_paths = self.video_manager.get_video_paths()
        video_name = self.video_manager.get_video_name()

        if scene_list:  # Ensure we don't divide by zero.
            self.logger.info('Detected %d scenes, average shot length %.1f seconds.',
                         len(scene_list),
                         sum([(end_time - start_time).get_seconds()
                              for start_time, end_time in scene_list]) / float(len(scene_list)))
        else:
            self.logger.info('No scenes detected.')

        # Handle list-scenes command.
        if self.scene_list_output:
            scene_list_filename = Template(self.scene_list_name_format).safe_substitute(
                VIDEO_NAME=video_name)
            if not scene_list_filename.lower().endswith('.csv'):
                scene_list_filename += '.csv'
            scene_list_path = get_and_create_path(
                scene_list_filename,
                self.scene_list_directory if self.scene_list_directory is not None
                else self.output_directory)
            self.logger.info('Writing scene list to CSV file:\n  %s', scene_list_path)
            with open(scene_list_path, 'wt') as scene_list_file:
                write_scene_list(
                    output_csv_file=scene_list_file,
                    scene_list=scene_list,
                    include_cut_list=not self.skip_cuts,
                    cut_list=cut_list)

        if self.print_scene_list:
            self.logger.info("""Scene List:
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
            self.logger.info('Comma-separated timecode list:\n  %s',
                         ','.join([cut.get_timecode() for cut in cut_list]))

        # Handle save-images command.

        if self.save_images:
            image_output_dir = self.output_directory
            if self.image_directory is not None:
                image_output_dir = self.image_directory

            image_filenames = save_images(
                scene_list=scene_list,
                video_manager=self.video_manager,
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

        # Handle export-html command.
        if self.export_html:
            html_filename = Template(self.html_name_format).safe_substitute(
                VIDEO_NAME=video_name)
            if not html_filename.lower().endswith('.html'):
                html_filename += '.html'
            html_path = get_and_create_path(
                html_filename,
                self.image_directory if self.image_directory is not None
                else self.output_directory)
            self.logger.info('Exporting to html file:\n %s:', html_path)
            if not self.html_include_images:
                image_filenames = None
            write_scene_list_html(html_path, scene_list, cut_list,
                                  image_filenames=image_filenames,
                                  image_width=self.image_width,
                                  image_height=self.image_height)

        # Handle split-video command.
        if self.split_video:
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
                self.split_directory if self.split_directory is not None
                else self.output_directory)
            # Ensure the appropriate tool is available before handling split-video.
            check_split_video_requirements(self.split_mkvmerge)
            if self.split_mkvmerge:
                split_video_mkvmerge(video_paths, scene_list, output_path_template, video_name,
                                     suppress_output=self.quiet_mode or self.split_quiet)
            else:
                split_video_ffmpeg(video_paths, scene_list, output_path_template,
                                   video_name, arg_override=self.split_args,
                                   hide_progress=self.quiet_mode,
                                   suppress_output=self.quiet_mode or self.split_quiet)
            if scene_list:
                self.logger.info('Video splitting completed, individual scenes written to disk.')



    def check_input_open(self):
        # type: () -> None
        """ Check Input Open: Ensures that the CliContext's VideoManager was initialized,
        started, and at *least* one input video was successfully opened - otherwise, an
        exception is raised.

        Raises:
            click.BadParameter
        """
        if self.video_manager is None or not self.video_manager.get_num_videos() > 0:
            error_strs = ["No input video(s) specified.",
                          "Make sure '--input VIDEO' is specified at the start of the command."]
            error_str = '\n'.join(error_strs)
            self.logger.debug(error_str)
            raise click.BadParameter(error_str, param_hint='input video')


    def add_detector(self, detector):
        """ Add Detector: Adds a detection algorithm to the CliContext's SceneManager. """
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

        self.logger.debug('Initializing VideoManager.')
        video_manager_initialized = False
        try:
            self.video_manager = VideoManager(
                video_files=input_list, framerate=framerate, logger=self.logger)
            video_manager_initialized = True
            self.base_timecode = self.video_manager.get_base_timecode()
            self.video_manager.set_downscale_factor(downscale)
        except VideoOpenFailure as ex:
            error_strs = [
                'could not open video%s.' % get_plural(ex.file_list),
                'Failed to open the following video file%s:' % get_plural(ex.file_list)]
            error_strs += ['  %s' % file_name[0] for file_name in ex.file_list]
            dll_okay, dll_name = check_opencv_ffmpeg_dll()
            if not dll_okay:
                error_strs += [
                    'Error: OpenCV dependency %s not found.' % dll_name,
                    'Ensure that you installed the Python OpenCV module, and that the',
                    '%s file can be found to enable video support.' % dll_name]
            self.logger.debug('\n'.join(error_strs[1:]))
            if not dll_okay:
                click.echo(click.style(
                    '\nOpenCV dependency missing, video input/decoding not available.\n', fg='red'))
            raise click.BadParameter('\n'.join(error_strs), param_hint='input video')
        except VideoFramerateUnavailable as ex:
            error_strs = ['could not get framerate from video(s)',
                          'Failed to obtain framerate for video file %s.' % ex.file_name]
            error_strs.append('Specify framerate manually with the -f / --framerate option.')
            self.logger.debug('\n'.join(error_strs))
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
            self.logger.debug('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='input videos')
        except InvalidDownscaleFactor as ex:
            error_strs = ['Downscale value is not > 0.', str(ex)]
            self.logger.debug('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='downscale factor')
        return video_manager_initialized


    def parse_options(self, input_list, framerate, stats_file, downscale, frame_skip,
                      min_scene_len, drop_short_scenes):
        # type: (List[str], float, str, int, int) -> None
        """ Parse Options: Parses all global options/arguments passed to the main
        scenedetect command, before other sub-commands (e.g. this function processes
        the [options] when calling scenedetect [options] [commands [command options]].

        This method calls the _init_video_manager(), _open_stats_file(), and
        check_input_open() methods, which may raise a click.BadParameter exception.

        Raises:
            click.BadParameter
        """
        if not input_list:
            return

        self.logger.debug('Parsing program options.')

        self.frame_skip = frame_skip

        video_manager_initialized = self._init_video_manager(
            input_list=input_list, framerate=framerate, downscale=downscale)

        # Ensure VideoManager is initialized, and open StatsManager if --stats is specified.
        if not video_manager_initialized:
            self.video_manager = None
            self.logger.info('VideoManager not initialized.')
        else:
            self.logger.debug('VideoManager initialized.')
            self.stats_file_path = get_and_create_path(stats_file, self.output_directory)
            if self.stats_file_path is not None:
                self.check_input_open()
                self._open_stats_file()

        # Init SceneManager.
        self.scene_manager = SceneManager(self.stats_manager)

        self.drop_short_scenes = drop_short_scenes
        self.min_scene_len = parse_timecode(self, min_scene_len)

        self.options_processed = True


    def time_command(self, start=None, duration=None, end=None):
        # type: (Optional[str], Optional[str], Optional[str]) -> None
        """ Time Command: Parses all options/arguments passed to the time command,
        or with respect to the CLI, this function processes [time options] when calling:
        scenedetect [global options] time [time options] [other commands...].

        Raises:
            click.BadParameter, VideoDecodingInProgress
        """
        self.logger.debug('Setting video time:\n    start: %s, duration: %s, end: %s',
                      start, duration, end)

        self.check_input_open()

        if duration is not None and end is not None:
            raise click.BadParameter(
                'Only one of --duration/-d or --end/-e can be specified, not both.',
                param_hint='time')

        self.video_manager.set_duration(start_time=start, duration=duration, end_time=end)

        if start is not None:
            self.start_frame = start.get_frames()


    def list_scenes_command(self, output_path, filename_format, no_output_mode,
                            quiet_mode, skip_cuts):
        # type: (str, str, bool, bool) -> None
        """ List Scenes Command: Parses all options/arguments passed to the list-scenes command,
        or with respect to the CLI, this function processes [list-scenes options] when calling:
        scenedetect [global options] list-scenes [list-scenes options] [other commands...].

        Raises:
            click.BadParameter
        """
        self.check_input_open()

        self.print_scene_list = True if quiet_mode is None else not quiet_mode
        self.scene_list_directory = output_path
        self.scene_list_name_format = filename_format
        if self.scene_list_name_format is not None and not no_output_mode:
            self.logger.info('Scene list CSV file name format:\n  %s', self.scene_list_name_format)
        self.scene_list_output = False if no_output_mode else True
        if self.scene_list_directory is not None:
            self.logger.info('Scene list output directory set:\n  %s', self.scene_list_directory)
        self.skip_cuts = skip_cuts


    def export_html_command(self, filename, no_images, image_width, image_height):
        # type: (str, bool) -> None
        """Export HTML command: Parses all options/arguments passed to the export-html command,
        or with respect to the CLI, this function processes [export-html] options when calling:
        scenedetect [global options] export-html [export-html options] [other commands...].

        Raises:
            click.BadParameter
        """
        self.check_input_open()

        self.html_name_format = filename
        if self.html_name_format is not None:
            self.logger.info('Scene list html file name format:\n %s', self.html_name_format)
        self.html_include_images = False if no_images else True
        self.image_width = image_width
        self.image_height = image_height


    def save_images_command(self, num_images, output, name_format, jpeg, webp, quality,
                            png, compression, frame_margin, scale, height, width):
        # type: (int, str, str, bool, bool, int, bool, int, float, int, int) -> None
        """ Save Images Command: Parses all options/arguments passed to the save-images command,
        or with respect to the CLI, this function processes [save-images options] when calling:
        scenedetect [global options] save-images [save-images options] [other commands...].

        Raises:
            click.BadParameter
        """
        self.check_input_open()

        if contains_sequence_or_url(self.video_manager.get_video_paths()):
            self.options_processed = False
            error_str = '\nThe save-images command is incompatible with image sequences/URLs.'
            self.logger.error(error_str)
            raise click.BadParameter(error_str, param_hint='save-images')

        num_flags = sum([1 if flag else 0 for flag in [jpeg, webp, png]])
        if num_flags <= 1:

            # Ensure the format exists.
            extension = 'jpg'   # Default is jpg.
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
                    'If you build OpenCV, ensure the the proper dependencies are enabled. ']
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
        else:
            self.options_processed = False
            self.logger.error('Multiple image type flags set for save-images command.')
            raise click.BadParameter(
                'Only one image type (JPG/PNG/WEBP) can be specified.', param_hint='save-images')
