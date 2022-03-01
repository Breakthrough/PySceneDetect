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

""" ``scenedetect.cli`` Module

This file contains the implementation of the PySceneDetect command-line
interface (CLI) parser logic for the PySceneDetect application ("business logic"),
which uses the click library. The main CLI entry-point function is the
function scenedetect_cli, which is a chained command group.

The scenedetect.cli module coordinates first parsing all actions to take and
their validity, storing them in the CliContext, finally performing scene
detection only after the input videos have been loaded and all CLI arguments
parsed and validated.

Some of this parsing functionality is shared between the scenedetect.cli
module and the scenedetect.cli.CliContext object.
"""

from __future__ import print_function
import logging

import click

import scenedetect
from scenedetect.backends import AVAILABLE_BACKENDS
from scenedetect.cli.config import CONFIG_FILE_PATH, CHOICE_MAP
from scenedetect.cli.controller import check_split_video_requirements
from scenedetect.cli.context import (
    USER_CONFIG, CliContext,
    # TODO(v0.6): Move usages of these functions inside of CliContext.
    contains_sequence_or_url, parse_timecode)
from scenedetect.cli.controller import run_scenedetect

logger = logging.getLogger('pyscenedetect')


def get_help_command_preface(command_name='scenedetect'):
    """ Preface/intro help message shown at the beginning of the help command. """
    return """
The PySceneDetect command-line interface is grouped into commands which
can be combined together, each containing its own set of arguments:

 > {command_name} ([options]) [command] ([options]) ([...other command(s)...])

Where [command] is the name of the command, and ([options]) are the
arguments/options associated with the command, if any. Options
associated with the {command_name} command below (e.g. --input,
--framerate) must be specified before any commands. The order of
commands is not strict, but each command should only be specified once.

Commands can also be combined, for example, running the 'detect-content'
and 'list-scenes' (specifying options for the latter):

 > {command_name} -i vid0001.mp4 detect-content list-scenes -n

A list of all commands is printed below. Help for a particular command
can be printed by specifying 'help [command]', or 'help all' to print
the help information for every command.

Lastly, there are several commands used for displaying application
version and copyright information (e.g. {command_name} about):

    version: Displays the version of PySceneDetect being used.
    about:   Displays PySceneDetect license and copyright information.
""".format(**{'command_name': command_name})


CLICK_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

COMMAND_DICT = []


def add_cli_command(cli, command):
    """Adds the CLI command to the cli object as well as to the COMMAND_DICT."""
    cli.add_command(command)
    COMMAND_DICT.append(command)


def print_command_help(ctx: click.Context, command):
    """ Print Command Help: Prints PySceneDetect help/usage for a given command. """
    ctx_name = ctx.info_name
    ctx.info_name = command.name
    click.echo(click.style('PySceneDetect %s Command' % command.name, fg='cyan'))
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(command.get_help(ctx))
    click.echo('')
    ctx.info_name = ctx_name


def print_command_list_header() -> None:
    """ Print Command List Header: Prints header shown before the option/command list. """
    click.echo(click.style('PySceneDetect Option/Command List:', fg='green'))
    click.echo(click.style('----------------------------------------------------', fg='green'))
    click.echo('')


def print_help_header() -> None:
    """ Print Help Header: Prints header shown before the help command. """
    click.echo(click.style('----------------------------------------------------', fg='yellow'))
    click.echo(click.style(' PySceneDetect %s Help' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='yellow'))


def duplicate_command(ctx: click.Context, param_hint: str) -> None:
    """ Duplicate Command: Called when a command is duplicated to stop parsing and raise an error.

    Called when a one-time use command is specified multiple times, displaying the appropriate
    error and usage information.

    Raises:
        click.BadParameter
    """
    assert isinstance(ctx.obj, CliContext)

    ctx.obj.options_processed = False
    error_strs = []
    error_strs.append('Error: Command %s specified multiple times.' % param_hint)
    error_strs.append('The %s command may appear only one time.')

    logger.error('\n'.join(error_strs))
    raise click.BadParameter('\n  Command %s may only be specified once.' % param_hint,
                             param_hint='%s command' % param_hint)



@click.group(
    chain=True, context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    '--input', '-i',
    multiple=False, required=False, metavar='VIDEO',
    type=click.STRING, help=
    '[Required] Input video file. Also supports image sequences and URLs.')
@click.option(
    '--output', '-o',
    multiple=False, required=False, metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=True), help=
    'Output directory for all files (stats file, output videos, images, log files, etc...)'
    ' If not set defaults to working directory. Some commands allow overriding this value.')
@click.option(
    '--framerate', '-f', metavar='FPS',
    type=click.FLOAT, default=None, help=
    'Force framerate, in frames/sec (e.g. -f 29.97). Disables check to ensure that all'
    ' input videos have the same framerates.')
@click.option(
    '--downscale', '-d', metavar='N',
    type=click.INT, default=None, help=
    'Integer factor to downscale frames by (e.g. 2, 3, 4...), where the frame is scaled'
    ' to width/N x height/N (thus -d 1 implies no downscaling). Each increment speeds up processing'
    ' by a factor of 4 (e.g. -d 2 is 4 times quicker than -d 1). Higher values can be used for'
    ' high definition content with minimal effect on accuracy.'
    ' [default: 2 for SD, 4 for 720p, 6 for 1080p, 12 for 4k]')
@click.option(
    '--frame-skip', '-fs', metavar='N', show_default=True,
    type=click.INT, default=0, help=
    'Skips N frames during processing (-fs 1 skips every other frame, processing 50% of the video,'
    ' -fs 2 processes 33% of the frames, -fs 3 processes 25%, etc...).'
    ' Reduces processing speed at expense of accuracy.')
@click.option(
    '--min-scene-len', '-m', metavar='TIMECODE',
    type=click.STRING, default='0.6s', show_default=True, help=
    'Minimum length of any scene. TIMECODE can be specified as exact'
    ' number of frames, a time in seconds followed by s, or a timecode in the'
    ' format HH:MM:SS or HH:MM:SS.nnn')
@click.option(
    '--drop-short-scenes', is_flag=True, flag_value=True, help=
    'Drop scenes shorter than `--min-scene-len` instead of combining them with neighbors')
@click.option(
    '--stats', '-s', metavar='CSV',
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False), help=
    'Path to stats file (.csv) for writing frame metrics to. If the file exists, any'
    ' metrics will be processed, otherwise a new file will be created. Can be used to determine'
    ' optimal values for various scene detector options, and to cache frame calculations in order'
    ' to speed up multiple detection runs.')
@click.option(
    '--verbosity', '-v', metavar='LEVEL',
    type=click.Choice(CHOICE_MAP['global']['verbosity'], False), default=None, help=
    'Level of debug/info/error information to show. Overrides `-q`/`--quiet`.'
    ' Must be one of: debug, info, warning, error.%s' % USER_CONFIG.get_help_string("global", "verbosity"))
@click.option(
    '--logfile', '-l', metavar='LOG',
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False), help=
    'Path to log file for writing application logging information, mainly for debugging.'
    ' Make sure to set `-v debug` as well if you are submitting a bug report.')
@click.option(
    '--quiet', '-q',
    is_flag=True, flag_value=True, help=
    'Suppresses all output of PySceneDetect to the terminal/stdout. If a logfile is'
    ' specified, it will still be generated with the specified verbosity.')
@click.option(
    '--backend', '-b', metavar='BACKEND', show_default=True,
    type=click.Choice([key for key in AVAILABLE_BACKENDS.keys()]), default='opencv', help=
    'Name of backend to use. Backends available on this system: %s' % str(
        [key for key in AVAILABLE_BACKENDS.keys()]))
@click.option(
    '--config', '-c', metavar='FILE',
    type=click.Path(exists=False, file_okay=True, readable=True, resolve_path=False), help=
    'Path to config file. If not set, tries to load one from %s' % (CONFIG_FILE_PATH))
@click.pass_context
# pylint: disable=redefined-builtin
def scenedetect_cli(ctx: click.Context, input, output, framerate, downscale, frame_skip,
                    min_scene_len, drop_short_scenes, stats,
                    verbosity, logfile, quiet, backend, config):
    """ For example:

    scenedetect -i video.mp4 -s video.stats.csv detect-content list-scenes

    Note that the following options represent [OPTIONS] above. To list the optional
    [ARGS] for a particular COMMAND, type `scenedetect help COMMAND`. You can also
    combine commands (e.g. scenedetect [...] detect-content save-images --png split-video).


    """
    assert isinstance(ctx.obj, CliContext)

    ctx.call_on_close(lambda: run_scenedetect(ctx.obj))
    ctx.obj.parse_options(
        input_path=input,
        output=output,
        framerate=framerate,
        stats_file=stats,
        downscale=downscale,
        frame_skip=frame_skip,
        min_scene_len=min_scene_len,
        drop_short_scenes=drop_short_scenes,
        backend=backend,
        quiet=quiet,
        logfile=logfile,
        config=config,
        stats=stats,
        verbosity=verbosity,
    )

@click.command('help', add_help_option=False)
@click.argument('command_name', required=False, type=click.STRING)
@click.pass_context
def help_command(ctx, command_name):
    """Print help for command (help [command])."""
    assert isinstance(ctx.obj, CliContext)

    ctx.obj.process_input_flag = False
    if command_name is not None:
        if command_name.lower() == 'all':
            print_help_header()
            click.echo(get_help_command_preface(ctx.parent.info_name))
            print_command_list_header()
            click.echo(ctx.parent.get_help())
            click.echo('')
            for command in COMMAND_DICT:
                print_command_help(ctx, command)
        else:
            command = None
            for command_ref in COMMAND_DICT:
                if command_name == command_ref.name:
                    command = command_ref
                    break
            if command is None:
                error_strs = [
                    'unknown command.', 'List of valid commands:',
                    '  %s' % ', '.join([command.name for command in COMMAND_DICT])]
                raise click.BadParameter('\n'.join(error_strs), param_hint='command name')
            click.echo('')
            print_command_help(ctx, command)
    else:
        print_help_header()
        click.echo(get_help_command_preface(ctx.parent.info_name))
        print_command_list_header()
        click.echo(ctx.parent.get_help())
        click.echo(
            "\nType '%s help [command]' for usage/help of [command], or" % ctx.parent.info_name)
        click.echo(
            "'%s help all' to list usage information for every command." % (ctx.parent.info_name))
    ctx.exit()



@click.command('about', add_help_option=False)
@click.pass_context
def about_command(ctx):
    """ Print license/copyright info. """
    assert isinstance(ctx.obj, CliContext)

    ctx.obj.process_input_flag = False
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(click.style(' About PySceneDetect %s' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(scenedetect.ABOUT_STRING)
    ctx.exit()



@click.command('version', add_help_option=False)
@click.pass_context
def version_command(ctx):
    """ Print version of PySceneDetect. """
    assert isinstance(ctx.obj, CliContext)

    ctx.obj.process_input_flag = False
    click.echo(click.style('PySceneDetect %s' % scenedetect.__version__, fg='yellow'))
    ctx.exit()



@click.command('time')
@click.option(
    '--start', '-s', metavar='TIMECODE',
    type=click.STRING, default='0', show_default=True, help=
    'Time in video to begin detecting scenes. TIMECODE can be specified as exact'
    ' number of frames (-s 100 to start at frame 100), time in seconds followed by s'
    ' (-s 100s to start at 100 seconds), or a timecode in the format HH:MM:SS or HH:MM:SS.nnn'
    ' (-s 00:01:40 to start at 1m40s).')
@click.option(
    '--duration', '-d', metavar='TIMECODE',
    type=click.STRING, default=None, help=
    'Maximum time in video to process. TIMECODE format is the same as other'
    ' arguments. Mutually exclusive with --end / -e.')
@click.option(
    '--end', '-e', metavar='TIMECODE',
    type=click.STRING, default=None, help=
    'Time in video to end detecting scenes. TIMECODE format is the same as other'
    ' arguments. Mutually exclusive with --duration / -d.')
@click.pass_context
def time_command(ctx, start, duration, end):
    """ Set start/end/duration of input video(s).

    Time values can be specified as frames (NNNN), seconds (NNNN.NNs), or as
    a timecode (HH:MM:SS.nnn). For example, to start scene detection at 1 minute,
    and stop after 100 seconds:

    time --start 00:01:00 --duration 100s

    Note that --end and --duration are mutually exclusive (i.e. only one of the two
    can be set). Lastly, the following is an example using absolute frame numbers
    to process frames 0 through 1000:

    time --start 0 --end 1000
    """
    assert isinstance(ctx.obj, CliContext)

    if ctx.obj.time:
        duplicate_command(ctx, 'time')
    if duration is not None and end is not None:
        raise click.BadParameter(
            'Only one of --duration/-d or --end/-e can be specified, not both.',
            param_hint='time')

    ctx.obj.check_input_open()
    frame_rate = ctx.obj.video_stream.frame_rate

    logger.debug('Setting video time:\n    start: %s, duration: %s, end: %s',
                    start, duration, end)

    options_processed_orig = ctx.obj.options_processed
    ctx.obj.options_processed = False
    ctx.obj.start_time = parse_timecode(start, frame_rate)
    ctx.obj.end_time = parse_timecode(end, frame_rate)
    ctx.obj.duration = parse_timecode(duration, frame_rate)
    ctx.obj.time = True
    ctx.obj.options_processed = options_processed_orig



@click.command('detect-content')
@click.option(
    '--threshold', '-t', metavar='VAL',
    type=click.FLOAT, default=27.0, show_default=True, help=
    'Threshold value (float) that the content_val frame metric must exceed to trigger a new scene.'
    ' Refers to frame metric content_val in stats file.')
@click.option(
    '--luma-only', '-l',
    is_flag=True, flag_value=True, help=
    'Only consider luma/brightness channel (useful for greyscale videos).')
@click.pass_context
def detect_content_command(ctx, threshold, luma_only):
    """ Perform content detection algorithm on input video(s).

    detect-content

    detect-content --threshold 27.5
    """
    assert isinstance(ctx.obj, CliContext)

    min_scene_len = 0 if ctx.obj.drop_short_scenes else ctx.obj.min_scene_len
    luma_mode_str = '' if not luma_only else ', luma_only mode'
    logger.debug('Detecting content, parameters:\n'
                  '  threshold: %d, min-scene-len: %d%s',
                  threshold, min_scene_len, luma_mode_str)

    # Initialize detector and add to scene manager.
    # Need to ensure that a detector is not added twice, or will cause
    # a frame metric key error when registering the detector.
    ctx.obj.add_detector(scenedetect.detectors.ContentDetector(
        threshold=threshold, min_scene_len=min_scene_len, luma_only=luma_only))


@click.command('detect-adaptive')
@click.option(
    '--threshold', '-t', metavar='VAL',
    type=click.FLOAT, default=3.0, show_default=True, help=
    'Threshold value (float) that the calculated frame score must exceed to'
    ' trigger a new scene (see frame metric adaptive_ratio in stats file).')
@click.option(
    '--min-scene-len', '-m', metavar='TIMECODE',
    type=click.STRING, default="0.6s", show_default=True, help=
    'Minimum size/length of any scene. TIMECODE can be specified as exact'
    ' number of frames, a time in seconds followed by s, or a timecode in the'
    ' format HH:MM:SS or HH:MM:SS.nnn')
@click.option(
    '--min-delta-hsv', '-d', metavar='VAL',
    type=click.FLOAT, default=15.0, show_default=True, help=
    'Minimum threshold (float) that the content_val must exceed in order to register as a new'
    ' scene. This is calculated the same way that `detect-content` calculates frame score.')
@click.option(
    '--frame-window', '-w', metavar='VAL',
    type=click.INT, default=2, show_default=True, help=
    'Size of window (number of frames) before and after each frame to average together in'
    ' order to detect deviations from the mean.')
@click.option(
    '--luma-only', '-l',
    is_flag=True, flag_value=True, help=
    'Only consider luma/brightness channel (useful for greyscale videos).')
@click.pass_context
def detect_adaptive_command(ctx, threshold, min_scene_len, min_delta_hsv,
                            frame_window, luma_only):
    """ Perform adaptive detection algorithm on input video(s).

    detect-adaptive

    detect-adaptive --threshold 3.2
    """
    assert isinstance(ctx.obj, CliContext)

    min_scene_len = parse_timecode(min_scene_len, ctx.obj.video_stream.frame_rate)
    luma_mode_str = '' if not luma_only else ', luma_only mode'

    logger.debug('Adaptively detecting content, parameters:\n'
                  '  threshold: %d, min-scene-len: %d%s',
                  threshold, min_scene_len, luma_mode_str)

    # Initialize detector and add to scene manager.
    # Need to ensure that a detector is not added twice, or will cause
    # a frame metric key error when registering the detector.
    ctx.obj.add_detector(scenedetect.detectors.AdaptiveDetector(
        adaptive_threshold=threshold,
        min_scene_len=min_scene_len,
        min_delta_hsv=min_delta_hsv,
        window_width=frame_window,
        luma_only=luma_only))



@click.command('detect-threshold')
@click.option(
    '--threshold', '-t', metavar='VAL',
    type=click.IntRange(0, 255), default=12, show_default=True, help=
    'Threshold value (integer) that the delta_rgb frame metric must exceed to trigger a new scene.'
    ' Refers to frame metric delta_rgb in stats file.')
@click.option(
    '--fade-bias', '-f', metavar='PERCENT',
    type=click.IntRange(-100, 100), default=0, show_default=True, help=
    'Percent (%) from -100 to 100 of timecode skew for where cuts should be placed. -100'
    ' indicates the start frame, +100 indicates the end frame, and 0 is the middle of both.')
@click.option(
    '--add-last-scene', '-l',
    is_flag=True, flag_value=True, help=
    'If set, if the video ends on a fade-out, an additional scene will be generated for the'
    ' last fade out position.')
@click.pass_context
def detect_threshold_command(ctx, threshold, fade_bias, add_last_scene):
    """  Perform threshold detection algorithm on input video(s).

    detect-threshold

    detect-threshold --threshold 15
    """
    assert isinstance(ctx.obj, CliContext)

    min_scene_len = 0 if ctx.obj.drop_short_scenes else ctx.obj.min_scene_len

    logger.debug('Detecting threshold, parameters:\n'
                  '  threshold: %d, min-scene-len: %d, fade-bias: %d, add-last-scene: %s',
                  threshold, min_scene_len, fade_bias, 'yes' if add_last_scene else 'no')

    # Handle case where add_last_scene is not set and is None.
    add_last_scene = True if add_last_scene else False

    # Convert and fade_bias from integer to float with a valid range of -1.0 to 1.0.
    fade_bias /= 100.0
    ctx.obj.add_detector(scenedetect.detectors.ThresholdDetector(
        threshold=threshold, min_scene_len=min_scene_len, fade_bias=fade_bias,
        add_final_scene=add_last_scene))




@click.command('export-html', add_help_option=False)
@click.option(
    '--filename', '-f', metavar='NAME', default='$VIDEO_NAME-Scenes.html',
    type=click.STRING, show_default=True, help=
    'Filename format to use for the scene list HTML file. You can use the'
    ' $VIDEO_NAME macro in the file name. Note that you may have to wrap'
    ' the format name using single quotes.')
@click.option(
    '--no-images', is_flag=True, flag_value=True, help=
    'Export the scene list including or excluding the saved images.')
@click.option(
    '--image-width', '-w', metavar='pixels',
    type=click.INT, help=
    'Width in pixels of the images in the resulting HTML table.')
@click.option(
    '--image-height', '-h', metavar='pixels',
    type=click.INT, help=
    'Height in pixels of the images in the resulting HTML table.')
@click.pass_context
def export_html_command(ctx, filename, no_images, image_width, image_height):
    """ Exports scene list to a HTML file. Requires save-images by default."""
    assert isinstance(ctx.obj, CliContext)

    if ctx.obj.export_html:
        duplicate_command(ctx, 'export_html')
    ctx.obj.check_input_open()

    if not ctx.obj.save_images and not no_images:
        ctx.obj.options_processed = False
        raise click.BadArgumentUsage(
            'The export-html command requires that the save-images command\n'
            'is specified before it, unless --no-images is specified.')

    if filename is not None:
        ctx.obj.html_name_format = filename
        logger.info('Scene list html file name format:\n %s', filename)
    ctx.obj.html_include_images = False if no_images else True
    ctx.obj.image_width = image_width
    ctx.obj.image_height = image_height

    ctx.obj.export_html = True



@click.command('list-scenes', add_help_option=False)
@click.option(
    '--output', '-o', metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False), help=
    'Output directory to save videos to. Overrides global option -o/--output if set.')
@click.option(
    '--filename', '-f', metavar='NAME', default='$VIDEO_NAME-Scenes.csv',
    type=click.STRING, show_default=True, help=
    'Filename format to use for the scene list CSV file. You can use the'
    ' $VIDEO_NAME macro in the file name. Note that you may have to wrap'
    ' the name using single quotes.')
@click.option(
    '--no-output-file', '-n',
    is_flag=True, flag_value=True, help=
    'Disable writing scene list CSV file to disk.  If set, -o/--output and'
    ' -f/--filename are ignored.')
@click.option(
    '--quiet', '-q',
    is_flag=True, flag_value=True, help=
    'Suppresses output of the table printed by the list-scenes command.')
@click.option(
    '--skip-cuts', '-s',
    is_flag=True, flag_value=True, help=
    'Skips outputting the cutting list as the first row in the CSV file.'
    ' Set this option if compliance with RFC 4810 is required.')
@click.pass_context
def list_scenes_command(ctx, output, filename, no_output_file, quiet, skip_cuts):
    """ Prints scene list and outputs to a CSV file. The default filename is
    $VIDEO_NAME-Scenes.csv. """
    assert isinstance(ctx.obj, CliContext)

    if ctx.obj.list_scenes:
        duplicate_command(ctx, 'list-scenes')
    ctx.obj.check_input_open()

    ctx.obj.print_scene_list = True if quiet is None else not quiet
    ctx.obj.scene_list_directory = output
    ctx.obj.scene_list_name_format = filename
    if ctx.obj.scene_list_name_format is not None and not no_output_file:
        logger.info('Scene list filename format:\n  %s', ctx.obj.scene_list_name_format)
    ctx.obj.scene_list_output = False if no_output_file else True
    if ctx.obj.scene_list_directory is not None:
        logger.info('Scene list output directory:\n  %s', ctx.obj.scene_list_directory)
    ctx.obj.skip_cuts = skip_cuts

    ctx.obj.list_scenes = True



@click.command('split-video', add_help_option=False)
@click.option(
    '--output', '-o', metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False), help=
    'Output directory to save videos to. Overrides global option -o/--output if set.')
@click.option(
    '--filename', '-f', metavar='NAME', default='$VIDEO_NAME-Scene-$SCENE_NUMBER',
    type=click.STRING, show_default=False, help= # TODO(v1.0): Change macros to {}s?
    'File name format to use when saving videos (with or without extension). You can use the'
    ' $VIDEO_NAME and $SCENE_NUMBER macros in the filename (e.g. $VIDEO_NAME-Part-$SCENE_NUMBER).'
    ' Note that you may have to wrap the format in single quotes to avoid variable expansion.'
    ' [default: $VIDEO_NAME-Scene-$SCENE_NUMBER]')
@click.option(
    '--high-quality', '-hq',
    is_flag=True, flag_value=True, help=
    'Encode video with higher quality, overrides -f option if present.'
    ' Equivalent to specifying --rate-factor 17 and --preset slow.')
@click.option(
    '--override-args', '-a', metavar='ARGS',
    type=click.STRING, help=
    'Override codec arguments/options passed to FFmpeg when splitting and re-encoding'
    ' scenes. Use double quotes (") around specified arguments. Must specify at least'
    ' audio/video codec to use (e.g. -a "-c:v [...] -c:a [...]").'
    ' [default: "-c:v libx264 -preset veryfast -crf 22 -c:a aac"]')
@click.option(
    '--quiet', '-q',
    is_flag=True, flag_value=True, help=
    'Hides any output from the external video splitting tool.')
@click.option(
    '--copy', '-c',
    is_flag=True, flag_value=True, help=
    'Copy instead of re-encode. Much faster, but less precise. Equivalent to specifying'
    ' -a "-c:v copy -c:a copy".')
@click.option(
    '--mkvmerge', '-m',
    is_flag=True, flag_value=True, help=
    'Split the video using mkvmerge. Faster than re-encoding, but less precise. The output will'
    ' be named $VIDEO_NAME-$SCENE_NUMBER.mkv. If set, all options other than -f/--filename,'
    ' -q/--quiet and -o/--output will be ignored. Note that mkvmerge automatically appends a'
    'suffix of "-$SCENE_NUMBER".')
@click.option(
    '--rate-factor', '-crf', metavar='RATE', default=None, show_default=False,
    type=click.IntRange(0, 100), help=
    'Video encoding quality (x264 constant rate factor), from 0-100, where lower'
    ' values represent better quality, with 0 indicating lossless.'
    ' [default: 22, if -hq/--high-quality is set: 17]')
@click.option(
    '--preset', '-p', metavar='LEVEL', default=None, show_default=False,
    type=click.Choice([
        'ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium',
        'slow', 'slower', 'veryslow']),
    help=
    'Video compression quality preset (x264 preset). Can be one of: ultrafast, superfast,'
    ' veryfast, faster, fast, medium, slow, slower, and veryslow. Faster modes take less'
    ' time to run, but the output files may be larger.'
    ' [default: veryfast, if -hq/--high quality is set: slow]')
@click.pass_context
def split_video_command(ctx, output, filename, high_quality, override_args, quiet, copy,
                        mkvmerge, rate_factor, preset):
    """Split input video(s) using ffmpeg or mkvmerge."""
    assert isinstance(ctx.obj, CliContext)

    if ctx.obj.split_video:
        duplicate_command(ctx, 'split-video')
    ctx.obj.check_input_open()
    check_split_video_requirements(use_mkvmerge=mkvmerge)

    if contains_sequence_or_url(ctx.obj.video_stream.path):
        ctx.obj.options_processed = False
        error_str = 'The save-images command is incompatible with image sequences/URLs.'
        raise click.BadParameter(error_str, param_hint='save-images')

    ##
    ## Common Arguments/Options
    ##
    ctx.obj.split_video = True
    ctx.obj.split_quiet = bool(quiet)
    ctx.obj.split_directory = output
    if ctx.obj.split_directory is not None:
        logger.info('Video output path set:  \n%s', ctx.obj.split_directory)
    ctx.obj.split_name_format = filename

    # Disallow certain combinations of flags.
    if mkvmerge or copy:
        command = '-m/--mkvmerge' if mkvmerge else '-c/--copy'
        if high_quality:
            raise click.BadParameter(
                '-hq/--high-quality cannot be specified with {command}'.format(command=command),
                param_hint='split_video')
        if override_args:
            raise click.BadParameter(
                '-a/--override-args cannot be specified with {command}'.format(command=command),
                param_hint='split_video')
        if rate_factor:
            raise click.BadParameter(
                '-crf/--rate-factor cannot be specified with {command}'.format(command=command),
                param_hint='split_video')
        if preset:
            raise click.BadParameter(
                '-p/--preset cannot be specified with {command}'.format(command=command),
                param_hint='split_video')
    ##
    ## mkvmerge-Specific Arguments/Options
    ##
    if mkvmerge:
        if copy:
            logger.warning('-c/--copy flag ignored due to -m/--mkvmerge.')
        ctx.obj.split_mkvmerge = True
        logger.info('Using mkvmerge for video splitting.')
        return

    ##
    ## ffmpeg-Specific Arguments/Options
    ##
    # TODO: Should add some validation of the name format to ensure it contains at least one variable,
    # otherwise the output will just keep getting overwritten.

    if copy:
        override_args = '-c:v copy -c:a copy'
    elif not override_args:
        if rate_factor is None:
            rate_factor = 22 if not high_quality else 17
        if preset is None:
            preset = 'veryfast' if not high_quality else 'slow'
        override_args = ('-c:v libx264 -preset {PRESET} -crf {RATE_FACTOR} -c:a aac'.format(
            PRESET=preset, RATE_FACTOR=rate_factor))

    logger.info('ffmpeg arguments: %s', override_args)
    ctx.obj.split_args = override_args
    if filename:
        logger.info('Output file name format: %s', filename)



@click.command('save-images', add_help_option=False)
@click.option(
    '--output', '-o', metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False), help=
    'Output directory to save images to. Overrides global option -o/--output if set.')
@click.option(
    '--filename', '-f', metavar='NAME', default='$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER',
    type=click.STRING, show_default=True, help=
    'Filename format, *without* extension, to use when saving image files. You can use the'
    ' $VIDEO_NAME, $SCENE_NUMBER, $IMAGE_NUMBER, and $FRAME_NUMBER macros in the file name.'
    ' Note that you may have to wrap the format in single quotes.')
@click.option(
    '--num-images', '-n', metavar='N', default=3,
    type=click.INT, help=
    'Number of images to generate. Will always include start/end frame,'
    ' unless N = 1, in which case the image will be the frame at the mid-point'
    ' in the scene.')
@click.option(
    '--jpeg', '-j',
    is_flag=True, flag_value=True, help=
    'Set output format to JPEG. [default]')
@click.option(
    '--webp', '-w',
    is_flag=True, flag_value=True, help=
    'Set output format to WebP.')
@click.option(
    '--quality', '-q', metavar='Q', default=None,
    type=click.IntRange(0, 100), help=
    'JPEG/WebP encoding quality, from 0-100 (higher indicates better quality).'
    ' For WebP, 100 indicates lossless. [default: JPEG: 95, WebP: 100]')
@click.option(
    '--png', '-p',
    is_flag=True, flag_value=True, help=
    'Set output format to PNG.')
@click.option(
    '--compression', '-c', metavar='C', default=3, show_default=False,
    type=click.IntRange(0, 9), help=
    'PNG compression rate, from 0-9. Higher values produce smaller files but result'
    ' in longer compression time. This setting does not affect image quality, only'
    ' file size. [default: 3]')
@click.option(
    '-m', '--frame-margin', metavar='N', default=1, show_default=True,
    type=click.INT, help=
    'Number of frames to ignore at the beginning and end of scenes when saving images')
@click.option(
    '--scale', '-s', metavar='S', default=None, show_default=False,
    type=click.FLOAT, help=
    'Optional factor by which saved images are rescaled. A scaling factor of 1 would'
    ' not result in rescaling. A value <1 results in a smaller saved image, while a'
    ' value >1 results in an image larger than the original. This value is ignored if'
    ' either the height, -h, or width, -w, values are specified.')
@click.option(
    '--height', '-h', metavar='H', default=None, show_default=False,
    type=click.INT, help=
    'Optional value for the height of the saved images. Specifying both the height'
    ' and width, -w, will resize images to an exact size, regardless of aspect ratio.'
    ' Specifying only height will rescale the image to that number of pixels in height'
    ' while preserving the aspect ratio.')
@click.option(
    '--width', '-w', metavar='W', default=None, show_default=False,
    type=click.INT, help=
    'Optional value for the width of the saved images. Specifying both the width'
    ' and height, -h, will resize images to an exact size, regardless of aspect ratio.'
    ' Specifying only width will rescale the image to that number of pixels wide'
    ' while preserving the aspect ratio.')
@click.pass_context
def save_images_command(ctx, output, filename, num_images, jpeg, webp, quality, png,
                        compression, frame_margin, scale, height, width):
    """ Create images for each detected scene. """
    assert isinstance(ctx.obj, CliContext)

    if ctx.obj.save_images:
        duplicate_command(ctx, 'save-images')
    if quality is None:
        quality = 100 if webp else 95
    ctx.obj.save_images_command(num_images, output, filename, jpeg, webp, quality, png,
                                compression, frame_margin, scale, height, width)


# ----------------------------------------------------------------------
# Commands Added To Help List
# ----------------------------------------------------------------------

# Info/Terminating Commands
add_cli_command(scenedetect_cli, help_command)
add_cli_command(scenedetect_cli, version_command)
add_cli_command(scenedetect_cli, about_command)

# Input Commands
add_cli_command(scenedetect_cli, time_command)

# Output Commands
add_cli_command(scenedetect_cli, export_html_command)
add_cli_command(scenedetect_cli, list_scenes_command)
add_cli_command(scenedetect_cli, save_images_command)
add_cli_command(scenedetect_cli, split_video_command)

# Detection Algorithms
add_cli_command(scenedetect_cli, detect_content_command)
add_cli_command(scenedetect_cli, detect_threshold_command)
add_cli_command(scenedetect_cli, detect_adaptive_command)
