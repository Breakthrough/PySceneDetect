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

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import click
import json
import typing as ty
from scenedetect._cli import scenedetect

StringGenerator = ty.Generator[str, None, None]

INDENT = ' ' * 4

PAGE_SEP = '*' * 72
TITLE_SEP = '=' * 72
HEADING_SEP = '-' * 72

@dataclass
class ReplaceWithReference:
    range: ty.Tuple[int, int]
    ref: str
    ref_type: str






def transform_backquotes(s: str) -> str:
    return s.replace('``', '`').replace('`', '``')

def add_backquotes_to_match(s: re.Match) -> str:
    return '``%s``' % s.string[s.start():s.end()]

def add_backquotes_with_refs(refs: ty.Set[str]) -> ty.Callable[[str], str]:
    def _add_backquotes(s: re.Match) -> str:
        to_add: str = s.string[s.start():s.end()]
        flag = re.search('-+[\w-]+[^\.\=\s\/]*', to_add)
        if flag is not None and flag.string[flag.start():flag.end()] in refs:
            print("Found cross ref for %s -> %s" % (to_add, flag.string[flag.start():flag.end()]))
            return ':option:`TODO %s`' % to_add
        return to_add
    return _add_backquotes



# TODO: Remove backquotes from CLI docstrings. Add in :option: links when detecting an option
# in the same command.

# TODO: Override help for config file path.

def format_option(opt: click.Option, flags: ty.List[str]) -> StringGenerator:
    if isinstance(opt, click.Argument):
        yield '\n.. option:: %s\n' % opt.name
        return
    yield '\n.. option:: %s\n' % ', '.join(
        arg if opt.metavar is None else '%s %s' % (arg, opt.metavar) for arg in sorted(opt.opts, reverse=True))
    help = opt.help.strip()

    default = re.search('\[default: .*\]', help)
    if default is not None:
        span = default.span()
        assert span[1] == len(help)
        help, default = help[:span[0]], help[span[0]:span[1]][len('[default: '):-1]
        # Double-quote any default values that contain spaces.
        if ' ' in default and not '"' in default:
            default = '"%s"' % default
        print(default)

    # Add backquotes to:
    # [default: ...]
    add_backquotes = add_backquotes_with_refs(flags)

    # TODO: need to return list of spans that need to be backquoted or ref'd. do transformation lazily after finding all.

    #  -c/--command
    help = re.sub('(?<=[\s"(])-\w/--\w[\w-]*', add_backquotes, help)
    #  --arg=value
    help = re.sub('(?<=[\s"(])-+[\w-]+=[^"\.\s\)]+', add_backquotes, help)
    # --args=" command with spaces" and --args "command with spaces"
    help = re.sub('(?<=[\s"(])--[\w-]+[\s=]+\".*?"', add_backquotes, help)

    yield '\n  %s\n' % help
    if default is not None:
        yield '\n  Default: ``%s``\n' % default


def generate_command_help(command: click.Command,
                          parent_name: ty.Optional[str] = None) -> StringGenerator:
    yield '\n\n.. program:: %s' % (
        command.name if parent_name is None else '%s %s' % (parent_name, command.name))
    yield '\n\n``%s``\n%s\n\n' % (command.name, TITLE_SEP)
    help = command.help.replace('Examples:\n', 'Examples\n%s\n' % HEADING_SEP).replace(
        '\b\n', '').format(scenedetect='scenedetect -i video.mp4')
    help = transform_backquotes(help)

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

        # Generate list of argument short/long flags in the form -s/--short-arg.
        replacements = []
        for param in command.params:
            if not hasattr(param, 'opts'):
                continue
            replacements += param.opts
        for param in command.params:
            yield from format_option(param, replacements)


def generate_subcommands(ctx: click.Context) -> StringGenerator:
    for command_name in ctx.command.list_commands(ctx):
        yield from generate_command_help(ctx.command.get_command(ctx, command_name), ctx.info_name)


def create_help() -> str:
    ctx = click.Context(scenedetect, info_name=scenedetect.name)
    #ctx.to_info_dict lacks metavar
    lines = [
        '%s\n``scenedetect`` Command Reference\n%s' % (PAGE_SEP, PAGE_SEP),
    ]
    lines.extend(generate_command_help(ctx.command))
    lines.extend(generate_subcommands(ctx))

    return ''.join(lines)


def main():
    help = create_help()
    print(help)


if __name__ == "__main__":
    main()
