# Generate formatted CLI documentation for PySceneDetect.
#
# Inspired by sphinx-click: https://github.com/click-contrib/sphinx-click
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
"""Generates CLI reference documentation file docs/cli.rst.

Run from main repo folder as working directory."""

import inspect
import os
import re
import sys
import typing as ty
from dataclasses import dataclass

# Add parent folder to path so we can resolve `scenedetect` imports.
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# Third-party imports
import click

from scenedetect._cli import scenedetect

StrGenerator = ty.Generator[str, None, None]

INDENT = " " * 4

PAGE_SEP = "*" * 72
TITLE_SEP = "=" * 72
HEADING_SEP = "-" * 72

OPTION_HELP_OVERRIDES = {
    "scenedetect": {
        "config": "Path to config file. See :ref:`config file reference <scenedetect_cli-config_file>` for details."
    },
}

TITLE_LEVELS = ["*", "=", "-"]

INFO_COMMANDS = ["help", "about", "version"]

INFO_COMMAND_OVERRIDE = """
.. _command-help:

``help``, ``version``, and ``about``
=======================================================================

.. program:: scenedetect help

``scenedetect --help`` will print PySceneDetect options, commands, and examples. You can also specify:

 * ``scenedetect [command] --help`` to show options and examples *for* a command or detector

 * ``scenedetect help`` command to print full reference of all options, commands, and examples

.. program:: scenedetect version

``scenedetect version`` prints the version of PySceneDetect that is installed, as well as system dependencies.

.. program:: scenedetect about

``scenedetect about`` prints PySceneDetect copyright, licensing, and redistribution information. This includes a list of all third-party software components that PySceneDetect uses or interacts with, as well as a reference to the license and copyright information for each component.
"""


def patch_help(s: str, commands: ty.List[str]) -> str:
    # Patch some TODOs still not handled correctly below.
    pos = 0
    while True:
        pos = s.find("global option :option:", pos)
        if pos < 0:
            break
        pos = s.find("<-", pos)
        assert pos > 0
        s = s[: pos + 1] + "scenedetect " + s[pos + 1 :]

    for command in [command for command in commands if command not in INFO_COMMANDS]:

        def add_link(_match: re.Match) -> str:
            return ":ref:`%s <command-%s>`" % (command, command)

        s = re.sub("``%s``(?!\\n)" % command, add_link, s)
    return s


def generate_title(s: str, level: int = 0, len: int = 72) -> StrGenerator:
    yield "\n"
    if level == 0:
        yield TITLE_LEVELS[level] * len + "\n"
    yield s + "\n"
    yield TITLE_LEVELS[level] * len + "\n\n"


@dataclass
class ReplaceWithReference:
    range: ty.Tuple[int, int]
    ref: str
    ref_type: str


def transform_backquotes(s: str) -> str:
    return s.replace("``", "`").replace("`", "``")


def add_backquotes(match: re.Match) -> str:
    return "``%s``" % match.string[match.start() : match.end()]


def add_backquotes_with_refs(refs: ty.Set[str]) -> ty.Callable[[str], str]:
    """Returns a transformation function that backquotes command examples, adding backquotes and
    references to any found options."""

    def _add_backquotes(s: re.Match) -> str:
        to_add: str = s.string[s.start() : s.end()]
        flag = re.search("-+[\w-]+[^\.\=\s\/]*", to_add)
        if flag is not None and flag.string[flag.start() : flag.end()] in refs:
            # add cross reference
            cross_ref = flag.string[flag.start() : flag.end()]
            option = s.string[s.start() : s.end()]
            return ":option:`%s <%s>`" % (option, cross_ref)
        else:
            return add_backquotes(s)

    return _add_backquotes


def extract_default_value(s: str) -> ty.Tuple[str, ty.Optional[str]]:
    default = re.search("\[default: .*\]", s)
    if default is not None:
        span = default.span()
        assert span[1] == len(s)
        s, default = s[: span[0]].strip(), s[span[0] : span[1]][len("[default: ") : -1]
        # Double-quote any default values that contain spaces.
        if " " in default and '"' not in default and "," not in default:
            default = '"%s"' % default
    return (s, default)


def transform_add_option_refs(s: str, refs: ty.List[str]) -> str:
    transform = add_backquotes_with_refs(refs)
    # TODO: Match prefix of `global option` and add ref to parent `scenedetect` command option.
    # Replace patch to complete this.
    #  -c/--command
    s = re.sub("-\w/--\w[\w-]*", transform, s)
    #  --arg=value, --arg=1.2.3, --arg=1,2,3
    s = re.sub('-+[\w-]+=[^"\s\)]+(?<![\.\,])', transform, s)
    # --args=" command with spaces"
    s = re.sub('--[\w-]+[=]+".*?"', transform, s)
    return s


def format_option(command: click.Command, opt: click.Option, flags: ty.List[str]) -> StrGenerator:
    if isinstance(opt, click.Argument):
        yield "\n.. option:: %s\n" % opt.name
        return
    yield "\n.. option:: %s\n" % ", ".join(
        arg if opt.metavar is None else "%s %s" % (arg, opt.metavar)
        for arg in sorted(opt.opts, reverse=True)
    )

    help = (
        OPTION_HELP_OVERRIDES[command.name][opt.name]
        if command.name in OPTION_HELP_OVERRIDES and opt.name in OPTION_HELP_OVERRIDES[command.name]
        else opt.help.strip()
    )

    # TODO: Make metavars link to the option as well.
    help, default = extract_default_value(help)
    help = transform_add_option_refs(help, flags)

    yield "\n  %s\n" % help
    if default is not None:
        yield "\n  Default: ``%s``\n" % default


def generate_command_help(
    ctx: click.Context, command: click.Command, parent_name: ty.Optional[str] = None
) -> StrGenerator:
    # TODO: Add references to long options. Requires splitting out examples.
    # TODO: Add references to subcommands. Need to add actual refs, since programs can't be ref'd.
    # TODO: Handle dollar signs in examples by having both escaped and unescaped versions
    yield "\n.. _command-%s:\n" % command.name
    yield "\n.. program:: %s\n\n" % (
        command.name if parent_name is None else "%s %s" % (parent_name, command.name)
    )
    if parent_name:
        yield from generate_title("``%s``" % command.name, 1)

    replacements = [
        opt
        for opts in [param.opts for param in command.params if hasattr(param, "opts")]
        for opt in opts
    ]

    help = command.help
    help = help.replace(
        "Examples:\n", "".join(generate_title("Examples", 0 if not parent_name else 2))
    )
    help = help.replace("\b\n", "")
    help = help.format(scenedetect="scenedetect", scenedetect_with_video="scenedetect -i video.mp4")
    help = transform_backquotes(help)
    help = transform_add_option_refs(help, replacements)

    for line in help.strip().splitlines():
        if line.startswith(INDENT):
            indent = line.count(INDENT)
            line = line.strip()
            yield "%s``%s``\n" % (indent * INDENT, line) if line else "\n"
        else:
            yield "%s\n" % line

    if command.params:
        yield "\n"
        yield from generate_title("Options", 0 if not parent_name else 2)
        for param in command.params:
            yield from format_option(command, param, replacements)
    yield "\n"


def generate_subcommands(ctx: click.Context, commands: ty.List[str]) -> StrGenerator:
    processed = set()

    for info_command in INFO_COMMANDS:
        assert info_command in commands
        processed.add(info_command)
    yield INFO_COMMAND_OVERRIDE

    yield from generate_title("Detectors", 0)
    detectors = [command for command in commands if command.startswith("detect-")]
    for detector in detectors:
        yield from generate_command_help(ctx, ctx.command.get_command(ctx, detector), ctx.info_name)
        processed.add(detector)

    yield from generate_title("Commands", 0)
    output_commands = [
        command
        for command in commands
        if (not command.startswith("detect-") and command not in INFO_COMMANDS)
    ]
    for command in output_commands:
        yield from generate_command_help(ctx, ctx.command.get_command(ctx, command), ctx.info_name)
        processed.add(command)

    assert set(commands) == processed


def create_help() -> ty.Tuple[str, ty.List[str]]:
    ctx = click.Context(scenedetect, info_name=scenedetect.name)

    commands: ty.List[str] = ctx.command.list_commands(ctx)
    commands = list(filter(lambda command: not ctx.command.hidden, commands))
    # ctx.to_info_dict lacks metavar so we have to use the context directly.
    actions = [
        generate_title("``scenedetect`` 🎬 Command", level=0),
        generate_command_help(ctx, ctx.command),
        generate_subcommands(ctx, commands),
    ]
    lines = []
    for action in actions:
        lines.extend(action)
    return "".join(lines), commands


def main():
    help, commands = create_help()
    help = patch_help(help, commands)
    help = ".. NOTE: This file is auto-generated by docs/generate_cli_docs.py and should not be modified.\n" + help
    with open("docs/cli.rst", "wb") as f:
        f.write(help.encode())


if __name__ == "__main__":
    main()
