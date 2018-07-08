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
interface (CLI) parser, which uses the click library.
"""

# Standard Library Imports
from __future__ import print_function
import sys
import string

# Third-Party Library Imports
import click

# PySceneDetect Library Imports
import scenedetect
from scenedetect.cli_context import CliContext
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.video_manager import VideoManager



# Preface/intro help message shown at the beginning of the help command.
def get_help_command_preface(command_name='scenedetect'):
    command_name = (command_name,) * 5
    return """
The PySceneDetect command-line interface is grouped into commands which
can be combined together, each containing its own set of arguments:

 > %s [command] ([options]) ([...other command(s)...])

Where [command] is the name of the command, and ([options]) are the
arguments/options associated with the command, if any. The 'input'
command must come first, followed by all other commands (the order of
which is not strict). Each command should only be specified once.

For example, to define the 'input' command with a file and framerate:

 > %s input --input vid0001.mp4 --framerate 29.97

Commands can also be combined, for example, running the 'detect_content'
command after the 'input' command:

 > %s input -i vid0001.mp4 -f 29.97 detect_content --threshold 20

A list of all commands is printed below, followed by help information
for all commands, including the options/arguments that they take.
The help message for individual commands can be printed by passing the
--help/-h option to the command (i.e. '%s [command] --help').

Lastly, there are several commands used for displaying application
help, version, and copyright information (e.g. %s about):

    help:    Displays this message, a list of commands, and the help
             text for each command.
    version: Displays the version of PySceneDetect being used.
    about:   Displays PySceneDetect license and copyright information.
""" % command_name



CLICK_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

COMMAND_LIST = []

@click.group(chain=True, context_settings=CLICK_CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx):
    ctx.call_on_close(ctx.obj.cleanup)


def add_cli_command(command):
    cli.add_command(command)
    COMMAND_LIST.append(command)


@click.command('help')
@click.pass_context
def help_command(ctx):
    click.echo(click.style('----------------------------------------------------', fg='yellow'))
    click.echo(click.style(' PySceneDetect %s Help' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='yellow'))
    click.echo(get_help_command_preface(ctx.parent.info_name))

    click.echo(click.style('PySceneDetect Command List:', fg='green'))
    click.echo(click.style('----------------------------------------------------', fg='green'))
    click.echo('  %s' % ', '.join([command.name for command in COMMAND_LIST]))
    click.echo('')

    ctx_name = ctx.info_name
    for command in COMMAND_LIST:
        ctx.info_name = command.name
        click.echo(click.style('PySceneDetect %s Command' % command.name, fg='cyan'))
        click.echo(click.style('----------------------------------------------------', fg='cyan'))
        click.echo(command.get_help(ctx))
        click.echo('')
    ctx.info_name = ctx_name
    ctx.exit()

@click.command('about')
@click.pass_context
def about_command(ctx):
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(click.style(' About PySceneDetect %s' % scenedetect.__version__, fg='yellow'))
    click.echo(click.style('----------------------------------------------------', fg='cyan'))
    click.echo(scenedetect.ABOUT_STRING)
    ctx.exit()

@click.command('version')
@click.pass_context
def version_command(ctx):
    click.echo(click.style('PySceneDetect %s' % scenedetect.__version__, fg='yellow'))
    ctx.exit()


@click.command('input')
@click.option('--input', '-i', multiple=True, type=click.Path(
    exists=True, file_okay=True, readable=True, resolve_path=True))
@click.option('--framerate', '-f', type=float, default=None)
@click.pass_context
def input_command(ctx, input, framerate):
    ctx.obj.input_videos(input, framerate)


    click.echo('Loaded %d videos, framerate = %.2f FPS.' % (
        len(ctx.obj.video_manager._cap_list), ctx.obj.video_manager.get_framerate()))


@click.command('output')
@click.option('--output-option', '-oo')
@click.pass_context
def output_command(ctx, output_option):
    click.echo('Output: %s' % output_option)

# Info/Terminating Commands:
cli.add_command(help_command)
cli.add_command(about_command)
cli.add_command(version_command)

# Commands Added To Help List:
add_cli_command(input_command)
add_cli_command(output_command)
