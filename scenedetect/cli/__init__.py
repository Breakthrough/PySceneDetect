# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2020 Brandon Castellano <http://www.bcastell.com>.
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

# Standard Library Imports
from __future__ import print_function
import sys
import string
import logging

# Third-Party Library Imports
import click

# PySceneDetect Library Imports
import scenedetect
from scenedetect.cli.context import CliContext
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_manager import VideoManager

from scenedetect.video_splitter import is_mkvmerge_available
from scenedetect.video_splitter import is_ffmpeg_available

from scenedetect.platform import get_and_create_path


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
    # type: (Callable[[...] -> None], Callable[]) -> None
    """Adds the CLI command to the cli object as well as to the COMMAND_DICT."""
    cli.add_command(command)
    COMMAND_DICT.append(command)


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


def print_command_help(ctx, command):
    # type: (click.Context, Callable[]) -> None
    """ Print Command Help: Prints PySceneDetect help/usage for a given command. """
    ctx_name = ctx.info_name
    ctx.info_name = command.name
    click.echo(click.style('PySceneDetect %s Command' % command.name, fg='cyan'))
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(command.get_help(ctx))
    click.echo('')
    ctx.info_name = ctx_name


def print_command_list_header():
    # type: () -> None
    """ Print Command List Header: Prints header shown before the option/command list. """
    click.echo(click.style('PySceneDetect Option/Command List:', fg='green'))
    click.echo(click.style('----------------------------------------------------', fg='green'))
    click.echo('')


def print_help_header():
    # type: () -> None
    """ Print Help Header: Prints header shown before the help command. """
    click.echo(click.style('----------------------------------------------------', fg='yellow'))
    click.echo(click.style(' PySceneDetect %s Help' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='yellow'))


def duplicate_command(ctx, param_hint):
    # type: (str) -> None
    """ Duplicate Command: Called when a command is duplicated to stop parsing and raise an error.

    Called when a one-time use command is specified multiple times, displaying the appropriate
    error and usage information.

    Raises:
        click.BadParameter
    """
    ctx.obj.options_processed = False
    error_strs = []
    error_strs.append('Error: Command %s specified multiple times.' % param_hint)
    error_strs.append('The %s command may appear only one time.')

    logging.error('\n'.join(error_strs))
    raise click.BadParameter('\n  Command %s may only be specified once.' % param_hint,
                             param_hint='%s command' % param_hint)



@click.group(
    chain=True, context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    '--input', '-i',
    multiple=True, required=False, metavar='VIDEO',
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=True), help=
    '[Required] Input video file.'
    ' May be specified multiple times to concatenate several videos together.')
@click.option(
    '--output', '-o',
    multiple=False, required=False, metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=True), help=
    'Output directory for all files (stats file, output videos, images, log files, etc...).')
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
    '--stats', '-s', metavar='CSV',
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False), help=
    'Path to stats file (.csv) for writing frame metrics to. If the file exists, any'
    ' metrics will be processed, otherwise a new file will be created. Can be used to determine'
    ' optimal values for various scene detector options, and to cache frame calculations in order'
    ' to speed up multiple detection runs.')
@click.option(
    '--verbosity', '-v', metavar='LEVEL',
    type=click.Choice(['none', 'debug', 'info', 'warning', 'error']), default='info', help=
    'Level of debug/info/error information to show. Setting to none will'
    ' suppress all output except that generated by actions (e.g. timecode list output).'
    ' Can be overriden by `-q`/`--quiet`.')
@click.option(
    '--logfile', '-l', metavar='LOG',
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False), help=
    'Path to log file for writing application logging information, mainly for debugging.'
    ' Make sure to set `-v debug` as well if you are submitting a bug report.')
@click.option(
    '--quiet', '-q',
    is_flag=True, flag_value=True, help=
    'Suppresses all output of PySceneDetect except for those from the specified'
    ' commands. Equivalent to setting `--verbosity none`. Overrides the current verbosity'
    ' level, even if `-v`/`--verbosity` is set.')
@click.pass_context
# pylint: disable=redefined-builtin
def scenedetect_cli(ctx, input, output, framerate, downscale, frame_skip, stats,
                    verbosity, logfile, quiet):
    """ For example:

    scenedetect -i video.mp4 -s video.stats.csv detect-content list-scenes

    Note that the following options represent [OPTIONS] above. To list the optional
    [ARGS] for a particular COMMAND, type `scenedetect help COMMAND`. You can also
    combine commands (e.g. scenedetect [...] detect-content save-images --png split-video).


    """
    ctx.call_on_close(ctx.obj.process_input)

    logging.disable(logging.NOTSET)

    format_str = '[PySceneDetect] %(message)s'
    if verbosity.lower() == 'none':
        verbosity = None
    elif verbosity.lower() == 'debug':
        format_str = '%(levelname)s: %(module)s.%(funcName)s(): %(message)s'

    if quiet:
        verbosity = None

    ctx.obj.output_directory = output
    if logfile is not None:
        logfile = get_and_create_path(logfile)
        logging.basicConfig(
            filename=logfile, filemode='a', format=format_str,
            level=getattr(logging, verbosity.upper()) if verbosity is not None else verbosity)
        logging.info('Version: %s', scenedetect.__version__)
        logging.info('Info Level: %s', verbosity)
    else:
        if verbosity is not None:
            logging.basicConfig(format=format_str,
                                level=getattr(logging, verbosity.upper()))
        else:
            logging.disable(logging.CRITICAL)

    ctx.obj.quiet_mode = True if verbosity is None else False

    if stats is not None and frame_skip != 0:
        ctx.obj.options_processed = False
        error_strs = [
            'Unable to detect scenes with stats file if frame skip is not 1.',
            '  Either remove the -fs/--frame-skip option, or the -s/--stats file.\n']
        logging.error('\n'.join(error_strs))
        raise click.BadParameter(
            '\n  Combining the -s/--stats and -fs/--frame-skip options is not supported.',
            param_hint='frame skip + stats file')
    try:
        if ctx.obj.output_directory is not None:
            logging.info('Output directory set:\n  %s', ctx.obj.output_directory)
        ctx.obj.parse_options(
            input_list=input, framerate=framerate, stats_file=stats, downscale=downscale,
            frame_skip=frame_skip)
    except:
        logging.error('Could not parse CLI options.')
        raise



@click.command('help', add_help_option=False)
@click.argument('command_name', required=False, type=click.STRING)
@click.pass_context
def help_command(ctx, command_name):
    """ Print help for command (help [command]).
    """
    ctx.obj.options_processed = False
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
    start = parse_timecode(ctx.obj, start)
    duration = parse_timecode(ctx.obj, duration)
    end = parse_timecode(ctx.obj, end)

    ctx.obj.time_command(start, duration, end)



@click.command('detect-content')
@click.option(
    '--threshold', '-t', metavar='VAL',
    type=click.FLOAT, default=30.0, show_default=True, help=
    'Threshold value (float) that the content_val frame metric must exceed to trigger a new scene.'
    ' Refers to frame metric content_val in stats file.')
@click.option(
    '--min-scene-len', '-m', metavar='TIMECODE',
    type=click.STRING, default="0.6s", show_default=True, help=
    'Minimum size/length of any scene. TIMECODE can be specified as exact'
    ' number of frames, a time in seconds followed by s, or a timecode in the'
    ' format HH:MM:SS or HH:MM:SS.nnn')
@click.pass_context
def detect_content_command(ctx, threshold, min_scene_len):
    """ Perform content detection algorithm on input video(s).

    detect-content

    detect-content --threshold 27.5
    """

    min_scene_len = parse_timecode(ctx.obj, min_scene_len)

    logging.debug('Detecting content, parameters:\n'
                  '  threshold: %d, min-scene-len: %d',
                  threshold, min_scene_len)

    # Initialize detector and add to scene manager.
    # Need to ensure that a detector is not added twice, or will cause
    # a frame metric key error when registering the detector.
    ctx.obj.add_detector(scenedetect.detectors.ContentDetector(
        threshold=threshold, min_scene_len=min_scene_len))


@click.command('adaptive-detect-content')
@click.option(
    '--threshold', '-t', metavar='VAL',
    type=click.FLOAT, default=3.0, show_default=True, help=
    'Threshold value (float) that the con_val_ratio frame metric must exceed to trigger a new scene.'
    ' Refers to frame metric content_val_ratio in stats file.')
@click.option(
    '--min-scene-len', '-m', metavar='TIMECODE',
    type=click.STRING, default="0.6s", show_default=True, help=
    'Minimum size/length of any scene. TIMECODE can be specified as exact'
    ' number of frames, a time in seconds followed by s, or a timecode in the'
    ' format HH:MM:SS or HH:MM:SS.nnn')
@click.option(
    '--min-delta-hsv', '-d', metavar='VAL',
    type=click.FLOAT, default=5.0, show_default=True, help=
    'Minimum threshold (float) that the content_val must exceed in order to register as a new scene.'
    ' This is calculated the same way that the detect-content command calculates content_val.')
@click.option(
    '--frame-window', '-w', metavar='VAL',
    type=click.INT, default=2, show_default=True, help=
    'Number of frames before and after each frame to average together in'
    ' order to detect deviations from the mean.')
@click.pass_context
def adaptive_detect_content_command(ctx, threshold, min_scene_len, min_delta_hsv, frame_window):
    """ Perform adaptive content detection algorithm on input video(s).

    adaptive-detect-content

    adaptive-detect-content --threshold 3.2
    """

    min_scene_len = parse_timecode(ctx.obj, min_scene_len)

    logging.debug('Adaptively detecting content, parameters:\n'
                  '  threshold: %d, min-scene-len: %d',
                  threshold, min_scene_len)

    # Check for a stats manager, necessary to use the adaptive content detector
    if not ctx.obj.stats_manager:
        error_strs = [
            'No stats file specified for use with the adaptive content detector.'
            ' Either use a different detector or specify a stats file with -s/--stats\n']
        logging.error('\n'.join(error_strs))
        raise click.BadParameter(
            '\n  Specifying a stats file -s/--stats is necessary to use the adaptive content detector',
            param_hint='adaptive detector + stats file')

    # Initialize detector and add to scene manager.
    # Need to ensure that a detector is not added twice, or will cause
    # a frame metric key error when registering the detector.
    ctx.obj.add_detector(scenedetect.detectors.AdaptiveContentDetector(
        video_manager=ctx.obj.video_manager,
        adaptive_threshold=threshold,
        min_scene_len=min_scene_len,
        min_delta_hsv=min_delta_hsv,
        window_width=frame_window))


@click.command('detect-threshold')
@click.option(
    '--threshold', '-t', metavar='VAL',
    type=click.IntRange(0, 255), default=12, show_default=True, help=
    'Threshold value (integer) that the delta_rgb frame metric must exceed to trigger a new scene.'
    ' Refers to frame metric delta_rgb in stats file.')
@click.option(
    '--min-scene-len', '-m', metavar='TIMECODE',
    type=click.STRING, show_default=True, default="0.6s", help=
    'Minimum size/length of any scene. TIMECODE can be specified as exact'
    ' number of frames, a time in seconds followed by s, or a timecode in the'
    ' format HH:MM:SS or HH:MM:SS.nnn')
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
@click.option(
    '--min-percent', '-p', metavar='PERCENT',
    type=click.IntRange(0, 100), default=95, show_default=True, help=
    'Percent (%) from 0 to 100 of amount of pixels that must meet the threshold value in order'
    'to trigger a scene change.')
@click.option(
    '--block-size', '-b', metavar='N',
    type=click.IntRange(1, 128), default=8, show_default=True, help=
    'Number of rows in image to sum per iteration (can be tuned for performance in some cases).')
@click.pass_context
def detect_threshold_command(ctx, threshold, min_scene_len, fade_bias, add_last_scene,
                             min_percent, block_size):
    """  Perform threshold detection algorithm on input video(s).

    detect-threshold

    detect-threshold --threshold 15
    """

    logging.debug('Detecting threshold, parameters:\n'
                  '  threshold: %d, min-scene-len: %d, fade-bias: %d,\n'
                  '  add-last-scene: %s, min-percent: %d, block-size: %d',
                  threshold, min_scene_len, fade_bias,
                  'yes' if add_last_scene else 'no', min_percent, block_size)

    # Handle case where add_last_scene is not set and is None.
    add_last_scene = True if add_last_scene else False

    min_scene_len = parse_timecode(ctx.obj, min_scene_len)

    # Convert min_percent and fade_bias from integer to floats (0.0-1.0 and -1.0-+1.0 respectively).
    min_percent /= 100.0
    fade_bias /= 100.0
    ctx.obj.add_detector(scenedetect.detectors.ThresholdDetector(
        threshold=threshold, min_scene_len=min_scene_len, fade_bias=fade_bias,
        add_final_scene=add_last_scene, min_percent=min_percent, block_size=block_size))


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
    if not ctx.obj.save_images and not no_images:
        raise click.BadParameter("save-images isn't enabled")
    ctx.obj.export_html_command(filename, no_images, image_width, image_height)
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
@click.pass_context
def list_scenes_command(ctx, output, filename, no_output_file, quiet):
    """ Prints scene list and outputs to a CSV file. The default filename is
    $VIDEO_NAME-Scenes.csv. """
    if ctx.obj.list_scenes:
        duplicate_command(ctx, 'list-scenes')
    ctx.obj.list_scenes_command(output, filename, no_output_file, quiet)
    ctx.obj.list_scenes = True



@click.command('split-video', add_help_option=False)
@click.option(
    '--output', '-o', metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False), help=
    'Output directory to save videos to. Overrides global option -o/--output if set.')
@click.option(
    '--filename', '-f', metavar='NAME', default='$VIDEO_NAME-Scene-$SCENE_NUMBER',
    type=click.STRING, show_default=True, help=
    'File name format, to use when saving image files. You can use the'
    ' $VIDEO_NAME and $SCENE_NUMBER macros in the file name. Note that'
    ' you may have to wrap the name using single quotes.')
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
    ' audio/video codec to use (e.g. -a "-c:v [...] and -c:a [...]"). [default:'
    ' "-c:v libx264 -preset veryfast -crf 22 -c:a aac"]')
@click.option(
    '--quiet', '-q',
    is_flag=True, flag_value=True, help=
    'Hides any output from the external video splitting tool.')
@click.option(
    '--copy', '-c',
    is_flag=True, flag_value=True, help=
    'Copy instead of re-encode using mkvmerge. All other options except'
    ' -o/--output and -q/--quiet are ignored in this mode.'
    ' Significantly faster, but far less precise. Output files will be'
    ' named $VIDEO_NAME-$SCENE_NUMBER.mkv.')
@click.option(
    '--rate-factor', '-crf', metavar='RATE', default=None,
    type=click.IntRange(0, 100), help=
    'Video encoding quality (x264 constant rate factor), from 0-100, where lower'
    ' values represent better quality, with 0 indicating lossless.'
    ' [default: 22, if -hq/--high-quality is set: 17]')
@click.option(
    '--preset', '-p', metavar='LEVEL', default=None,
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
                        rate_factor, preset):
    """Split input video(s) using ffmpeg or mkvmerge."""
    if ctx.obj.split_video:
        logging.warning('split-video command is specified twice.')
    ctx.obj.check_input_open()
    ctx.obj.split_video = True
    ctx.obj.split_quiet = True if quiet else False
    ctx.obj.split_directory = output
    ctx.obj.split_name_format = filename
    if copy:
        ctx.obj.split_mkvmerge = True
        if high_quality:
            logging.warning('-hq/--high-quality flag ignored due to -c/--copy.')
        if override_args:
            logging.warning('-f/--ffmpeg-args option ignored due to -c/--copy.')
    if not override_args:
        if rate_factor is None:
            rate_factor = 22 if not high_quality else 17
        if preset is None:
            preset = 'veryfast' if not high_quality else 'slow'
        override_args = ('-c:v libx264 -preset {PRESET} -crf {RATE_FACTOR} -c:a aac'.format(
            PRESET=preset, RATE_FACTOR=rate_factor))
    if not copy:
        logging.info('FFmpeg codec args set: %s', override_args)
    if filename:
        logging.info('Video output file name format: %s', filename)
    if ctx.obj.split_directory is not None:
        logging.info('Video output path set:  \n%s', ctx.obj.split_directory)
    ctx.obj.split_args = override_args

    mkvmerge_available = is_mkvmerge_available()
    ffmpeg_available = is_ffmpeg_available()
    if not (mkvmerge_available or ffmpeg_available) or (
            (not mkvmerge_available and copy) or (not ffmpeg_available and not copy)):
        split_tool = 'ffmpeg/mkvmerge'
        if (not mkvmerge_available and copy):
            split_tool = 'mkvmerge'
        elif (not ffmpeg_available and not copy):
            split_tool = 'ffmpeg'
        error_strs = [
            "{EXTERN_TOOL} is required for split-video{EXTRA_ARGS}.".format(
                EXTERN_TOOL=split_tool, EXTRA_ARGS=' -c/--copy' if copy else ''),
            "Install the above tool%s to enable video splitting support." % (
                's' if split_tool.find('/') > 0 else '')]
        if mkvmerge_available:
            error_strs += [
                'You can also specify `split-video -c/--copy` to use mkvmerge for splitting.']
        error_str = '\n'.join(error_strs)
        logging.debug(error_str)
        ctx.obj.options_processed = False
        raise click.BadParameter(error_str, param_hint='split-video')



@click.command('save-images', add_help_option=False)
@click.option(
    '--output', '-o', metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False), help=
    'Output directory to save images to. Overrides global option -o/--output if set.')
@click.option(
    '--filename', '-f', metavar='NAME', default='$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER',
    type=click.STRING, show_default=True, help=
    'Filename format, *without* extension, to use when saving image files. You can use the'
    ' $VIDEO_NAME, $SCENE_NUMBER, and $IMAGE_NUMBER macros in the file name. Note that you'
    ' may have to wrap the format in single quotes.')
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
    '--compression', '-c', metavar='C', default=None,
    type=click.IntRange(0, 9), help=
    'PNG compression rate, from 0-9. Higher values produce smaller files but result'
    ' in longer compression time. This setting does not affect image quality, only'
    ' file size. [default: 3]')
@click.option(
    '--image-frame-margin', metavar='N', default=0,
    type=click.INT, help=
    'Number of frames to ignore at the beginning and end of scenes when saving images')
@click.pass_context
def save_images_command(ctx, output, filename, num_images, jpeg, webp, quality, png,
                        compression, image_frame_margin):
    """ Create images for each detected scene. """
    if ctx.obj.save_images:
        duplicate_command(ctx, 'save-images')
    ctx.obj.save_images_command(num_images, output, filename, jpeg, webp, quality, png,
                                compression, image_frame_margin)



@click.command('colors', add_help_option=False)
@click.option(
    '--colors', '-c', metavar='N',
    type=click.INT, default=4, help=
    'Number of color averages to generate.')
@click.option(
    '--generate-pallette', '-p', metavar='N',
    type=click.INT, default=4, help=
    'Flag which, if set, saves an image with the colors in a grid as for use as a pallette.')
@click.pass_context
def colors_command(ctx):
    """ Colors Command: Generates pallette/image of average N colours in video, and each scene.

    Not implemented yet, needs to be added to backlog.
    """
    raise NotImplementedError()



# Info/Terminating Commands:
add_cli_command(scenedetect_cli, help_command)
add_cli_command(scenedetect_cli, about_command)
add_cli_command(scenedetect_cli, version_command)

# Commands Added To Help List:
add_cli_command(scenedetect_cli, time_command)
add_cli_command(scenedetect_cli, detect_content_command)
add_cli_command(scenedetect_cli, detect_threshold_command)
add_cli_command(scenedetect_cli, adaptive_detect_content_command)
add_cli_command(scenedetect_cli, list_scenes_command)

add_cli_command(scenedetect_cli, save_images_command)
add_cli_command(scenedetect_cli, split_video_command)

add_cli_command(scenedetect_cli, export_html_command)
