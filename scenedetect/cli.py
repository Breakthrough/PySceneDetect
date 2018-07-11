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

""" PySceneDetect scenedetect.cli Module

This file contains the implementation of the PySceneDetect command-line
interface (CLI) parser, which uses the click library.  The main CLI
entry-point function is the scenedetect_cli command group.
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
from scenedetect.cli_context import CliContext
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_manager import VideoManager


# Preface/intro help message shown at the beginning of the help command.
def get_help_command_preface(command_name='scenedetect'):
    command_name = (command_name,) * 3
    return """
The PySceneDetect command-line interface is grouped into commands which
can be combined together, each containing its own set of arguments:

 > %s ([options]) [command] ([options]) ([...other command(s)...])

Where [command] is the name of the command, and ([options]) are the
arguments/options associated with the command, if any. The order of
commands is not strict, but each command should only be specified once.

Commands can also be combined, for example, running the 'detect_threshold'
and 'detect_content' (specifying options for the latter):

 > %s input -i vid0001.mp4 detect_threshold detect_content --threshold 20

A list of all commands is printed below. Help for a particular command
can be printed by specifying 'help [command]', or 'help all' to print
the help information for every command.

Lastly, there are several commands used for displaying application
version and copyright information (e.g. %s about):

    version: Displays the version of PySceneDetect being used.
    about:   Displays PySceneDetect license and copyright information.
""" % command_name


CLICK_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

COMMAND_LIST = []


def add_cli_command(cli, command):
    cli.add_command(command)
    COMMAND_LIST.append(command)


def get_command(command_name):
    command_ref = None
    for command in COMMAND_LIST:
        if command.name == command_name:
            command_ref = command
            break
    return command_ref


def parse_timecode(ctx, value):
    ctx.obj.check_input_open()
    if value is None:
        return value
    try:
        timecode = FrameTimecode(
            timecode=value, fps=ctx.obj.video_manager.get_framerate())
        return timecode
    except (ValueError, TypeError):
        raise click.BadParameter(
            'timecode must be in frames (1234), seconds (123.4s), or HH:MM:SS (00:02:03.400)')


def print_command_help(ctx, command):
    ctx_name = ctx.info_name
    ctx.info_name = command.name
    click.echo(click.style('PySceneDetect %s Command' % command.name, fg='cyan'))
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(command.get_help(ctx))
    click.echo('')
    ctx.info_name = ctx_name


def print_command_list_header():
    click.echo(click.style('PySceneDetect Option/Command List:', fg='green'))
    click.echo(click.style('----------------------------------------------------', fg='green'))
    click.echo('')


def print_help_header():
    click.echo(click.style('----------------------------------------------------', fg='yellow'))
    click.echo(click.style(' PySceneDetect %s Help' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='yellow'))


@click.group(chain=True, context_settings=CLICK_CONTEXT_SETTINGS)
@click.option(
    '--input', '-i',
    multiple=True, required=False, metavar='VIDEO',
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=True), help=
    'Input video file. May be specified multiple times to concatenate several videos together.')
@click.option(
    '--framerate', '-f', metavar='FPS',
    type=click.FLOAT, default=None, help=
    '[Optional] Force framerate, in frames/sec (e.g. -f 29.97). Disables check to ensure that all '
    ' input video framerates are equal.')
@click.option(
    '--stats', '-s', metavar='CSV',
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False), help=
    '[Optional] Path to stats file (.csv) for writing frame metrics to. If the file exists, any'
    ' metrics will be processed, otherwise a new file will be created. Can be used to determine'
    ' optimal values for various scene detector options, and to cache frame calculations in order'
    ' to speed up multiple detection runs.')
@click.option(
    '--info-level', '-il', metavar='LEVEL',
    type=click.Choice([ 'debug', 'info', 'warning', 'error']), default=None, help=
    '[Optional] Level of debug/info/error information to show.')
@click.option(
    '--logfile', '-l', metavar='LOG',
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=True), help=
    '[Optional] Path to log file for writing application logging information (debug/errors).')
@click.pass_context
def scenedetect_cli(ctx, input, framerate, stats, info_level, logfile):
    ctx.call_on_close(ctx.obj.process_input)
    
    logging.disable(logging.NOTSET)
    if logfile is not None:
        logging.basicConfig(filename=logfile, filemode='w+',
        level=getattr(logging, info_level.upper()) if info_level is not None else info_level)
    else:
        if info_level is not None:
            logging.basicConfig(level=getattr(logging, info_level.upper()))
        else:
            logging.disable(logging.CRITICAL)
    
    ctx.obj.input_videos(input, framerate)
    ctx.obj.stats_file_path = stats


@click.command('help', add_help_option=False)
@click.argument('command_name', required=False, type=click.STRING)
@click.pass_context
def help_command(ctx, command_name):
    ctx.obj.process_input_flag = False
    if command_name is not None:
        if command_name.lower() == 'all':
            print_help_header()
            click.echo(get_help_command_preface(ctx.parent.info_name))
            print_command_list_header()
            click.echo(ctx.parent.get_help())
            for command in COMMAND_LIST:
                print_command_help(ctx, command)
        else:
            command = get_command(command_name)
            if command is None:
                error_strs = [
                    'unknown command.', 'List of valid commands:',
                    '  %s' % ', '.join([command.name for command in COMMAND_LIST]) ]
                raise click.BadParameter('\n'.join(error_strs), param_hint='command name')
            click.echo('')
            print_command_help(ctx, command)
    else:
        print_help_header()
        click.echo(get_help_command_preface(ctx.parent.info_name))
        print_command_list_header()
        click.echo(ctx.parent.get_help())
        click.echo("\nType '%s help [command]' for usage/help of [command], or" % ctx.parent.info_name)
        click.echo("'%s help all' to list usage information for every command." % (ctx.parent.info_name))
    ctx.exit()


@click.command('about', add_help_option=False)
@click.pass_context
def about_command(ctx):
    ctx.obj.process_input_flag = False
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(click.style(' About PySceneDetect %s' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(scenedetect.ABOUT_STRING)
    ctx.exit()


@click.command('version', add_help_option=False)
@click.pass_context
def version_command(ctx):
    ctx.obj.process_input_flag = False
    click.echo(click.style('PySceneDetect %s' % scenedetect.__version__, fg='yellow'))
    ctx.exit()


@click.command('time', add_help_option=False)
@click.option(
    '--start', '-s', metavar='TIMECODE',
    type=click.STRING, default='0', show_default=True, help=
    '[Optional] Time in video to begin detecting scenes. TIMECODE can be specified as exact'
    ' number of frames (-s 100 to start at frame 100), time in seconds followed by s'
    ' (-s 100s to start at 100 seconds), or a timecode in the format HH:MM:SS or HH:MM:SS.nnn'
    ' (-s 00:01:40 to start at 1m40s).')
@click.option(
    '--duration', '-d', metavar='TIMECODE',
    type=click.STRING, default=None, help=
    '[Optional] Maximum time in video to process. TIMECODE format is the same as other'
    ' arguments. Mutually exclusive with --end / -e.')
@click.option(
    '--end', '-e', metavar='TIMECODE',
    type=click.STRING, default=None, help=
    '[Optional] Time in video to end detecting scenes. TIMECODE format is the same as other'
    ' arguments. Mutually exclusive with --duration / -d.')
@click.pass_context
def time_command(ctx, start, duration, end):
    """ 
    time --start 00:01:00 --duration 100s

    time --start 0 --end 1000
    """
    start = parse_timecode(ctx, start)
    duration = parse_timecode(ctx, duration)
    end = parse_timecode(ctx, end)

    ctx.obj.time_command(start, duration, end)


@click.command('detect-content', add_help_option=False)
@click.option(
    '--threshold', '-t', metavar='VAL',
    type=click.FLOAT, default=30.0, show_default=True, help=
    '[Optional] Threshold value the delta_hsv frame metric must exceed to trigger a new scene.')
@click.pass_context
def detect_content_command(ctx, threshold):
    """ 
    detect-content

    detect-content --threshold 30
    """
    click.echo('detect_content, threshold: %s' % threshold)
    # Initialize detector and add to scene manager.
    # Need to ensure that a detector is not added twice, or will cause
    # a frame metric key error when registering the detector.


@click.command('output', add_help_option=False)
@click.option('--output-option', '-oo')
@click.pass_context
def output_command(ctx, output_option):
    click.echo('output, output_option: %s' % output_option)
    pass


# Info/Terminating Commands:
add_cli_command(scenedetect_cli, help_command)
add_cli_command(scenedetect_cli, about_command)
add_cli_command(scenedetect_cli, version_command)

# Commands Added To Help List:
add_cli_command(scenedetect_cli, time_command)
add_cli_command(scenedetect_cli, detect_content_command)
add_cli_command(scenedetect_cli, output_command)
