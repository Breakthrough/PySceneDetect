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
"""``scenedetect.cli`` Module

This file contains the implementation of the PySceneDetect command-line interface (CLI)
parser logic for the PySceneDetect application ("business logic"), The main CLI
entry-point function is the function scenedetect_cli, which is a chained command group.

The scenedetect.cli module coordinates first parsing all commands and their options using
a `CliContext`, finally performing scene detection by passing the `CliContext` to the
`run_scenedetect` run in `scenedetect.cli.controller`.
"""

import logging
from typing import AnyStr, Optional

import click

import scenedetect
from scenedetect.backends import AVAILABLE_BACKENDS
from scenedetect.cli.config import CONFIG_FILE_PATH, CONFIG_MAP, CHOICE_MAP
from scenedetect.cli.context import USER_CONFIG, CliContext
from scenedetect.cli.controller import run_scenedetect

logger = logging.getLogger('pyscenedetect')


def _get_help_command_preface(command_name='scenedetect'):
    """Preface/intro help message shown at the beginning of the help command."""
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

    help:    Display help information (e.g. `help [command]`).
    version: Display version of PySceneDetect being used.
    about:   Display license and copyright information.
""".format(command_name=command_name)


_COMMAND_DICT = []
"""All commands registered with the CLI. Used for generating help contexts."""


def _add_cli_command(cli: click.Group, command: click.Command):
    """Add the given `command` to the `cli` group as well as the global _COMMAND_DICT."""
    cli.add_command(command)
    _COMMAND_DICT.append(command)


def _print_command_help(ctx: click.Context, command: click.Command):
    """Print PySceneDetect help/usage for a given command."""
    ctx.help_option_names = []
    ctx_name = ctx.info_name
    ctx.info_name = command.name
    click.echo(click.style('`%s` Command' % command.name, fg='cyan'))
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(command.get_help(ctx))
    click.echo('')
    ctx.info_name = ctx_name


def _print_command_list_header() -> None:
    """Print header shown before the option/command list."""
    click.echo(click.style('PySceneDetect Options & Commands', fg='green'))
    click.echo(click.style('----------------------------------------------------', fg='green'))
    click.echo('')


def _print_help_header() -> None:
    """Print header shown before the help command."""
    click.echo(click.style('----------------------------------------------------', fg='yellow'))
    click.echo(click.style(' PySceneDetect %s Help' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='yellow'))


@click.group(
    chain=True,
    context_settings=dict(help_option_names=['-h', '--help']),
)
@click.option(
    '--input',
    '-i',
    multiple=False,
    required=False,
    metavar='VIDEO',
    type=click.STRING,
    help='[Required] Input video file. Also supports image sequences and URLs.',
)
@click.option(
    '--output',
    '-o',
    multiple=False,
    required=False,
    metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=True),
    help='Output directory for created files (stats file, output videos, images, etc...).'
    ' If not set defaults to working directory. Some commands allow overriding this value.%s' %
    (USER_CONFIG.get_help_string("global", "output", show_default=False)),
)
@click.option(
    '--framerate',
    '-f',
    metavar='FPS',
    type=click.FLOAT,
    default=None,
    help='Force framerate, in frames/sec (e.g. -f 29.97). Disables check to ensure that all'
    ' input videos have the same framerates.',
)
@click.option(
    '--downscale',
    '-d',
    metavar='N',
    type=click.INT,
    default=None,
    help='Integer factor to downscale frames by (e.g. 2, 3, 4...), where the frame is scaled'
    ' to width/N x height/N (thus -d 1 implies no downscaling). Leave unset for automatic'
    ' downscaling based on source resolution.%s' %
    (USER_CONFIG.get_help_string("global", "downscale", show_default=False)),
)
@click.option(
    '--frame-skip',
    '-fs',
    metavar='N',
    type=click.INT,
    default=None,
    help='Skips N frames during processing (-fs 1 skips every other frame, processing 50%%'
    ' of the video, -fs 2 processes 33%% of the frames, -fs 3 processes 25%%, etc...).'
    ' Reduces processing speed at expense of accuracy.%s' %
    USER_CONFIG.get_help_string("global", "frame-skip"),
)
@click.option(
    '--min-scene-len',
    '-m',
    metavar='TIMECODE',
    type=click.STRING,
    default=None,
    help='Minimum length of any scene. TIMECODE can be specified as exact'
    ' number of frames, a time in seconds followed by s, or a timecode in the'
    ' format HH:MM:SS or HH:MM:SS.nnn.%s' % USER_CONFIG.get_help_string("global", "min-scene-len"),
)
@click.option(
    '--drop-short-scenes',
    is_flag=True,
    flag_value=True,
    help='Drop scenes shorter than `min-scene-len` instead of combining them with neighbors.%s' %
    (USER_CONFIG.get_help_string('global', 'drop-short-scenes')),
)
@click.option(
    '--merge-last-scene',
    is_flag=True,
    flag_value=True,
    help='Merge last scene with previous if shorter than min-scene-len.%s' %
    (USER_CONFIG.get_help_string('global', 'merge-last-scene')),
)
@click.option(
    '--stats',
    '-s',
    metavar='CSV',
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False),
    help='Path to stats file (.csv) for writing frame metrics to. If the file exists, any'
    ' metrics will be processed, otherwise a new file will be created. Can be used to determine'
    ' optimal values for various scene detector options, and to cache frame calculations in order'
    ' to speed up multiple detection runs.',
)
@click.option(
    '--verbosity',
    '-v',
    metavar='LEVEL',
    type=click.Choice(CHOICE_MAP['global']['verbosity'], False),
    default=None,
    help='Level of debug/info/error information to show. Must be one of: %s.'
    ' Overrides `-q`/`--quiet`. Use `-v debug` for bug reports.%s' % (', '.join(
        CHOICE_MAP["global"]["verbosity"]), USER_CONFIG.get_help_string("global", "verbosity")),
)
@click.option(
    '--logfile',
    '-l',
    metavar='LOG',
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False),
    help='Path to log file for writing application logging information, mainly for debugging.'
    ' Set `-v debug` as well if you are submitting a bug report. If verbosity is none, logfile'
    ' is still be generated with info-level verbosity.',
)
@click.option(
    '--quiet',
    '-q',
    is_flag=True,
    flag_value=True,
    help='Suppresses all output of PySceneDetect to the terminal/stdout. Equivalent to `-v none`.',
)
@click.option(
    '--backend',
    '-b',
    metavar='BACKEND',
    type=click.Choice(CHOICE_MAP["global"]["backend"]),
    default=None,
    help='Backend to use for video input. Backends can be configured using -c/--config. Backends'
    ' available on this system: %s.%s.' %
    (', '.join(AVAILABLE_BACKENDS.keys()), USER_CONFIG.get_help_string("global", "backend")),
)
@click.option(
    '--config',
    '-c',
    metavar='FILE',
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=False),
    help='Path to config file. If not set, tries to load one from %s' % (CONFIG_FILE_PATH),
)
@click.pass_context
# pylint: disable=redefined-builtin
def scenedetect_cli(
    ctx: click.Context,
    input: Optional[AnyStr],
    output: Optional[AnyStr],
    framerate: Optional[float],
    downscale: Optional[int],
    frame_skip: Optional[int],
    min_scene_len: Optional[str],
    drop_short_scenes: bool,
    merge_last_scene: bool,
    stats: Optional[AnyStr],
    verbosity: Optional[str],
    logfile: Optional[AnyStr],
    quiet: bool,
    backend: Optional[str],
    config: Optional[AnyStr],
):
    """For example:

    scenedetect -i video.mp4 -s video.stats.csv detect-content list-scenes

    Note that the following options represent [OPTIONS] above. To list the optional
    [ARGS] for a particular COMMAND, type `scenedetect help COMMAND`. You can also
    combine commands (e.g. scenedetect [...] detect-content save-images --png split-video).


    """
    assert isinstance(ctx.obj, CliContext)
    ctx.call_on_close(lambda: run_scenedetect(ctx.obj))
    ctx.obj.handle_options(
        input_path=input,
        output=output,
        framerate=framerate,
        stats_file=stats,
        downscale=downscale,
        frame_skip=frame_skip,
        min_scene_len=min_scene_len,
        drop_short_scenes=drop_short_scenes,
        merge_last_scene=merge_last_scene,
        backend=backend,
        quiet=quiet,
        logfile=logfile,
        config=config,
        stats=stats,
        verbosity=verbosity,
    )


@click.command('help')
@click.argument(
    'command_name',
    required=False,
    type=click.STRING,
)
@click.pass_context
def help_command(ctx: click.Context, command_name: str):
    """Print help for command (`help [command]`) or all commands (`help all`)."""
    assert isinstance(ctx.obj, CliContext)
    ctx.obj.process_input_flag = False
    if command_name is not None:
        if command_name.lower() == 'all':
            _print_help_header()
            click.echo(_get_help_command_preface(ctx.parent.info_name))
            _print_command_list_header()
            click.echo(ctx.parent.get_help())
            click.echo('')
            for command in _COMMAND_DICT:
                _print_command_help(ctx, command)
        else:
            command = None
            for command_ref in _COMMAND_DICT:
                if command_name == command_ref.name:
                    command = command_ref
                    break
            if command is None:
                error_strs = [
                    'unknown command.', 'List of valid commands:',
                    '  %s' % ', '.join([command.name for command in _COMMAND_DICT])
                ]
                raise click.BadParameter('\n'.join(error_strs), param_hint='command name')
            click.echo('')
            _print_command_help(ctx, command)
    else:
        _print_help_header()
        click.echo(_get_help_command_preface(ctx.parent.info_name))
        _print_command_list_header()
        click.echo(ctx.parent.get_help())
        click.echo("\nType '%s help [command]' for usage/help of [command], or" %
                   ctx.parent.info_name)
        click.echo("'%s help all' to list usage information for every command." %
                   (ctx.parent.info_name))
    ctx.exit()


@click.command('about')
@click.pass_context
def about_command(ctx: click.Context):
    """Print license/copyright info."""
    assert isinstance(ctx.obj, CliContext)
    ctx.obj.process_input_flag = False
    click.echo('')
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(click.style(' About PySceneDetect %s' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(scenedetect.ABOUT_STRING)
    ctx.exit()


@click.command('version')
@click.pass_context
def version_command(ctx: click.Context):
    """Print PySceneDetect version."""
    assert isinstance(ctx.obj, CliContext)
    ctx.obj.process_input_flag = False
    click.echo('')
    click.echo(click.style('PySceneDetect %s' % scenedetect.__version__, fg='yellow'))
    ctx.exit()


@click.command('time')
@click.option(
    '--start',
    '-s',
    metavar='TIMECODE',
    type=click.STRING,
    default=None,
    help='Time in video to begin detecting scenes. TIMECODE can be specified as exact'
    ' number of frames (-s 100 to start at frame 100), time in seconds followed by s'
    ' (-s 100s to start at 100 seconds), or a timecode in the format HH:MM:SS or HH:MM:SS.nnn'
    ' (-s 00:01:40 to start at 1m40s).',
)
@click.option(
    '--duration',
    '-d',
    metavar='TIMECODE',
    type=click.STRING,
    default=None,
    help='Maximum time in video to process. TIMECODE format is the same as other'
    ' arguments. Mutually exclusive with --end / -e.',
)
@click.option(
    '--end',
    '-e',
    metavar='TIMECODE',
    type=click.STRING,
    default=None,
    help='Time in video to end detecting scenes. TIMECODE format is the same as other'
    ' arguments. Mutually exclusive with --duration / -d.',
)
@click.pass_context
def time_command(
    ctx: click.Context,
    start: Optional[str],
    duration: Optional[str],
    end: Optional[str],
):
    """Set start/end/duration of input video.

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
    ctx.obj.handle_time(
        start=start,
        duration=duration,
        end=end,
    )


@click.command('detect-content')
@click.option(
    '--threshold',
    '-t',
    metavar='VAL',
    type=click.FloatRange(CONFIG_MAP['detect-content']['threshold'].min_val,
                          CONFIG_MAP['detect-content']['threshold'].max_val),
    default=None,
    help='Threshold value that the content_val frame metric must exceed to trigger a new scene.'
    ' Refers to frame metric content_val in stats file.%s' %
    (USER_CONFIG.get_help_string("detect-content", "threshold")),
)
@click.option(
    '--luma-only',
    '-l',
    is_flag=True,
    flag_value=True,
    help='Only consider luma/brightness channel (useful for greyscale videos).%s' %
    (USER_CONFIG.get_help_string("detect-content", "luma-only")),
)
@click.option(
    '--min-scene-len',
    '-m',
    metavar='TIMECODE',
    type=click.STRING,
    default=None,
    help='Minimum length of any scene. Overrides global min-scene-len (-m) setting.'
    ' TIMECODE can be specified as exact number of frames, a time in seconds followed by s,'
    ' or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.%s' %
    ('' if USER_CONFIG.is_default('detect-content', 'min-scene-len') else
     USER_CONFIG.get_help_string('detect-content', 'min-scene-len')),
)
@click.pass_context
def detect_content_command(
    ctx: click.Context,
    threshold: Optional[float],
    luma_only: bool,
    min_scene_len: Optional[str],
):
    """Perform content detection algorithm on input video.

    detect-content

    detect-content --threshold 27.5
    """
    assert isinstance(ctx.obj, CliContext)
    ctx.obj.handle_detect_content(
        threshold=threshold,
        luma_only=luma_only,
        min_scene_len=min_scene_len,
    )


@click.command('detect-adaptive')
@click.option(
    '--threshold',
    '-t',
    metavar='VAL',
    type=click.FLOAT,
    default=None,
    help='Threshold value (float) that the calculated frame score must exceed to'
    ' trigger a new scene (see frame metric adaptive_ratio in stats file).%s' %
    (USER_CONFIG.get_help_string('detect-adaptive', 'threshold')),
)
@click.option(
    '--min-delta-hsv',
    '-d',
    metavar='VAL',
    type=click.FLOAT,
    default=None,
    help='Minimum threshold (float) that the content_val must exceed in order to register as a new'
    ' scene. This is calculated the same way that `detect-content` calculates frame score.%s' %
    (USER_CONFIG.get_help_string('detect-adaptive', 'min-delta-hsv')),
)
@click.option(
    '--frame-window',
    '-w',
    metavar='VAL',
    type=click.INT,
    default=None,
    help='Size of window (number of frames) before and after each frame to average together in'
    ' order to detect deviations from the mean.%s' %
    (USER_CONFIG.get_help_string('detect-adaptive', 'frame-window')),
)
@click.option(
    '--luma-only',
    '-l',
    is_flag=True,
    flag_value=True,
    help='Only consider luma/brightness channel (useful for greyscale videos).%s' %
    (USER_CONFIG.get_help_string('detect-adaptive', 'luma-only')),
)
@click.option(
    '--min-scene-len',
    '-m',
    metavar='TIMECODE',
    type=click.STRING,
    default=None,
    help='Minimum length of any scene. Overrides global min-scene-len (-m) setting.'
    ' TIMECODE can be specified as exact number of frames, a time in seconds followed by s,'
    ' or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.%s' %
    ('' if USER_CONFIG.is_default('detect-adaptive', 'min-scene-len') else
     USER_CONFIG.get_help_string('detect-adaptive', 'min-scene-len')),
)
@click.pass_context
def detect_adaptive_command(
    ctx: click.Context,
    threshold: Optional[float],
    min_delta_hsv: Optional[float],
    frame_window: Optional[int],
    luma_only: bool,
    min_scene_len: Optional[str],
):
    """Perform adaptive detection algorithm on input video.

    detect-adaptive

    detect-adaptive --threshold 3.2
    """
    assert isinstance(ctx.obj, CliContext)

    ctx.obj.handle_detect_adaptive(
        threshold=threshold,
        min_delta_hsv=min_delta_hsv,
        frame_window=frame_window,
        luma_only=luma_only,
        min_scene_len=min_scene_len,
    )


@click.command('detect-threshold')
@click.option(
    '--threshold',
    '-t',
    metavar='VAL',
    type=click.FloatRange(CONFIG_MAP['detect-threshold']['threshold'].min_val,
                          CONFIG_MAP['detect-threshold']['threshold'].max_val),
    default=None,
    help='Threshold value (integer) that the delta_rgb frame metric must exceed to trigger'
    ' a new scene. Refers to frame metric delta_rgb in stats file.%s' %
    (USER_CONFIG.get_help_string('detect-threshold', 'threshold')),
)
@click.option(
    '--fade-bias',
    '-f',
    metavar='PERCENT',
    type=click.FloatRange(CONFIG_MAP['detect-threshold']['fade-bias'].min_val,
                          CONFIG_MAP['detect-threshold']['fade-bias'].max_val),
    default=None,
    help='Percent (%%) from -100 to 100 of timecode skew for where cuts should be placed. -100'
    ' indicates the start frame, +100 indicates the end frame, and 0 is the middle of both.%s' %
    (USER_CONFIG.get_help_string('detect-threshold', 'fade-bias')),
)
@click.option(
    '--add-last-scene',
    '-l',
    is_flag=True,
    flag_value=True,
    help='If set, if the video ends on a fade-out, a final scene will be generated from the'
    ' last fade-out position to the end of the video.%s' %
    (USER_CONFIG.get_help_string('detect-threshold', 'add-last-scene')),
)
@click.option(
    '--min-scene-len',
    '-m',
    metavar='TIMECODE',
    type=click.STRING,
    default=None,
    help='Minimum length of any scene. Overrides global min-scene-len (-m) setting.'
    ' TIMECODE can be specified as exact number of frames, a time in seconds followed by s,'
    ' or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.%s' %
    ('' if USER_CONFIG.is_default('detect-threshold', 'min-scene-len') else
     USER_CONFIG.get_help_string('detect-threshold', 'min-scene-len')),
)
@click.pass_context
def detect_threshold_command(
    ctx: click.Context,
    threshold: Optional[float],
    fade_bias: Optional[float],
    add_last_scene: bool,
    min_scene_len: Optional[str],
):
    """Perform threshold detection algorithm on input video.

    detect-threshold

    detect-threshold --threshold 15
    """
    assert isinstance(ctx.obj, CliContext)

    ctx.obj.handle_detect_threshold(
        threshold=threshold,
        fade_bias=fade_bias,
        add_last_scene=add_last_scene,
        min_scene_len=min_scene_len,
    )


@click.command('detect-hash')
@click.option(
    '--threshold', '-t', metavar='VAL',
    type=click.FLOAT, default=100.0, show_default=True, help=
    'Threshold value (float) that the hash_dist metric must exceed to trigger'
    ' a new scene. Refers to frame metric hash_dist in the stats file.'
)
@click.option(
    '--size', '-s', metavar='VAL',
    type=click.IntRange(min=2), default=16, show_default=True, help=
    'Size of the hash used in the perceptual hasing algorithm. Must be an '
    'integer >=2.'
)
@click.option(
    '--freq_factor', '-f', metavar='VAL',
    type=click.IntRange(min=1), default=2, show_default=True, help=
    'Parameter used to specify the amount of high frequency image information '
    'used for the perceptual hashing algorithm. A high value uses less high '
    'frequency image information, meaning that the algorithm is less sensitive '
    'to small changes. A low value causes the algorithm to be more sensitive to'
    ' small changes. Must be an integer >0.'
)
@click.option(
    '--min-scene-len',
    '-m',
    metavar='TIMECODE',
    type=click.STRING,
    default=None,
    help='Minimum length of any scene. Overrides global min-scene-len (-m) setting.'
    ' TIMECODE can be specified as exact number of frames, a time in seconds followed by s,'
    ' or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.%s' %
    ('' if USER_CONFIG.is_default('detect-hash', 'min-scene-len') else
     USER_CONFIG.get_help_string('detect-hash', 'min-scene-len'))
)
@click.pass_context
def detect_hash_command(
    ctx: click.Context,
    threshold: Optional[float],
    size: Optional[int],
    freq_factor: Optional[int],
    min_scene_len: Optional[str]
    ):
    """ Perform perceptual hashing based scene detection on input video(s).
    detect-hash
    detect-hash --threshold 27.5
    detect-hash --threshold 100 --size 16 --freq_factor 2
    """
    assert isinstance(ctx.obj, CliContext)

    ctx.obj.handle_detect_hash(
        threshold=threshold,
        min_scene_len=min_scene_len,
        hash_size=size,
        highfreq_factor=freq_factor
    )


@click.command('export-html')
@click.option(
    '--filename',
    '-f',
    metavar='NAME',
    default='$VIDEO_NAME-Scenes.html',
    type=click.STRING,
    help='Filename format to use for the scene list HTML file. You can use the'
    ' $VIDEO_NAME macro in the file name. Note that you may have to wrap'
    ' the format name using single quotes.%s' %
    (USER_CONFIG.get_help_string('export-html', 'filename')),
)
@click.option(
    '--no-images',
    is_flag=True,
    flag_value=True,
    help='Export the scene list including or excluding the saved images.%s' %
    (USER_CONFIG.get_help_string('export-html', 'no-images')),
)
@click.option(
    '--image-width',
    '-w',
    metavar='pixels',
    type=click.INT,
    help='Width in pixels of the images in the resulting HTML table.%s' %
    (USER_CONFIG.get_help_string('export-html', 'image-width', show_default=False)),
)
@click.option(
    '--image-height',
    '-h',
    metavar='pixels',
    type=click.INT,
    help='Height in pixels of the images in the resulting HTML table.%s' %
    (USER_CONFIG.get_help_string('export-html', 'image-height', show_default=False)),
)
@click.pass_context
def export_html_command(
    ctx: click.Context,
    filename: Optional[AnyStr],
    no_images: bool,
    image_width: Optional[int],
    image_height: Optional[int],
):
    """Export scene list to HTML file. Requires `save-images` unless --no-images is specified."""
    assert isinstance(ctx.obj, CliContext)
    ctx.obj.handle_export_html(
        filename=filename,
        no_images=no_images,
        image_width=image_width,
        image_height=image_height,
    )


@click.command('list-scenes')
@click.option(
    '--output',
    '-o',
    metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help='Output directory to save videos to. Overrides global option -o/--output if set.%s' %
    (USER_CONFIG.get_help_string('list-scenes', 'output', show_default=False)),
)
@click.option(
    '--filename',
    '-f',
    metavar='NAME',
    default='$VIDEO_NAME-Scenes.csv',
    type=click.STRING,
    help='Filename format to use for the scene list CSV file. You can use the'
    ' $VIDEO_NAME macro in the file name. Note that you may have to wrap'
    ' the name using single quotes.%s' % (USER_CONFIG.get_help_string('list-scenes', 'filename')),
)
@click.option(
    '--no-output-file',
    '-n',
    is_flag=True,
    flag_value=True,
    help='Disable writing scene list CSV file to disk.  If set, -o/--output and'
    ' -f/--filename are ignored.%s' %
    (USER_CONFIG.get_help_string('list-scenes', 'no-output-file')),
)
@click.option(
    '--quiet',
    '-q',
    is_flag=True,
    flag_value=True,
    help='Suppresses output of the table printed by the list-scenes command.%s' %
    (USER_CONFIG.get_help_string('list-scenes', 'quiet')),
)
@click.option(
    '--skip-cuts',
    '-s',
    is_flag=True,
    flag_value=True,
    help='Skips outputting the cutting list as the first row in the CSV file.'
    ' Set this option if compliance with RFC 4180 is required.%s' %
    (USER_CONFIG.get_help_string('list-scenes', 'skip-cuts')),
)
@click.pass_context
def list_scenes_command(
    ctx: click.Context,
    output: Optional[AnyStr],
    filename: Optional[AnyStr],
    no_output_file: bool,
    quiet: bool,
    skip_cuts: bool,
):
    """Print scene list and outputs to a CSV file. Ddefault filename is $VIDEO_NAME-Scenes.csv."""
    assert isinstance(ctx.obj, CliContext)
    ctx.obj.handle_list_scenes(
        output=output,
        filename=filename,
        no_output_file=no_output_file,
        quiet=quiet,
        skip_cuts=skip_cuts,
    )


@click.command('split-video')
@click.option(
    '--output',
    '-o',
    metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help='Output directory to save videos to. Overrides global option -o/--output if set.%s' %
    (USER_CONFIG.get_help_string('split-video', 'output', show_default=False)),
)
@click.option(
    '--filename',
    '-f',
    metavar='NAME',
    default=None,
    type=click.STRING,
    help='File name format to use when saving videos (with or without extension). You can use the'
    ' $VIDEO_NAME and $SCENE_NUMBER macros in the filename (e.g. $VIDEO_NAME-Part-$SCENE_NUMBER).'
    ' Note that you may have to wrap the format in single quotes to avoid variable expansion.%s' %
    (USER_CONFIG.get_help_string('split-video', 'filename')),
)
@click.option(
    '--quiet',
    '-q',
    is_flag=True,
    flag_value=True,
    help='Hides any output from the external video splitting tool.%s' %
    (USER_CONFIG.get_help_string('split-video', 'quiet')),
)
@click.option(
    '--copy',
    '-c',
    is_flag=True,
    flag_value=True,
    help='Copy instead of re-encode. Much faster, but less precise. Equivalent to specifying'
    ' -a "-c:v copy -c:a copy".%s' % (USER_CONFIG.get_help_string('split-video', 'copy')),
)
@click.option(
    '--high-quality',
    '-hq',
    is_flag=True,
    flag_value=True,
    help='Encode video with higher quality, overrides -f option if present.'
    ' Equivalent to specifying --rate-factor 17 and --preset slow.%s' %
    (USER_CONFIG.get_help_string('split-video', 'high-quality')),
)
@click.option(
    '--rate-factor',
    '-crf',
    metavar='RATE',
    default=None,
    type=click.IntRange(CONFIG_MAP['split-video']['rate-factor'].min_val,
                        CONFIG_MAP['split-video']['rate-factor'].max_val),
    help='Video encoding quality (x264 constant rate factor), from 0-100, where lower'
    ' values represent better quality, with 0 indicating lossless.%s' %
    (USER_CONFIG.get_help_string('split-video', 'rate-factor')),
)
@click.option(
    '--preset',
    '-p',
    metavar='LEVEL',
    default=None,
    type=click.Choice(CHOICE_MAP['split-video']['preset']),
    help='Video compression quality preset (x264 preset). Can be one of: ultrafast, superfast,'
    ' veryfast, faster, fast, medium, slow, slower, and veryslow. Faster modes take less'
    ' time to run, but the output files may be larger.%s' %
    (USER_CONFIG.get_help_string('split-video', 'preset')),
)
@click.option(
    '--args',
    '-a',
    metavar='ARGS',
    type=click.STRING,
    default=None,
    help='Override codec arguments/options passed to FFmpeg when splitting and re-encoding'
    ' scenes. Use double quotes (") around specified arguments. Must specify at least'
    ' audio/video codec to use (e.g. -a "-c:v [...] -c:a [...]").%s' %
    (USER_CONFIG.get_help_string('split-video', 'args')),
)
@click.option(
    '--mkvmerge',
    '-m',
    is_flag=True,
    flag_value=True,
    help='Split the video using mkvmerge. Faster than re-encoding, but less precise. The output'
    ' will be named $VIDEO_NAME-$SCENE_NUMBER.mkv. If set, all options other than -f/--filename,'
    ' -q/--quiet and -o/--output will be ignored. Note that mkvmerge automatically appends a'
    'suffix of "-$SCENE_NUMBER".%s' % (USER_CONFIG.get_help_string('split-video', 'mkvmerge')),
)
@click.pass_context
def split_video_command(
    ctx: click.Context,
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
    """Split input video using ffmpeg or mkvmerge."""
    assert isinstance(ctx.obj, CliContext)
    ctx.obj.handle_split_video(
        output=output,
        filename=filename,
        quiet=quiet,
        copy=copy,
        high_quality=high_quality,
        rate_factor=rate_factor,
        preset=preset,
        args=args,
        mkvmerge=mkvmerge,
    )


@click.command('save-images')
@click.option(
    '--output',
    '-o',
    metavar='DIR',
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help='Output directory to save images to. Overrides global option -o/--output if set.%s' %
    (USER_CONFIG.get_help_string('save-images', 'output', show_default=False)),
)
@click.option(
    '--filename',
    '-f',
    metavar='NAME',
    default=None,
    type=click.STRING,
    help='Filename format, *without* extension, to use when saving image files. You can use the'
    ' $VIDEO_NAME, $SCENE_NUMBER, $IMAGE_NUMBER, and $FRAME_NUMBER macros in the file name.'
    ' Note that you may have to wrap the format in single quotes.%s' %
    (USER_CONFIG.get_help_string('save-images', 'filename')),
)
@click.option(
    '--num-images',
    '-n',
    metavar='N',
    default=None,
    type=click.INT,
    help='Number of images to generate. Will always include start/end frame,'
    ' unless N = 1, in which case the image will be the frame at the mid-point'
    ' in the scene.%s' % (USER_CONFIG.get_help_string('save-images', 'num-images')),
)
@click.option(
    '--jpeg',
    '-j',
    is_flag=True,
    flag_value=True,
    help='Set output format to JPEG (default).%s' %
    (USER_CONFIG.get_help_string('save-images', 'format', show_default=False)),
)
@click.option(
    '--webp',
    '-w',
    is_flag=True,
    flag_value=True,
    help='Set output format to WebP',
)
@click.option(
    '--quality',
    '-q',
    metavar='Q',
    default=None,
    type=click.IntRange(0, 100),
    help='JPEG/WebP encoding quality, from 0-100 (higher indicates better quality).'
    ' For WebP, 100 indicates lossless. [default: JPEG: 95, WebP: 100]%s' %
    (USER_CONFIG.get_help_string('save-images', 'quality', show_default=False)),
)
@click.option(
    '--png',
    '-p',
    is_flag=True,
    flag_value=True,
    help='Set output format to PNG.',
)
@click.option(
    '--compression',
    '-c',
    metavar='C',
    default=None,
    type=click.IntRange(0, 9),
    help='PNG compression rate, from 0-9. Higher values produce smaller files but result'
    ' in longer compression time. This setting does not affect image quality, only'
    ' file size.%s' % (USER_CONFIG.get_help_string('save-images', 'compression')),
)
@click.option(
    '-m',
    '--frame-margin',
    metavar='N',
    default=None,
    type=click.INT,
    help='Number of frames to ignore at the beginning and end of scenes when saving images.%s' %
    (USER_CONFIG.get_help_string('save-images', 'num-images')),
)
@click.option(
    '--scale',
    '-s',
    metavar='S',
    default=None,
    type=click.FLOAT,
    help='Optional factor by which saved images are rescaled. A scaling factor of 1 would'
    ' not result in rescaling. A value <1 results in a smaller saved image, while a'
    ' value >1 results in an image larger than the original. This value is ignored if'
    ' either the height, -h, or width, -w, values are specified.%s' %
    (USER_CONFIG.get_help_string('save-images', 'scale', show_default=False)),
)
@click.option(
    '--height',
    '-h',
    metavar='H',
    default=None,
    type=click.INT,
    help='Optional value for the height of the saved images. Specifying both the height'
    ' and width, -w, will resize images to an exact size, regardless of aspect ratio.'
    ' Specifying only height will rescale the image to that number of pixels in height'
    ' while preserving the aspect ratio.%s' %
    (USER_CONFIG.get_help_string('save-images', 'height', show_default=False)),
)
@click.option(
    '--width',
    '-w',
    metavar='W',
    default=None,
    type=click.INT,
    help='Optional value for the width of the saved images. Specifying both the width'
    ' and height, -h, will resize images to an exact size, regardless of aspect ratio.'
    ' Specifying only width will rescale the image to that number of pixels wide'
    ' while preserving the aspect ratio.%s' %
    (USER_CONFIG.get_help_string('save-images', 'width', show_default=False)),
)
@click.pass_context
def save_images_command(
    ctx: click.Context,
    output: Optional[AnyStr],
    filename: Optional[AnyStr],
    num_images: Optional[int],
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
    """Create images for each detected scene."""
    assert isinstance(ctx.obj, CliContext)
    ctx.obj.handle_save_images(
        num_images=num_images,
        output=output,
        filename=filename,
        jpeg=jpeg,
        webp=webp,
        quality=quality,
        png=png,
        compression=compression,
        frame_margin=frame_margin,
        scale=scale,
        height=height,
        width=width,
    )


# ----------------------------------------------------------------------
# Commands Omitted From Help List
# ----------------------------------------------------------------------

# Info Commands
scenedetect_cli.add_command(help_command)
scenedetect_cli.add_command(version_command)
scenedetect_cli.add_command(about_command)

# ----------------------------------------------------------------------
# Commands Added To Help List
# ----------------------------------------------------------------------

# Input / Output
_add_cli_command(scenedetect_cli, time_command)
_add_cli_command(scenedetect_cli, export_html_command)
_add_cli_command(scenedetect_cli, list_scenes_command)
_add_cli_command(scenedetect_cli, save_images_command)
_add_cli_command(scenedetect_cli, split_video_command)

# Detection Algorithms
_add_cli_command(scenedetect_cli, detect_content_command)
_add_cli_command(scenedetect_cli, detect_threshold_command)
_add_cli_command(scenedetect_cli, detect_adaptive_command)
_add_cli_command(scenedetect_cli, detect_hash_command)
