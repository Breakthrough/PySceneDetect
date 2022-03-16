# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""" ``scenedetect.cli.context`` Module

This module contains :py:class:`CliContext` which encapsulates the command-line options.
"""

from __future__ import print_function
import logging
import os
from typing import AnyStr, Optional, Union

import click

from scenedetect.backends import open_video, AVAILABLE_BACKENDS
from scenedetect.cli.config import ConfigRegistry, ConfigLoadFailure, CHOICE_MAP
from scenedetect.frame_timecode import FrameTimecode, MAX_FPS_DELTA
import scenedetect.detectors
from scenedetect.platform import get_and_create_path, get_cv2_imwrite_params, init_logger
from scenedetect.scene_manager import SceneManager
from scenedetect.stats_manager import StatsManager, StatsFileCorrupt
from scenedetect.video_stream import VideoStream, VideoOpenFailure, FrameRateUnavailable
from scenedetect.video_splitter import is_mkvmerge_available, is_ffmpeg_available

logger = logging.getLogger('pyscenedetect')

USER_CONFIG = ConfigRegistry()


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
    except ValueError as ex:
        raise click.BadParameter(
            'timecode must be in frames (1234), seconds (123.4s), or HH:MM:SS (00:02:03.400)'
        ) from ex


def contains_sequence_or_url(video_path: str) -> bool:
    """Checks if the video path is a URL or image sequence."""
    return '%' in video_path or '://' in video_path


def check_split_video_requirements(use_mkvmerge: bool) -> None:
    # type: (bool) -> None
    """ Validates that the proper tool is available on the system to perform the
    `split-video` command.

    Arguments:
        use_mkvmerge: True if mkvmerge (-m), False otherwise.

    Raises: click.BadParameter if the proper video splitting tool cannot be found.
    """

    if (use_mkvmerge and not is_mkvmerge_available()) or not is_ffmpeg_available():
        error_strs = [
            "{EXTERN_TOOL} is required for split-video{EXTRA_ARGS}.".format(
                EXTERN_TOOL='mkvmerge' if use_mkvmerge else 'ffmpeg',
                EXTRA_ARGS=' when mkvmerge (-m) is set' if use_mkvmerge else '')
        ]
        error_strs += ['Ensure the program is available on your system and try again.']
        if not use_mkvmerge and is_mkvmerge_available():
            error_strs += ['You can specify mkvmerge (-m) to use mkvmerge for splitting.']
        elif use_mkvmerge and is_ffmpeg_available():
            error_strs += ['You can specify copy (-c) to use ffmpeg stream copying.']
        error_str = '\n'.join(error_strs)
        raise click.BadParameter(error_str, param_hint='split-video')


# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-locals
class CliContext:
    """Context of the command-line interface passed between the various sub-commands.

    Handles validation of options taken in from the CLI and configuration files.

    After processing the main program options via `handle_options`, the CLI will then call
    the respective `handle_*` method for each command. Once all commands have been
    processed, the main program actions are executed by passing this object to the
    `run_scenedetect` function in `scenedetect.cli.controller`.
    """

    def __init__(self):
        self.config = USER_CONFIG
        self.options_processed: bool = False # True when CLI option parsing is complete.
        self.process_input_flag: bool = True # If False, skips video processing.

        self.video_stream: VideoStream = None
        self.scene_manager: SceneManager = None
        self.stats_manager: StatsManager = None

        # Main `scenedetect` Options
        self.output_directory: str = None        # -o/--output
        self.quiet_mode: bool = None             # -q/--quiet or -v/--verbosity quiet
        self.stats_file_path: str = None         # -s/--stats
        self.drop_short_scenes: bool = None      # --drop-short-scenes
        self.min_scene_len: FrameTimecode = None # -m/--min-scene-len
        self.frame_skip: int = None              # -fs/--frame-skip

        # `time` Command Options
        self.time: bool = False
        self.start_time: FrameTimecode = None # time -s/--start
        self.end_time: FrameTimecode = None   # time -e/--end
        self.duration: FrameTimecode = None   # time -d/--duration

        # `save-images` Command Options
        self.save_images: bool = False
        self.image_extension: str = None   # save-images -j/--jpeg, -w/--webp, -p/--png
        self.image_directory: str = None   # save-images -o/--output
        self.image_param: int = None       # save-images -q/--quality if -j/-w,
                                           #   otherwise -c/--compression if -p
        self.image_name_format: str = None # save-images -f/--name-format
        self.num_images: int = None        # save-images -n/--num-images
        self.frame_margin: int = 1         # save-images -m/--frame-margin
        self.scale: float = None           # save-images -s/--scale
        self.height: int = None            # save-images -h/--height
        self.width: int = None             # save-images -w/--width

        # `split-video` Command Options
        self.split_video: bool = False
        self.split_mkvmerge: bool = None   # split-video -m/--mkvmerge
        self.split_args: str = None        # split-video -a/--args, -c/--copy
        self.split_directory: str = None   # split-video -o/--output
        self.split_name_format: str = None # split-video -f/--filename
        self.split_quiet: bool = None      # split-video -q/--quiet

        # `list-scenes` Command Options
        self.list_scenes: bool = False
        self.print_scene_list: bool = None      # list-scenes -q/--quiet
        self.scene_list_directory: str = None   # list-scenes -o/--output
        self.scene_list_name_format: str = None # list-scenes -f/--filename
        self.scene_list_output: bool = None     # list-scenes -n/--no-output
        self.skip_cuts: bool = None             # list-scenes -s/--skip-cuts

        # `export-html` Command Options
        self.export_html: bool = False
        self.html_name_format: str = None     # export-html -f/--filename
        self.html_include_images: bool = None # export-html --no-images
        self.image_width: int = None          # export-html -w/--image-width
        self.image_height: int = None         # export-html -h/--image-height

        # Internal variables
        self._check_input_open_failed = False # Used to avoid excessive log messages

    #
    # Command Handlers
    #

    def handle_options(
        self,
        input_path: AnyStr,
        output: Optional[AnyStr],
        framerate: float,
        stats_file: Optional[AnyStr],
        downscale: Optional[int],
        frame_skip: int,
        min_scene_len: str,
        drop_short_scenes: bool,
        backend: Optional[str],
        quiet: bool,
        logfile: Optional[AnyStr],
        config: Optional[AnyStr],
        stats: Optional[AnyStr],
        verbosity: Optional[str],
    ):
        """Parse all global options/arguments passed to the main scenedetect command,
        before other sub-commands (e.g. this function processes the [options] when calling
        `scenedetect [options] [commands [command options]]`).

        Raises:
            click.BadParameter: One of the given options/parameters is invalid.
            click.Abort: Fatal initialization failure.
        """
        self.options_processed = False

        # TODO(v1.0): Make the stats value optional (e.g. allow -s only), and allow use of
        # $VIDEO_NAME macro in the name.  Default to $VIDEO_NAME.csv.

        try:
            init_failure = False
            init_log = self.config.get_init_log()
            self._initialize(config, quiet, verbosity, logfile)
        except ConfigLoadFailure as ex:
            init_failure = True
            init_log += ex.init_log
        finally:
            # Make sure we print the version number even on any kind of init failure.
            logger.info('PySceneDetect %s', scenedetect.__version__)
            init_log += self.config.get_init_log()
            for (log_level, log_str) in init_log:
                logger.log(log_level, log_str)
                # We don't raise an exception if the user configuration fails to load, so
                # we instead look for errors in the init log.
                if log_level >= logging.ERROR:
                    init_failure = True
            if init_failure:
                logger.critical("Error processing configuration file.")
                raise click.Abort()

        logger.debug("Current configuration:\n%s", str(self.config.config_dict))
        logger.debug('Parsing program options.')

        if stats is not None and frame_skip:
            error_strs = [
                'Unable to detect scenes with stats file if frame skip is not 0.',
                '  Either remove the -fs/--frame-skip option, or the -s/--stats file.\n'
            ]
            logger.error('\n'.join(error_strs))
            raise click.BadParameter(
                'Combining the -s/--stats and -fs/--frame-skip options is not supported.',
                param_hint='frame skip + stats file')

        # Handle the case where -i/--input was not specified (e.g. for the `help` command).
        if input_path is None:
            return

        # Have to load the input video to obtain a time base before parsing timecodes.
        self._open_video_stream(
            input_path=input_path,
            framerate=framerate,
            backend=self.config.get_value("global", "backend", backend, ignore_default=True))

        self.output_directory = output if output else self.config.get_value("global", "output")
        if self.output_directory:
            logger.info('Output directory set:\n  %s', self.output_directory)

        self.min_scene_len = parse_timecode(
            min_scene_len if min_scene_len is not None else self.config.get_value(
                "global", "min-scene-len"), self.video_stream.frame_rate)
        self.drop_short_scenes = drop_short_scenes or self.config.get_value(
            "global", "drop-short-scenes")
        self.frame_skip = self.config.get_value("global", "frame-skip", frame_skip)

        # Open StatsManager if --stats is specified.
        if stats_file:
            self._open_stats_file(file_path=stats_file)

        logger.debug('Initializing SceneManager.')
        self.scene_manager = SceneManager(self.stats_manager)
        if downscale is None and self.config.is_default("global", "downscale"):
            self.scene_manager.auto_downscale = True
        else:
            try:
                self.scene_manager.auto_downscale = False
                self.scene_manager.downscale = self.config.get_value("global", "downscale",
                                                                     downscale)
            except ValueError as ex:
                logger.debug(str(ex))
                raise click.BadParameter(str(ex), param_hint='downscale factor')

        self.options_processed = True

    def handle_detect_content(
        self,
        threshold: Optional[float],
        luma_only: bool,
        min_scene_len: Optional[str],
    ):
        """Handle detect-content command options."""
        self._check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False

        if self.drop_short_scenes:
            min_scene_len = 0
        else:
            if min_scene_len is None:
                if self.config.is_default("detect-content", "min-scene-len"):
                    min_scene_len = self.min_scene_len.frame_num
                else:
                    min_scene_len = self.config.get_value("detect-content", "min-scene-len")
            min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate).frame_num

        threshold = self.config.get_value("detect-content", "threshold", threshold)
        luma_only = luma_only or self.config.get_value("detect-content", "luma-only")
        logger.debug(
            'Adding detector: ContentDetector(threshold=%f, min_scene_len=%d, luma_only=%s)',
            threshold, min_scene_len, luma_only)
        self._add_detector(
            scenedetect.detectors.ContentDetector(
                threshold=threshold, min_scene_len=min_scene_len, luma_only=luma_only))

        self.options_processed = options_processed_orig

    def handle_detect_adaptive(
        self,
        threshold: Optional[float],
        min_delta_hsv: Optional[float],
        frame_window: Optional[int],
        luma_only: bool,
        min_scene_len: Optional[str],
    ):
        """Handle detect-adaptive command options."""
        self._check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False

        if self.drop_short_scenes:
            min_scene_len = 0
        else:
            if min_scene_len is None:
                if self.config.is_default("detect-adaptive", "min-scene-len"):
                    min_scene_len = self.min_scene_len.frame_num
                else:
                    min_scene_len = self.config.get_value("detect-adaptive", "min-scene-len")
            min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate).frame_num

        threshold = self.config.get_value("detect-adaptive", "threshold", threshold)
        min_delta_hsv = self.config.get_value("detect-adaptive", "min-delta-hsv", min_delta_hsv)
        frame_window = self.config.get_value("detect-adaptive", "frame-window", frame_window)
        luma_only = luma_only or self.config.get_value("detect-adaptive", "luma-only")

        logger.debug(
            'Adding detector: AdaptiveDetector(threshold=%f, min_delta_hsv=%f,'
            ' min_scene_len=%d, luma_only=%s, frame_window=%d)', threshold, min_delta_hsv,
            min_scene_len, luma_only, frame_window)

        self._add_detector(
            scenedetect.detectors.AdaptiveDetector(
                adaptive_threshold=threshold,
                min_scene_len=min_scene_len,
                min_delta_hsv=min_delta_hsv,
                luma_only=luma_only,
                window_width=frame_window,
            ))

        self.options_processed = options_processed_orig

    def handle_detect_threshold(
        self,
        threshold: Optional[float],
        fade_bias: Optional[float],
        add_last_scene: bool,
        min_scene_len: Optional[str],
    ):
        """Handle detect-threshold command options."""
        self._check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False

        if self.drop_short_scenes:
            min_scene_len = 0
        else:
            if min_scene_len is None:
                if self.config.is_default("detect-threshold", "min-scene-len"):
                    min_scene_len = self.min_scene_len.frame_num
                else:
                    min_scene_len = self.config.get_value("detect-threshold", "min-scene-len")
            min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate).frame_num

        threshold = self.config.get_value("detect-threshold", "threshold", threshold)
        fade_bias = self.config.get_value("detect-threshold", "fade-bias", fade_bias)
        # TODO(v1.0): This cannot be disabled right now.
        add_last_scene = add_last_scene or self.config.get_value("detect-threshold",
                                                                 "add-last-scene")

        logger.debug(
            'Adding detector: ThresholdDetector(threshold=%f, fade_bias=%f,'
            ' min_scene_len=%d, add_last_scene=%s)', threshold, fade_bias, min_scene_len,
            add_last_scene)

        self._add_detector(
            scenedetect.detectors.ThresholdDetector(
                threshold=threshold,
                fade_bias=fade_bias,
                min_scene_len=min_scene_len,
                add_final_scene=add_last_scene,
            ))

        self.options_processed = options_processed_orig

    def handle_export_html(
        self,
        filename: Optional[AnyStr],
        no_images: bool,
        image_width: Optional[int],
        image_height: Optional[int],
    ):
        """Handle `export-html` command options."""
        self._check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False
        if self.export_html:
            self._on_duplicate_command('export_html')

        no_images = no_images or self.config.get_value('export-html', 'no-images')
        self.html_include_images = not no_images

        self.html_name_format = self.config.get_value('export-html', 'filename', filename)
        self.image_width = self.config.get_value('export-html', 'image-width', image_width)
        self.image_height = self.config.get_value('export-html', 'image-height', image_height)

        if not self.save_images and not no_images:
            self.options_processed = False
            raise click.BadArgumentUsage(
                'The export-html command requires that the save-images command\n'
                'is specified before it, unless --no-images is specified.')
        logger.info('HTML file name format:\n %s', filename)

        self.export_html = True

        self.options_processed = options_processed_orig

    def handle_list_scenes(
        self,
        output: Optional[AnyStr],
        filename: Optional[AnyStr],
        no_output_file: bool,
        quiet: bool,
        skip_cuts: bool,
    ):
        """Handle `list-scenes` command options."""
        self._check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False
        if self.list_scenes:
            self._on_duplicate_command('list-scenes')

        self.skip_cuts = skip_cuts or self.config.get_value('list-scenes', 'skip-cuts')
        self.print_scene_list = not (quiet or self.config.get_value('list-scenes', 'quiet'))
        no_output_file = no_output_file or self.config.get_value('list-scenes', 'no-output-file')

        self.scene_list_directory = self.config.get_value(
            'list-scenes', 'output', output, ignore_default=True)
        self.scene_list_name_format = self.config.get_value('list-scenes', 'filename', filename)
        if self.scene_list_name_format is not None and not no_output_file:
            logger.info('Scene list filename format:\n  %s', self.scene_list_name_format)
        self.scene_list_output = not no_output_file
        if self.scene_list_directory is not None:
            logger.info('Scene list output directory:\n  %s', self.scene_list_directory)

        self.list_scenes = True

        self.options_processed = options_processed_orig

    def handle_split_video(
        self,
        output: Optional[AnyStr],
        filename: Optional[AnyStr],
        quiet: bool,
        copy: bool,
        high_quality: bool,
        rate_factor: Optional[int],
        preset: Optional[str],
        args: Optional[str],
        mkvmerge: bool,
    ):
        """Handle `split-video` command options."""
        self._check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False
        if self.split_video:
            self._on_duplicate_command('split-video')

        check_split_video_requirements(use_mkvmerge=mkvmerge)

        if contains_sequence_or_url(self.video_stream.path):
            error_str = 'The split-video command is incompatible with image sequences/URLs.'
            raise click.BadParameter(error_str, param_hint='split-video')

        ##
        ## Common Arguments/Options
        ##

        self.split_video = True
        self.split_quiet = quiet or self.config.get_value('split-video', 'quiet')
        self.split_directory = self.config.get_value(
            'split-video', 'output', output, ignore_default=True)
        if self.split_directory is not None:
            logger.info('Video output path set:  \n%s', self.split_directory)
        self.split_name_format = self.config.get_value('split-video', 'filename', filename)

        # We only load the config values for these flags/options if none of the other
        # encoder flags/options were set via the CLI to avoid any conflicting options
        # (e.g. if the config file sets `high-quality = yes` but `--copy` is specified).
        if not (mkvmerge or copy or high_quality or args or rate_factor or preset):
            mkvmerge = self.config.get_value('split-video', 'mkvmerge')
            copy = self.config.get_value('split-video', 'copy')
            high_quality = self.config.get_value('split-video', 'high-quality')
            rate_factor = self.config.get_value('split-video', 'rate-factor')
            preset = self.config.get_value('split-video', 'preset')
            args = self.config.get_value('split-video', 'args')

        # Disallow certain combinations of flags/options.
        if mkvmerge or copy:
            command = 'mkvmerge (-m)' if mkvmerge else 'copy (-c)'
            if high_quality:
                raise click.BadParameter(
                    'high-quality (-hq) cannot be used with %s' % (command),
                    param_hint='split-video')
            if args:
                raise click.BadParameter(
                    'args (-a) cannot be used with %s' % (command), param_hint='split-video')
            if rate_factor:
                raise click.BadParameter(
                    'rate-factor (crf) cannot be used with %s' % (command),
                    param_hint='split-video')
            if preset:
                raise click.BadParameter(
                    'preset (-p) cannot be used with %s' % (command), param_hint='split-video')

        ##
        ## mkvmerge-Specific Arguments/Options
        ##
        if mkvmerge:
            if copy:
                logger.warning('copy mode (-c) ignored due to mkvmerge mode (-m).')
            self.split_mkvmerge = True
            logger.info('Using mkvmerge for video splitting.')
            self.options_processed = options_processed_orig
            return

        ##
        ## ffmpeg-Specific Arguments/Options
        ##
        if copy:
            args = '-c:v copy -c:a copy'
        elif not args:
            if rate_factor is None:
                rate_factor = 22 if not high_quality else 17
            if preset is None:
                preset = 'veryfast' if not high_quality else 'slow'
            args = ('-c:v libx264 -preset {PRESET} -crf {RATE_FACTOR} -c:a aac'.format(
                PRESET=preset, RATE_FACTOR=rate_factor))

        logger.info('ffmpeg arguments: %s', args)
        self.split_args = args
        if filename:
            logger.info('Output file name format: %s', filename)

        self.options_processed = options_processed_orig

    def handle_save_images(
        self,
        num_images: Optional[int],
        output: Optional[AnyStr],
        filename: Optional[AnyStr],
        jpeg: bool,
        webp: bool,
        quality: Optional[int],
        png: bool,
        compression: Optional[int],
        frame_margin: Optional[int],
        scale: Optional[float],
        height: Optional[int],
        width: Optional[int],
    ):
        """Handle `save-images` command options."""
        self._check_input_open()
        if self.save_images:
            self._on_duplicate_command('save-images')
        options_processed_orig = self.options_processed
        self.options_processed = False

        if contains_sequence_or_url(self.video_stream.path):
            error_str = '\nThe save-images command is incompatible with image sequences/URLs.'
            logger.error(error_str)
            raise click.BadParameter(error_str, param_hint='save-images')

        num_flags = sum([1 if flag else 0 for flag in [jpeg, webp, png]])
        if num_flags > 1:
            logger.error('Multiple image type flags set for save-images command.')
            raise click.BadParameter(
                'Only one image type (JPG/PNG/WEBP) can be specified.', param_hint='save-images')
        # Only use config params for image format if one wasn't specified.
        elif num_flags == 0:
            image_format = self.config.get_value('save-images', 'format').lower()
            jpeg = image_format == 'jpeg'
            webp = image_format == 'webp'
            png = image_format == 'png'

        # Only use config params for scale/height/width if none of them are specified explicitly.
        if scale is None and height is None and width is None:
            self.scale = self.config.get_value('save-images', 'scale')
            self.height = self.config.get_value('save-images', 'height')
            self.width = self.config.get_value('save-images', 'width')
        else:
            self.scale = scale
            self.height = height
            self.width = width

        quality = self.config.get_value('save-images', 'quality', 100 if webp else 95)
        compression = self.config.get_value('save-images', 'compression', compression)
        self.image_param = compression if png else quality

        self.image_extension = 'jpg' if jpeg else 'png' if png else 'webp'
        valid_params = get_cv2_imwrite_params()
        if not self.image_extension in valid_params or valid_params[self.image_extension] is None:
            error_strs = [
                'Image encoder type `%s` not supported.' % self.image_extension.upper(),
                'The specified encoder type could not be found in the current OpenCV module.',
                'To enable this output format, please update the installed version of OpenCV.',
                'If you build OpenCV, ensure the the proper dependencies are enabled. '
            ]
            logger.debug('\n'.join(error_strs))
            raise click.BadParameter('\n'.join(error_strs), param_hint='save-images')

        self.image_directory = self.config.get_value(
            'save-images', 'output', output, ignore_default=True)

        self.image_name_format = self.config.get_value('save-images', 'filename', filename)
        self.num_images = self.config.get_value('save-images', 'num-images', num_images)
        self.frame_margin = self.config.get_value('save-images', 'frame-margin', frame_margin)

        image_type = ('jpeg' if jpeg else self.image_extension).upper()
        image_param_type = 'Compression' if png else 'Quality'
        image_param_type = ' [%s: %d]' % (image_param_type, self.image_param)
        logger.info('Image output format set: %s%s', image_type, image_param_type)
        if self.image_directory is not None:
            logger.info('Image output directory set:\n  %s', os.path.abspath(self.image_directory))

        self.save_images = True

        self.options_processed = options_processed_orig

    def handle_time(self, start, duration, end):
        """Handle `time` command options."""
        self._check_input_open()
        options_processed_orig = self.options_processed
        self.options_processed = False
        if self.time:
            self._on_duplicate_command('time')

        if duration is not None and end is not None:
            raise click.BadParameter(
                'Only one of --duration/-d or --end/-e can be specified, not both.',
                param_hint='time')

        logger.debug('Setting video time:\n    start: %s, duration: %s, end: %s', start, duration,
                     end)

        self.start_time = parse_timecode(start, self.video_stream.frame_rate)
        self.end_time = parse_timecode(end, self.video_stream.frame_rate)
        self.duration = parse_timecode(duration, self.video_stream.frame_rate)
        self.time = True

        self.options_processed = options_processed_orig

    #
    # Private Methods
    #

    def _initialize(
        self,
        config: Optional[str],
        quiet: Optional[bool],
        verbosity: Optional[str],
        logfile: Optional[AnyStr],
    ):
        """Setup logging and load application configuration file."""
        self.quiet_mode = bool(quiet)
        curr_verbosity = logging.INFO
        # Convert verbosity into it's log level enum, and override quiet mode if set.
        if verbosity is not None:
            assert verbosity in CHOICE_MAP['global']['verbosity']
            if verbosity.lower() == 'none':
                self.quiet_mode = True
                verbosity = 'info'
            else:
                # Override quiet mode if verbosity is set.
                self.quiet_mode = False
            curr_verbosity = getattr(logging, verbosity.upper())
        else:
            verbosity_str = USER_CONFIG.get_value('global', 'verbosity')
            assert verbosity_str in CHOICE_MAP['global']['verbosity']
            if verbosity_str.lower() == 'none':
                self.quiet_mode = True
            else:
                curr_verbosity = getattr(logging, verbosity_str.upper())
                # Override quiet mode if verbosity is set.
                if not USER_CONFIG.is_default('global', 'verbosity'):
                    self.quiet_mode = False

        init_logger(log_level=curr_verbosity, show_stdout=not self.quiet_mode, log_file=logfile)

        # Configuration file was specified via CLI argument -c/--config.
        if config:
            new_config = ConfigRegistry(config)
            self.config = new_config
            # Re-initialize logger with the correct verbosity.
            if verbosity is None and not self.config.is_default('global', 'verbosity'):
                verbosity_str = self.config.get_value('global', 'verbosity')
                assert verbosity_str in CHOICE_MAP['global']['verbosity']
                curr_verbosity = getattr(logging, verbosity_str.upper())
                self.quiet_mode = False
                init_logger(
                    log_level=curr_verbosity, show_stdout=not self.quiet_mode, log_file=logfile)

    def _add_detector(self, detector):
        """ Add Detector: Adds a detection algorithm to the CliContext's SceneManager. """
        self._check_input_open()
        try:
            self.scene_manager.add_detector(detector)
        except scenedetect.stats_manager.FrameMetricRegistered as ex:
            raise click.BadParameter(
                message='Cannot specify detection algorithm twice.',
                param_hint=detector.cli_name) from ex

    def _check_input_open(self) -> None:
        """Ensure self.video_stream was initialized (i.e. -i/--input was specified),
        otherwise raises an exception. Should only be used from commands that require an
        input video to process the options (e.g. those that require a timecode).

        Raises:
            click.BadParameter: self.video_stream was not initialized.
        """
        if self.video_stream is None:
            if not self._check_input_open_failed:
                logger.error('Error: No input video (-i/--input) was specified.')
            self._check_input_open_failed = True
            self.options_processed = False
            raise click.Abort()

    def _open_video_stream(self, input_path: AnyStr, framerate: Optional[float],
                           backend: Optional[str]):
        if framerate is not None and framerate < MAX_FPS_DELTA:
            raise click.BadParameter('Invalid framerate specified!', param_hint='-f/--framerate')
        try:
            if backend is not None:
                if not backend in AVAILABLE_BACKENDS:
                    raise click.BadParameter(
                        'Specified backend %s is not available on this system!' % backend,
                        param_hint='-b/--backend')
                self.video_stream = AVAILABLE_BACKENDS[backend](input_path, framerate)
            else:
                self.video_stream = open_video(path=input_path, framerate=framerate, backend='pyav')
            logger.debug('Video opened using backend %s', type(self.video_stream).__name__)
        except FrameRateUnavailable as ex:
            raise click.BadParameter(
                'Failed to obtain framerate for input video. Manually specify framerate with the'
                ' -f/--framerate option, or try re-encoding the file.',
                param_hint='-i/--input') from ex
        except VideoOpenFailure as ex:
            raise click.BadParameter(
                'Failed to open input video%s: %s' %
                (' using %s backend' % backend if backend else '', str(ex)),
                param_hint='-i/--input') from ex
        except OSError as ex:
            raise click.BadParameter('Input error:\n\n\t%s\n' % str(ex), param_hint='-i/--input')

    def _open_stats_file(self, file_path: str):
        """Initializes this object's StatsManager, loading any existing stats from disk.
        If the file does not already exist, all directories leading up to it's eventual
        location will be created here."""
        self.stats_file_path = get_and_create_path(file_path, self.output_directory)
        self.stats_manager = StatsManager()

        logger.info('Loading frame metrics from stats file: %s',
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
            logger.error('\n'.join(error_strs))
            # pylint: disable=raise-missing-from
            raise click.BadParameter(
                '\n  Could not load given stats file, see above output for details.',
                param_hint='input stats file')

    def _on_duplicate_command(self, command: str) -> None:
        """Called when a command is duplicated to stop parsing and raise an error.

        Arguments:
            command: Command that was duplicated for error context.

        Raises:
            click.BadParameter
        """
        self.options_processed = False
        error_strs = []
        error_strs.append('Error: Command %s specified multiple times.' % command)
        error_strs.append('The %s command may appear only one time.')

        logger.error('\n'.join(error_strs))
        raise click.BadParameter(
            '\n  Command %s may only be specified once.' % command,
            param_hint='%s command' % command)
