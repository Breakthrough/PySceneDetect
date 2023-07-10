# Generate formatted CLI documentation for PySceneDetect.
#
# Inspired by sphinx-click: https://github.com/click-contrib/sphinx-click
#
# Copyright (C) 2014-2023 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.

import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import click
import json
import typing as ty
from scenedetect._cli import scenedetect_command

StringGenerator = ty.Generator[str, None, None]

INDENT = ' ' * 4

PAGE_SEP = '*' * 72
TITLE_SEP = '=' * 72
HEADING_SEP = '-' * 72


def format_option(opt: click.Option) -> StringGenerator:
    if isinstance(opt, click.Argument):
        yield '\n.. option:: %s\n' % opt.name
        return
    yield '\n.. option:: %s\n' % ', '.join(
        arg if opt.metavar is None else '%s %s' % (arg, opt.metavar) for arg in sorted(opt.opts))
    help = opt.help
    # TODO: Escape ':' in all help strings
    if help.endswith(']') and help.find('[default: '):
        help = help.replace('[default: ', '[default: `')
        help = '%s`]' % help[:-1]
    yield '\n  %s\n' % help.replace('``', '`').replace('`', '``')


def _generate_command_help(command: click.Command) -> StringGenerator:
    yield '\n\n``%s``\n%s\n\n' % (command.name, TITLE_SEP)
    help = command.help.replace('Examples:\n', 'Examples\n%s\n' %
                        HEADING_SEP).replace('``', '`').replace('`', '``').replace('\b\n', '').format(scenedetect='scenedetect -i video.mp4')

    for line in help.splitlines(keepends=True):
        if line.startswith(INDENT):
            indent = line.count(INDENT)
            line = line.strip()
            yield '%s``%s``' % (indent * INDENT, line) if line else ''
        else:
            yield line
        if not line.endswith('\n'):
            yield '\n'

    if command.params:
        yield '\n'
        yield 'Options\n%s\n' % (HEADING_SEP)

        for param in command.params:
            yield from format_option(param)


def generate_subcommands(ctx: click.Context) -> StringGenerator:
    for command_name in ctx.command.list_commands(ctx):
        yield from _generate_command_help(ctx.command.get_command(ctx, command_name))


def create_help() -> str:
    ctx = click.Context(scenedetect_command, info_name=scenedetect_command.name)
    lines = [
        '%s\n``scenedetect`` Command Reference\n%s' % (PAGE_SEP, PAGE_SEP),
    ]
    lines.extend(_generate_command_help(ctx.command))
    lines.extend(generate_subcommands(ctx))

    return ''.join(lines)


def main():
    help = create_help()
    print(help)


if __name__ == "__main__":
    main()
