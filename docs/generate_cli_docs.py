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
import typing as ty
import re
from dataclasses import dataclass

# Add parent folder to path so we can resolve `scenedetect` imports.
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from scenedetect._cli import scenedetect

# Third-party imports
import click

StrGenerator = ty.Generator[str, None, None]

INDENT = ' ' * 4

PAGE_SEP = '*' * 72
TITLE_SEP = '=' * 72
HEADING_SEP = '-' * 72

OPTION_HELP_OVERRIDES = {
    'scenedetect': {
        'config':
            'Path to config file. See :ref:`config file reference <scenedetect_cli-config_file>` for details.'
    },
}


@dataclass
class ReplaceWithReference:
    range: ty.Tuple[int, int]
    ref: str
    ref_type: str


def transform_backquotes(s: str) -> str:
    return s.replace('``', '`').replace('`', '``')


def transform_add_command_refs(s: str, ctx: click.Context) -> str:
    commands = ctx.command.list_commands(ctx)
    for command in commands:
        s = s.replace('``%s``' % command, ':program:`%s <scenedetect %s>`' % (command, command))
    return s


def add_backquotes(match: re.Match) -> str:
    return '``%s``' % match.string[match.start():match.end()]


def add_backquotes_with_refs(refs: ty.Set[str]) -> ty.Callable[[str], str]:
    """Returns a transformation function that backquotes command examples, adding backquotes and
    references to any found options."""

    def _add_backquotes(s: re.Match) -> str:
        to_add: str = s.string[s.start():s.end()]
        flag = re.search('-+[\w-]+[^\.\=\s\/]*', to_add)
        if flag is not None and flag.string[flag.start():flag.end()] in refs:
            # add cross reference
            cross_ref = flag.string[flag.start():flag.end()]
            option = s.string[s.start():s.end()]
            return ':option:`%s <%s>`' % (option, cross_ref)
        else:
            return add_backquotes(s)

    return _add_backquotes


def extract_default_value(s: str) -> ty.Tuple[str, ty.Optional[str]]:
    default = re.search('\[default: .*\]', s)
    if default is not None:
        span = default.span()
        assert span[1] == len(s)
        s, default = s[:span[0]].strip(), s[span[0]:span[1]][len('[default: '):-1]
        # Double-quote any default values that contain spaces.
        if ' ' in default and not '"' in default and not ',' in default:
            default = '"%s"' % default
    return (s, default)


def transform_add_option_refs(s: str, refs: ty.List[str]) -> str:
    transform = add_backquotes_with_refs(refs)
    # TODO: Find `global option -c/--command` and add ref to parent instead.
    #  -c/--command
    s = re.sub('-\w/--\w[\w-]*', transform, s)
    #  --arg=value, --arg=1.2.3, --arg=1,2,3
    s = re.sub('-+[\w-]+=[^"\s\)]+(?<![\.\,])', transform, s)
    # --args=" command with spaces"
    s = re.sub('--[\w-]+[=]+\".*?"', transform, s)
    return s


def format_option(command: click.Command, opt: click.Option, flags: ty.List[str]) -> StrGenerator:
    if isinstance(opt, click.Argument):
        yield '\n.. option:: %s\n' % opt.name
        return
    yield '\n.. option:: %s\n' % ', '.join(arg if opt.metavar is None else '%s %s' %
                                           (arg, opt.metavar)
                                           for arg in sorted(opt.opts, reverse=True))

    help = OPTION_HELP_OVERRIDES[command.name][
        opt.name] if command.name in OPTION_HELP_OVERRIDES and opt.name in OPTION_HELP_OVERRIDES[
            command.name] else opt.help.strip()

    help, default = extract_default_value(help)
    help = transform_add_option_refs(help, flags)

    yield '\n  %s\n' % help
    if default is not None:
        yield '\n  Default: ``%s``\n' % default


def generate_command_help(ctx: click.Context,
                          command: click.Command,
                          parent_name: ty.Optional[str] = None) -> StrGenerator:
    yield '\n\n.. program:: %s' % (
        command.name if parent_name is None else '%s %s' % (parent_name, command.name))
    yield '\n\n``%s``\n%s\n\n' % (command.name, TITLE_SEP)
    # TODO: Add references to long options. Requires splitting out examples.
    help = command.help.replace('Examples:\n', 'Examples\n%s\n' % HEADING_SEP).replace(
        '\b\n', '').format(scenedetect='scenedetect -i video.mp4')

    help = transform_backquotes(help)

    replacements = [
        opt for opts in [param.opts for param in command.params if hasattr(param, 'opts')]
        for opt in opts
    ]

    help = transform_add_command_refs(help, ctx)
    help = transform_add_option_refs(help, replacements)

    for line in help.strip().splitlines():
        if line.startswith(INDENT):
            indent = line.count(INDENT)
            line = line.strip()
            yield '%s``%s``\n' % (indent * INDENT, line) if line else '\n'
        else:
            yield '%s\n' % line

    if command.params:
        yield '\n'
        yield 'Options\n%s\n' % (HEADING_SEP)
        for param in command.params:
            yield from format_option(command, param, replacements)


def generate_subcommands(ctx: click.Context) -> StrGenerator:
    for command_name in ctx.command.list_commands(ctx):
        yield from generate_command_help(ctx, ctx.command.get_command(ctx, command_name),
                                         ctx.info_name)


def create_help() -> str:
    ctx = click.Context(scenedetect, info_name=scenedetect.name)
    #ctx.to_info_dict lacks metavar
    lines = [
        '%s\n``scenedetect`` Command Reference\n%s' % (PAGE_SEP, PAGE_SEP),
    ]
    lines.extend(generate_command_help(ctx, ctx.command))
    lines.extend(generate_subcommands(ctx))

    return ''.join(lines)


def main():
    help = create_help()
    print(help)


if __name__ == "__main__":
    main()
