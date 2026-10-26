# Generate formatted CLI documentation for PySceneDetect.
#
# Inspired by sphinx-click: https://github.com/click-contrib/sphinx-click
#
# Copyright (C) 2023 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
"""Generates the CLI reference documentation file docs/cli.rst, cross-linked to the Python API
and the config file from one mapping, `CONCORDANCE`, below.

Also generates:

- docs/cli_index.inc: the nested list of the CLI reference on the index page.
- docs/api/detector_options/<command>.inc (included by docs/api/detectors.rst): one option table
  per detector, from the `detect-*` commands, `CONFIG_MAP`, and the detector constructors. See
  `DETECTOR_OPTIONS` below.
- docs/cli/config_sections.inc (included by docs/cli/config_file.rst): one section per config
  file section, from `CONFIG_MAP` and the shipped template scenedetect.cfg, which must agree
  (see `check_template`).

Run from main repo folder as working directory."""

import inspect
import os
import re
import sys
import typing as ty
from dataclasses import dataclass, field
from enum import Enum

# Add parent folder to path so we can resolve `scenedetect` imports.
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
# Third-party imports (must follow sys.path mutation above).
import click  # noqa: E402

from scenedetect._cli import scenedetect  # noqa: E402
from scenedetect._cli.config import (  # noqa: E402
    CHOICE_MAP,
    CONFIG_MAP,
    TimecodeValue,
    ValidatedValue,
    default_to_str,
)
from scenedetect.detectors import (  # noqa: E402
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
)

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

TITLE_LEVELS = ["*", "=", "-", "^"]

INFO_COMMANDS = ["help", "about", "version"]

INFO_COMMAND_OVERRIDE = """
.. _command-help:

``help``, ``version``, and ``about``
-----------------------------------------------------------------------

.. program:: scenedetect help

``scenedetect --help`` will print PySceneDetect options, commands, and examples. You can also specify:

 * ``scenedetect [command] --help`` to show options and examples *for* a command or detector

 * ``scenedetect help`` command to print full reference of all options, commands, and examples

.. program:: scenedetect version

``scenedetect version`` prints the version of PySceneDetect that is installed, as well as system dependencies.

.. program:: scenedetect about

``scenedetect about`` prints PySceneDetect copyright, licensing, and redistribution information. This includes a list of all third-party software components that PySceneDetect uses or interacts with, as well as a reference to the license and copyright information for each component.
"""

#
# CLI <-> config file <-> Python API mapping
#
# This is the single source of truth for every link between the two halves of the docs. From it
# the generator emits: a "See also" line under each command in cli.rst, a table of Python API
# equivalents for the global options in cli.rst, and the pointer above each section of the config
# file reference. The reverse links (API pages -> CLI) are hand-written `.. seealso::` blocks in
# docs/api/*.rst; `check_reverse_links` warns when one is missing for a command listed here.
#
# Every visible command and global option needs exactly one row (`check_concordance`); rows that
# have neither are only needed for config file sections and keys that have no CLI option.
#


@dataclass(frozen=True)
class Counterpart:
    """One thing a reader may look for, and where it lives on each surface.

    `thing` names the row for readers of this file (it is not emitted). Exactly one of `command`
    (a CLI command name), `option` (the Click parameter name of a global `scenedetect` option) or
    `cli` (free-form RST) locates the CLI side. `config` is a config file section or
    `[section] key`, and `api` is a list of RST snippets (Sphinx roles plus optional argument
    names); if `api` is empty, the thing is CLI only.
    """

    thing: str
    command: str | None = None
    option: str | None = None
    cli: str | None = None
    config: str | None = None
    api: tuple[str, ...] = ()


# Short aliases used to keep the table below readable.
_DET = "scenedetect.detectors"
_OUT = "scenedetect.output"
_SM = "scenedetect.scene_manager.SceneManager"
_BE = "scenedetect.backends"
_DETECT_SCENES = f":meth:`SceneManager.detect_scenes <{_SM}.detect_scenes>`"
_INIT_LOGGER = ":func:`~scenedetect.platform.init_logger`"

# Rows grouped by topic (the groups are for readability only).
CONCORDANCE: dict[str, list[Counterpart]] = {
    "Detectors": [
        Counterpart(
            "Fast cuts (adaptive)",
            command="detect-adaptive",
            config="[detect-adaptive]",
            api=(f":class:`~{_DET}.adaptive_detector.AdaptiveDetector`",),
        ),
        Counterpart(
            "Fast cuts (content)",
            command="detect-content",
            config="[detect-content]",
            api=(f":class:`~{_DET}.content_detector.ContentDetector`",),
        ),
        Counterpart(
            "Fast cuts (perceptual hash)",
            command="detect-hash",
            config="[detect-hash]",
            api=(f":class:`~{_DET}.hash_detector.HashDetector`",),
        ),
        Counterpart(
            "Fast cuts (histogram)",
            command="detect-hist",
            config="[detect-hist]",
            api=(f":class:`~{_DET}.histogram_detector.HistogramDetector`",),
        ),
        Counterpart(
            "Fades in/out (threshold)",
            command="detect-threshold",
            config="[detect-threshold]",
            api=(f":class:`~{_DET}.threshold_detector.ThresholdDetector`",),
        ),
        Counterpart(
            "Default detector",
            cli="Used if no ``detect-*`` command is given",
            config="[global] default-detector",
        ),
        Counterpart(
            "Minimum scene length",
            option="min_scene_len",
            config="[global] min-scene-len",
            api=(":ref:`Detector <scenedetect-detectors>` argument ``min_scene_len``",),
        ),
        Counterpart(
            "Drop short scenes",
            option="drop_short_scenes",
            config="[global] drop-short-scenes",
        ),
        Counterpart(
            "Merge short last scene",
            option="merge_last_scene",
            config="[global] merge-last-scene",
        ),
    ],
    "Output": [
        Counterpart(
            "Scene list (CSV)",
            command="list-scenes",
            config="[list-scenes]",
            api=(f":func:`~{_OUT}.write_scene_list`",),
        ),
        Counterpart(
            "Scene list (HTML)",
            command="save-html",
            config="[save-html]",
            api=(f":func:`~{_OUT}.write_scene_list_html`",),
        ),
        Counterpart(
            "Edit decision list (EDL)",
            command="save-edl",
            config="[save-edl]",
            api=(f":func:`~{_OUT}.write_scene_list_edl`",),
        ),
        Counterpart(
            "Final Cut Pro XML",
            command="save-fcp",
            config="[save-fcp]",
            api=(
                f":func:`~{_OUT}.write_scene_list_fcpx`",
                f":func:`~{_OUT}.write_scene_list_fcp7`",
            ),
        ),
        Counterpart(
            "OpenTimelineIO",
            command="save-otio",
            config="[save-otio]",
            api=(f":func:`~{_OUT}.write_scene_list_otio`",),
        ),
        Counterpart(
            "Images from each scene",
            command="save-images",
            config="[save-images]",
            api=(f":func:`~{_OUT}.save_images`",),
        ),
        Counterpart(
            "Split video into scenes",
            command="split-video",
            config="[split-video]",
            api=(f":func:`~{_OUT}.split_video_ffmpeg`", f":func:`~{_OUT}.split_video_mkvmerge`"),
        ),
        Counterpart(
            "Expand scenes to cover the whole video",
            cli=":option:`--expand <scenedetect split-video --expand>`",
            config="[split-video] expand",
            api=(":func:`~scenedetect.scene_manager.expand_scenes_to_bounds`",),
        ),
        Counterpart(
            "Output directory",
            option="output",
            config="[global] output",
            api=(
                "``output_dir`` argument of :func:`~scenedetect.output.save_images` and "
                ":func:`~scenedetect.output.split_video_ffmpeg`; output path argument of each "
                "``write_scene_list*`` function",
            ),
        ),
        Counterpart(
            "Keyframes for x264/x265 (QP file)",
            command="save-qp",
            config="[save-qp]",
        ),
        Counterpart(
            "Keyframes for Aegisub",
            command="save-keyframes",
            config="[save-keyframes]",
        ),
        Counterpart(
            "Load a scene list (CSV)",
            command="load-scenes",
            config="[load-scenes]",
        ),
    ],
    "Input and Processing": [
        Counterpart(
            "Input video",
            option="input",
            api=(":func:`~scenedetect.open_video`", ":func:`~scenedetect.detect`"),
        ),
        Counterpart(
            "Start, end, or duration",
            command="time",
            api=(
                ":func:`~scenedetect.detect` (``start_time``, ``end_time``)",
                f"{_DETECT_SCENES} (``duration``, ``end_time``)",
                ":meth:`VideoStream.seek <scenedetect.video_stream.VideoStream.seek>`",
            ),
        ),
        Counterpart(
            "Override frame rate",
            option="frame_rate",
            api=(":func:`~scenedetect.open_video` (``frame_rate``)",),
        ),
        Counterpart(
            "Crop",
            option="crop",
            config="[global] crop",
            api=(f":attr:`SceneManager.crop <{_SM}.crop>`",),
        ),
        Counterpart(
            "Downscale",
            option="downscale",
            config="[global] downscale",
            api=(
                f":attr:`SceneManager.downscale <{_SM}.downscale>`",
                f":attr:`SceneManager.auto_downscale <{_SM}.auto_downscale>`",
            ),
        ),
        Counterpart(
            "Downscale method",
            cli="*config file only*",
            config="[global] downscale-method",
            api=(f":attr:`SceneManager.interpolation <{_SM}.interpolation>`",),
        ),
        Counterpart(
            "Skip frames",
            option="frame_skip",
            config="[global] frame-skip",
            api=(f"{_DETECT_SCENES} (``frame_skip``)",),
        ),
        Counterpart(
            "Per-frame metrics (stats file)",
            option="stats",
            api=(
                ":class:`~scenedetect.stats_manager.StatsManager`",
                ":func:`~scenedetect.detect` (``stats_file_path``)",
            ),
        ),
        Counterpart(
            "Config file path",
            option="config",
        ),
    ],
    "Video Backends": [
        Counterpart(
            "Choose a backend",
            option="backend",
            config="[global] backend",
            api=(
                ":func:`~scenedetect.open_video` (``backend``)",
                f":data:`~{_BE}.AVAILABLE_BACKENDS`",
            ),
        ),
        Counterpart(
            "OpenCV",
            cli=":ref:`-b opencv <cli-backend-opencv>`",
            config="[backend-opencv]",
            api=(f":class:`~{_BE}.opencv.VideoStreamCv2`",),
        ),
        Counterpart(
            "PyAV",
            cli=":ref:`-b pyav <cli-backend-pyav>`",
            config="[backend-pyav]",
            api=(f":class:`~{_BE}.pyav.VideoStreamAv`",),
        ),
    ],
    "Logging": [
        Counterpart(
            "Verbosity",
            option="verbosity",
            config="[global] verbosity",
            api=(f"{_INIT_LOGGER} (``log_level``)",),
        ),
        Counterpart(
            "Log file",
            option="logfile",
            api=(f"{_INIT_LOGGER} (``log_file``)",),
        ),
        Counterpart(
            "Quiet mode",
            option="quiet",
            config="[global] verbosity",
            api=(f"{_INIT_LOGGER} (``show_stdout``)",),
        ),
    ],
}

CLI_ONLY = "*CLI only*"
NO_API = "*no Python API equivalent*"
API_ONLY = "*Python API only*"

CLI_INDEX_PATH = "docs/cli_index.inc"

ROOT_SEEALSO = (
    "\n.. seealso:: Config file: :ref:`Configuration File <scenedetect_cli-config_file>` | "
    "Python API: :doc:`api`\n\n"
)

#
# Config file reference
#
# docs/cli/config_sections.inc has one section per `CONFIG_MAP` section: a table of its keys
# (default and CLI option) followed by that section of the shipped template, scenedetect.cfg.
# `check_template` fails the run when the template and `CONFIG_MAP` list different keys.
#

TEMPLATE_PATH = "scenedetect.cfg"
CONFIG_SECTIONS_PATH = "docs/cli/config_sections.inc"

# Config keys that are set by CLI options with a different name (default: `--<key>`).
CONFIG_KEY_OPTIONS: dict[tuple[str, str], tuple[str, ...]] = {
    ("global", "verbosity"): ("--verbosity", "--quiet"),
    ("save-images", "format"): ("--jpeg", "--png", "--webp"),
    ("save-otio", "audio"): ("--audio", "--no-audio"),
}

# Defaults shown as RST instead of the `CONFIG_MAP` value, where that value is a placeholder or
# is not what a user can write (`auto` is how `-1` is displayed, not an accepted value).
CONFIG_DEFAULT_DISPLAY: dict[tuple[str, str], str] = {
    ("global", "downscale"): "``0`` (auto)",
    ("detect-adaptive", "kernel-size"): "``-1`` (auto)",
    ("detect-content", "kernel-size"): "``-1`` (auto)",
    ("save-images", "interval"): "*none*",
    ("save-images", "quality"): "``95`` (jpeg), ``100`` (webp)",
}


#
# Detector option tables
#
# One table per `detect-*` command, mapping each CLI option to its config file key and the
# detector constructor parameter it sets, with both defaults. A CLI option sets the parameter of
# the same name (`--min-content-val` -> `min_content_val`) unless listed in `renames`. Every
# constructor parameter must be set by a CLI option or listed in `api_only`. The CLI default is
# the option's `CONFIG_MAP` entry, the Python default comes from the constructor signature.
#


@dataclass(frozen=True)
class DetectorOptions:
    """How the options of one `detect-*` command map onto its detector's constructor.

    `renames` maps a long CLI option (e.g. `--frame-window`) to a constructor parameter with a
    different name. `api_only` maps each constructor parameter that has no CLI option to an extra
    note for its row (may be empty)."""

    detector: type
    renames: dict[str, str] = field(default_factory=dict)
    api_only: dict[str, str] = field(default_factory=dict)


DETECTOR_OPTIONS: dict[str, DetectorOptions] = {
    "detect-adaptive": DetectorOptions(
        AdaptiveDetector,
        renames={"--threshold": "adaptive_threshold", "--frame-window": "window_width"},
    ),
    "detect-content": DetectorOptions(ContentDetector),
    "detect-hash": DetectorOptions(HashDetector),
    "detect-hist": DetectorOptions(HistogramDetector),
    "detect-threshold": DetectorOptions(
        ThresholdDetector,
        renames={"--add-last-scene": "add_final_scene"},
        api_only={"method": "", "block_size": "Deprecated, unused."},
    ),
}

# Config keys whose per-detector default defers to the same key in `[global]`.
GLOBAL_DEFAULT_KEYS = ("min-scene-len",)

DETECTOR_OPTIONS_DIR = "docs/api/detector_options"


def global_options(ctx: click.Context) -> dict[str, click.Parameter]:
    return {param.name: param for param in ctx.command.params if isinstance(param, click.Option)}


def counterpart_entries() -> ty.Iterator[Counterpart]:
    for entries in CONCORDANCE.values():
        yield from entries


def counterpart_for(command: str | None = None, option: str | None = None) -> Counterpart | None:
    for entry in counterpart_entries():
        if (command and entry.command == command) or (option and entry.option == option):
            return entry
    return None


def option_flags(opt: click.Parameter, program: str = "scenedetect") -> tuple[str, str]:
    """Returns (display, target) for an option, e.g. ("-i/--input", "scenedetect -i")."""
    short = [o for o in opt.opts if not o.startswith("--")]
    long = [o for o in opt.opts if o.startswith("--")]
    return "/".join(short[:1] + long[:1]), f"{program} {(short or long)[0]}"


def format_config(config: str | None) -> str:
    """Link a `[section]` or `[section] key` to that section of the config file reference."""
    if config is None or not config.startswith("["):
        return config or ""
    section = config[1 : config.index("]")]
    return f":ref:`{config} <config-{section}>`"


def format_api(entry: Counterpart) -> str:
    return ", ".join(entry.api) if entry.api else CLI_ONLY


def format_cli(entry: Counterpart, options: dict[str, click.Parameter]) -> str:
    if entry.command:
        return f":ref:`{entry.command} <command-{entry.command}>`"
    if entry.option:
        display, target = option_flags(options[entry.option])
        return f":option:`{display} <{target}>`"
    return entry.cli or API_ONLY


def table_row(first: str, *rest: str) -> str:
    """One `list-table` row; empty cells get no trailing whitespace."""
    return f"   * - {first}\n" + "".join(f"     - {cell}".rstrip() + "\n" for cell in rest)


def generate_seealso(entry: Counterpart) -> StrGenerator:
    """One-line pointer from a CLI command to its Python API and config file counterparts."""
    api = format_api(entry) if entry.api else NO_API
    if entry.command in DETECTOR_OPTIONS:
        api += f" (:ref:`option table <options-{entry.command}>`)"
    parts = [f"Python API: {api}"]
    if entry.config:
        parts.append(f"Config file: {format_config(entry.config)}")
    yield f"\n.. seealso:: {' | '.join(parts)}\n\n"


def generate_global_option_table(options: dict[str, click.Parameter]) -> StrGenerator:
    yield "\n.. rubric:: Python API Equivalents\n\n"
    yield "Global options, their config file keys, and their Python API counterparts.\n\n"
    yield ".. list-table::\n   :header-rows: 1\n   :widths: 20 25 55\n\n"
    yield table_row("Option", "Config file", "Python API")
    for name in options:
        entry = counterpart_for(option=name)
        assert entry is not None
        yield table_row(format_cli(entry, options), format_config(entry.config), format_api(entry))
    yield "\n"


def check_concordance(commands: list[str], options: dict[str, click.Parameter]):
    """Every visible command and global option must have exactly one row in CONCORDANCE."""
    problems = []
    for kind, mapped, expected in (
        (
            "command",
            [e.command for e in counterpart_entries() if e.command],
            [c for c in commands if c not in INFO_COMMANDS],
        ),
        ("option", [e.option for e in counterpart_entries() if e.option], list(options)),
    ):
        for name in sorted(set(expected) - set(mapped)):
            problems.append(f"{kind} {name!r} has no CONCORDANCE row: add a Counterpart(...)")
        for name in sorted(set(mapped) - set(expected)):
            problems.append(f"{kind} {name!r} is in CONCORDANCE but not in the CLI: remove it")
        for name in sorted(n for n in set(mapped) if mapped.count(n) > 1):
            problems.append(f"{kind} {name!r} has more than one CONCORDANCE row")
    if problems:
        raise SystemExit("generate_cli_docs.py: " + "; ".join(problems))


def check_reverse_links():
    """Warn if an API page lacks the hand-written link back to a command that has an API."""
    api_rst = ""
    for root, _, files in os.walk("docs/api"):
        for name in files:
            if name.endswith(".rst"):
                with open(os.path.join(root, name), encoding="utf-8") as f:
                    api_rst += f.read()
    for entry in counterpart_entries():
        if entry.command and entry.api and f"<command-{entry.command}>" not in api_rst:
            print(f"WARNING: no link to command-{entry.command} in docs/api/*.rst", file=sys.stderr)


def patch_help(s: str, commands: list[str]) -> str:
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

        def add_link(_match: re.Match, command: str = command) -> str:
            return f":ref:`{command} <command-{command}>`"

        s = re.sub(f"``{command}``(?!\\n)", add_link, s)
    return s


def generate_title(s: str, level: int = 0, len: int = 72) -> StrGenerator:
    yield "\n"
    if level == 0:
        yield TITLE_LEVELS[level] * len + "\n"
    yield s + "\n"
    yield TITLE_LEVELS[level] * len + "\n\n"


@dataclass
class ReplaceWithReference:
    range: tuple[int, int]
    ref: str
    ref_type: str


def transform_backquotes(s: str) -> str:
    return s.replace("``", "`").replace("`", "``")


def add_backquotes(match: re.Match) -> str:
    return f"``{match.string[match.start() : match.end()]}``"


def add_backquotes_with_refs(refs: set[str]) -> ty.Callable[[str], str]:
    """Returns a transformation function that backquotes command examples, adding backquotes and
    references to any found options."""

    def _add_backquotes(s: re.Match) -> str:
        to_add: str = s.string[s.start() : s.end()]
        flag = re.search(r"-+[\w-]+[^\.\=\s\/]*", to_add)
        if flag is not None and flag.string[flag.start() : flag.end()] in refs:
            # add cross reference
            cross_ref = flag.string[flag.start() : flag.end()]
            option = s.string[s.start() : s.end()]
            return f":option:`{option} <{cross_ref}>`"
        else:
            return add_backquotes(s)

    return _add_backquotes


def extract_default_value(s: str) -> tuple[str, str | None]:
    """Split the `[default: ...]` suffix that `get_help_string` adds off a help string."""
    default = re.search(r"\[default: .*\]", s)
    if default is not None:
        span = default.span()
        assert span[1] == len(s)
        s, default = s[: span[0]].strip(), s[span[0] : span[1]][len("[default: ") : -1]
    return (s, default)


def config_section_for(command: click.Command) -> str:
    """Config file section that holds the options of `command` (`[global]` for `scenedetect`)."""
    if command.name in CONFIG_MAP:
        return command.name
    if command.name == scenedetect.name:
        return "global"
    raise SystemExit(f"generate_cli_docs.py: command {command.name!r} has no config file section")


def option_key(opt: click.Option) -> str | None:
    """Config file key of an option: its long name without the leading dashes."""
    long = next((o for o in opt.opts if o.startswith("--")), None)
    return long[2:] if long is not None else None


def option_default(command: click.Command, opt: click.Option, suffix: str) -> str:
    """The `Default:` text of an option, from `CONFIG_MAP` (so cli.rst, the config file reference
    and the detector option tables all show the same value). `suffix` is what `--help` prints;
    the run fails if it disagrees with `CONFIG_MAP`."""
    section, key = config_section_for(command), option_key(opt)
    where = f"generate_cli_docs.py: {section} {opt.opts}"
    if key is None or key not in CONFIG_MAP[section]:
        raise SystemExit(f"{where}: has a [default: ...] help suffix but no config key")
    if (section, key) in CONFIG_DEFAULT_DISPLAY:
        return CONFIG_DEFAULT_DISPLAY[(section, key)]
    value = CONFIG_MAP[section][key]
    if suffix != default_to_str(value):
        raise SystemExit(
            f"{where}: --help says [default: {suffix}] but CONFIG_MAP[{section!r}][{key!r}] is "
            f"{default_to_str(value)!r}; add a CONFIG_DEFAULT_DISPLAY entry if this is intended"
        )
    return format_cli_default(value, shell=True)


def transform_add_option_refs(s: str, refs: list[str]) -> str:
    transform = add_backquotes_with_refs(refs)
    # TODO: Match prefix of `global option` and add ref to parent `scenedetect` command option.
    # Replace patch to complete this.
    #  -c/--command
    s = re.sub(r"-\w/--\w[\w-]*", transform, s)
    #  --arg=value, --arg=1.2.3, --arg=1,2,3
    s = re.sub(r'-+[\w-]+=[^"\s\)]+(?<![\.\,])', transform, s)
    # --args=" command with spaces"
    s = re.sub(r'--[\w-]+[=]+".*?"', transform, s)
    return s


def format_option(command: click.Command, opt: click.Option, flags: list[str]) -> StrGenerator:
    if isinstance(opt, click.Argument):
        yield f"\n.. option:: {opt.name}\n"
        return
    yield "\n.. option:: {}\n".format(
        ", ".join(
            arg if opt.metavar is None else f"{arg} {opt.metavar}"
            for arg in sorted(opt.opts, reverse=True)
        )
    )

    help = (
        OPTION_HELP_OVERRIDES[command.name][opt.name]
        if command.name in OPTION_HELP_OVERRIDES and opt.name in OPTION_HELP_OVERRIDES[command.name]
        else opt.help.strip()
    )

    # TODO: Make metavars link to the option as well.
    help, suffix = extract_default_value(help)
    help = transform_add_option_refs(help, flags)

    yield f"\n  {help}\n"
    if suffix is not None:
        yield f"\n  Default: {option_default(command, opt, suffix)}\n"


def generate_command_help(
    ctx: click.Context, command: click.Command, parent_name: str | None = None
) -> StrGenerator:
    # TODO: Add references to long options. Requires splitting out examples.
    # TODO: Add references to subcommands. Need to add actual refs, since programs can't be ref'd.
    # TODO: Handle dollar signs in examples by having both escaped and unescaped versions
    yield f"\n.. _command-{command.name}:\n"
    yield "\n.. program:: %s\n\n" % (
        command.name if parent_name is None else f"{parent_name} {command.name}"
    )
    if parent_name:
        yield from generate_title(f"``{command.name}``", 2)
        entry = counterpart_for(command=command.name)
        if entry is not None:
            yield from generate_seealso(entry)
    else:
        yield ROOT_SEEALSO

    replacements = [
        opt
        for opts in [param.opts for param in command.params if hasattr(param, "opts")]
        for opt in opts
    ]

    help = command.help
    help = help.replace(
        "Examples:\n",
        ("\n.. _cli-usage:\n" if not parent_name else "")
        + "".join(
            generate_title("Usage" if not parent_name else "Examples", 1 if not parent_name else 3)
        ),
    )
    help = help.replace("\b\n", "")
    help = help.format(scenedetect="scenedetect", scenedetect_with_video="scenedetect -i video.mp4")
    help = transform_backquotes(help)
    help = transform_add_option_refs(help, replacements)

    for line in help.strip().splitlines():
        if line.startswith(INDENT):
            indent = line.count(INDENT)
            line = line.strip()
            yield f"{indent * INDENT}``{line}``\n" if line else "\n"
        else:
            yield f"{line}\n"

    if command.params:
        yield "\n"
        if not parent_name:
            yield "\n.. _cli-options:\n"
        yield from generate_title("Options", 1 if not parent_name else 3)
        for param in command.params:
            yield from format_option(command, param, replacements)
    if not parent_name:
        yield from generate_global_option_table(global_options(ctx))
    yield "\n"


def generate_subcommands(ctx: click.Context, commands: list[str]) -> StrGenerator:
    processed = set()

    for info_command in INFO_COMMANDS:
        assert info_command in commands
        processed.add(info_command)

    yield "\n.. _cli-detectors:\n"
    yield from generate_title("Detectors", 1)
    detectors = [command for command in commands if command.startswith("detect-")]
    for detector in detectors:
        yield from generate_command_help(ctx, ctx.command.get_command(ctx, detector), ctx.info_name)
        processed.add(detector)

    yield "\n.. _cli-commands:\n"
    yield from generate_title("Commands", 1)
    output_commands = [
        command
        for command in commands
        if (not command.startswith("detect-") and command not in INFO_COMMANDS)
    ]
    for command in output_commands:
        yield from generate_command_help(ctx, ctx.command.get_command(ctx, command), ctx.info_name)
        processed.add(command)
    yield INFO_COMMAND_OVERRIDE

    assert set(commands) == processed


def create_help() -> tuple[str, list[str]]:
    ctx = click.Context(scenedetect, info_name=scenedetect.name)

    commands: list[str] = ctx.command.list_commands(ctx)
    commands = list(
        filter(lambda command: not ctx.command.get_command(ctx, command).hidden, commands)
    )
    # ctx.to_info_dict lacks metavar so we have to use the context directly.
    actions = [
        generate_title("``scenedetect`` Command", level=0),
        generate_command_help(ctx, ctx.command),
        generate_subcommands(ctx, commands),
    ]
    lines = []
    for action in actions:
        lines.extend(action)
    return "".join(lines), commands


def generate_cli_index(commands: list[str]) -> str:
    """Nested link list of the CLI reference, included by the index page."""
    detectors = [c for c in commands if c.startswith("detect-")]
    others = [c for c in commands if not c.startswith("detect-") and c not in INFO_COMMANDS]
    return "".join(
        [
            ".. NOTE: This file is auto-generated by docs/generate_cli_docs.py and should not be"
            " modified.\n\n",
            "- :doc:`scenedetect Command </cli>`\n\n",
            "  - :ref:`Usage <cli-usage>`\n",
            "  - :ref:`Options <cli-options>`\n",
            "  - :ref:`Detectors <cli-detectors>`: "
            + ", ".join(f":ref:`{c} <command-{c}>`" for c in detectors)
            + "\n",
            "  - :ref:`Commands <cli-commands>`: "
            + ", ".join(f":ref:`{c} <command-{c}>`" for c in others)
            + "\n\n",
            "- :doc:`cli/config_file`\n",
            "- :doc:`cli/backends`\n",
        ]
    )


def format_api_default(value: ty.Any) -> str:
    """A constructor default as a Python literal."""
    if isinstance(value, Enum):
        value = f"{type(value).__name__}.{value.name}"  # `Method.FLOOR`, which fits the table
    elif isinstance(value, tuple):
        value = repr(tuple(value))
    else:
        value = repr(value)
    return f"``{value}``"


def format_cli_default(value: ty.Any, shell: bool = False) -> str:
    """A `CONFIG_MAP` default as it is written in the config file or, with `shell`, on the
    command line (values with spaces are quoted), as RST. Unset values are shown as *none*."""
    text = default_to_str(value)
    if text in ("None", "(none)"):
        return "*none*"
    text = text.replace("\n", "\\n").replace("\t", "\\t")
    if shell and " " in text and '"' not in text and "," not in text:
        text = f'"{text}"'
    return f"``{text}``"


def generate_detector_options(ctx: click.Context, command_name: str) -> str:
    """Option table for one `detect-*` command, included by docs/api/detectors.rst."""
    spec = DETECTOR_OPTIONS[command_name]
    command = ctx.command.get_command(ctx, command_name)
    config = CONFIG_MAP[command_name]
    signature = inspect.signature(spec.detector.__init__)
    params = {name: p for name, p in signature.parameters.items() if name != "self"}
    detector = spec.detector.__name__
    where = f"generate_cli_docs.py: {command_name} -> {detector}"
    rows = []
    for opt in command.params:
        if not isinstance(opt, click.Option):
            continue
        long = next((o for o in opt.opts if o.startswith("--")), None)
        if long is None:
            raise SystemExit(f"{where}: option {opt.opts} has no long name")
        key = long[2:]
        same_name = key.replace("-", "_")
        param = spec.renames.get(long, same_name)
        if param not in params:
            raise SystemExit(
                f"{where}: CLI option {long} has no constructor parameter {param!r}; add an "
                f"entry to DETECTOR_OPTIONS[{command_name!r}].renames"
            )
        if param in spec.api_only:
            raise SystemExit(f"{where}: {param!r} is set by {long} but listed in api_only")
        if key not in config:
            raise SystemExit(f"{where}: CLI option {long} has no config key [{command_name}] {key}")
        cli_default, via_global = config[key], ""
        if key in GLOBAL_DEFAULT_KEYS:
            cli_default = CONFIG_MAP["global"][key]
            display, target = option_flags(global_options(ctx)[same_name])
            via_global = f" (global :option:`{display} <{target}>`)"
        api_default = params[param].default
        if api_default is inspect.Parameter.empty:
            raise SystemExit(f"{where}: constructor parameter {param!r} has no default")
        cli_value = cli_default.value if isinstance(cli_default, ValidatedValue) else cli_default
        notes = ["**RENAMED**"] if param != same_name else []
        # Flags are written `yes`/`no` only in the config file; everything else is typed the
        # same way on the command line.
        label = "config" if isinstance(cli_value, bool) else "CLI"
        override = CONFIG_DEFAULT_DISPLAY.get((command_name, key))
        if cli_value == api_default and not via_global:
            # Same value; show the CLI spelling too when it differs (`None` vs `-1`), but not
            # for `12` vs `12.0`.
            api, cli = format_api_default(api_default), override or format_cli_default(cli_default)
            numbers = all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in (cli_value, api_default)
            )
            if api == cli or numbers:
                default = api
            elif override:
                default = f"{api}; {label} {cli}"
            else:
                default = f"{api} ({label} {cli})"
        else:
            notes.append("**DIFFERS**")
            unit = (
                " frames"
                if isinstance(cli_default, TimecodeValue) and isinstance(api_default, int)
                else ""
            )
            default = (
                f"{label} {override or format_cli_default(cli_default)}{via_global}, "
                f"Python {format_api_default(api_default)}{unit}"
            )
        display, target = option_flags(opt, f"scenedetect {command_name}")
        rows.append(
            table_row(f":option:`{display} <{target}>`", f"``{param}``", default, " ".join(notes))
        )
        del params[param]
    for param, note in spec.api_only.items():
        if param not in params:
            raise SystemExit(f"{where}: api_only parameter {param!r} is not in the constructor")
        default = format_api_default(params.pop(param).default)
        rows.append(table_row("*none*", f"``{param}``", default, f"**API only** {note}"))
    if params:
        raise SystemExit(
            f"{where}: constructor parameters {sorted(params)} are not set by any CLI option; "
            f"add a rename or list them in DETECTOR_OPTIONS[{command_name!r}].api_only"
        )
    # The table sits in a container so that it can scroll sideways on narrow screens.
    table = ".. list-table::\n   :class: detector-options\n   :header-rows: 1\n\n" + "".join(
        [table_row("CLI option", "Python parameter", "Default", "Notes"), *rows]
    )
    return "".join(
        [
            ".. NOTE: This file is auto-generated by docs/generate_cli_docs.py and should not be"
            " modified.\n\n",
            f".. _options-{command_name}:\n\n",
            f"Options of :ref:`{command_name} <command-{command_name}>` and the "
            f":class:`~{spec.detector.__module__}.{detector}` parameters they set. Each option "
            f"can also be set in the :ref:`[{command_name}] <config-{command_name}>` config file "
            "section under its long name (``--threshold`` is ``threshold``):\n\n",
            ".. container:: table-scroll\n\n",
            "".join(
                f"   {line}" if line.strip() else line for line in table.splitlines(keepends=True)
            ),
        ]
    )


def write_detector_options(ctx: click.Context, commands: list[str]):
    detectors = [c for c in commands if c.startswith("detect-")]
    if sorted(detectors) != sorted(DETECTOR_OPTIONS):
        raise SystemExit(
            f"generate_cli_docs.py: DETECTOR_OPTIONS {sorted(DETECTOR_OPTIONS)} does not match "
            f"the detect-* commands {sorted(detectors)}"
        )
    os.makedirs(DETECTOR_OPTIONS_DIR, exist_ok=True)
    for command in detectors:
        text = generate_detector_options(ctx, command)
        assert text.isascii(), command
        with open(os.path.join(DETECTOR_OPTIONS_DIR, f"{command}.inc"), "wb") as f:
            f.write(text.encode())


@dataclass
class TemplateSection:
    """One `[section]` of scenedetect.cfg: its keys in order, its text (header line through the
    last key or comment, without the banner comments that separate groups of sections), and any
    lines that look like a commented-out key missing its `=`."""

    name: str
    keys: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        lines = list(self.lines)
        while lines and (not lines[-1].strip() or _TEMPLATE_BANNER.match(lines[-1])):
            lines.pop()
        while len(lines) > 1 and not lines[1].strip():
            del lines[1]  # blank line after the header
        return "\n".join(lines)


_TEMPLATE_HEADER = re.compile(r"^\[([\w-]+)\]\s*$")
_TEMPLATE_KEY = re.compile(r"^#([\w-]+)\s*=")
_TEMPLATE_BAD_KEY = re.compile(r"^#([\w-]+)\s+\S")
_TEMPLATE_BANNER = re.compile(r"^#(\s*[A-Z][A-Z ]*)?$")


def parse_template(path: str) -> dict[str, TemplateSection]:
    """The sections of the config file template, in file order."""
    sections: dict[str, TemplateSection] = {}
    current: TemplateSection | None = None
    with open(path, encoding="utf-8") as f:
        for line in f.read().splitlines():
            header = _TEMPLATE_HEADER.match(line)
            if header is not None:
                if header.group(1) in sections:
                    raise SystemExit(f"generate_cli_docs.py: [{header.group(1)}] twice in {path}")
                current = sections[header.group(1)] = TemplateSection(header.group(1))
            if current is None:
                continue
            current.lines.append(line)
            key = _TEMPLATE_KEY.match(line)
            if key is not None:
                current.keys.append(key.group(1))
            elif _TEMPLATE_BAD_KEY.match(line):
                current.malformed.append(line)
    return sections


def check_template(sections: dict[str, TemplateSection]) -> None:
    """The template and `CONFIG_MAP` must list the same sections and keys (values are not
    compared: the template may show an example where the default is unset)."""
    problems = []
    for name in sorted(set(CONFIG_MAP) - set(sections)):
        problems.append(f"[{name}] is missing from {TEMPLATE_PATH}")
    for name in sorted(set(sections) - set(CONFIG_MAP)):
        problems.append(f"[{name}] in {TEMPLATE_PATH} is not in CONFIG_MAP")
    for name, section in sections.items():
        for line in section.malformed:
            problems.append(f"[{name}] line {line!r} in {TEMPLATE_PATH} is missing its '='")
        if name not in CONFIG_MAP:
            continue
        for key in sorted(set(CONFIG_MAP[name]) - set(section.keys)):
            problems.append(f"[{name}] {key} is missing from {TEMPLATE_PATH}")
        for key in sorted(set(section.keys) - set(CONFIG_MAP[name])):
            problems.append(f"[{name}] {key} in {TEMPLATE_PATH} is not in CONFIG_MAP")
        for key in sorted(k for k in set(section.keys) if section.keys.count(k) > 1):
            problems.append(f"[{name}] {key} appears more than once in {TEMPLATE_PATH}")
    for name, choices in CHOICE_MAP.items():
        for key in sorted(set(choices) - set(CONFIG_MAP.get(name, {}))):
            problems.append(f"CHOICE_MAP[{name!r}] key {key!r} is not in CONFIG_MAP")
    if problems:
        raise SystemExit("generate_cli_docs.py: " + "; ".join(problems))


def config_section_order(commands: list[str]) -> list[str]:
    """`[global]`, then the detectors and commands in CLI order, then the backends."""
    order = ["global"]
    order += [c for c in commands if c.startswith("detect-") and c in CONFIG_MAP]
    order += [c for c in commands if not c.startswith("detect-") and c in CONFIG_MAP]
    order += sorted(s for s in CONFIG_MAP if s not in order)
    return order


def config_key_cli(ctx: click.Context, section: str, key: str) -> str:
    """Link(s) to the CLI option(s) that set a config key, or a note if there is none."""
    command = ctx.command if section == "global" else ctx.command.get_command(ctx, section)
    program = "scenedetect" if section == "global" else f"scenedetect {section}"
    links = []
    if command is not None:
        for flag in CONFIG_KEY_OPTIONS.get((section, key), (f"--{key}",)):
            opt = next(
                (p for p in command.params if isinstance(p, click.Option) and flag in p.opts), None
            )
            if opt is not None:
                display, target = option_flags(opt, program)
                links.append(f":option:`{display} <{target}>`")
    if links:
        return ", ".join(links)
    entry = next((e for e in counterpart_entries() if e.config == f"[{section}] {key}"), None)
    return entry.cli if entry is not None and entry.cli else "*config file only*"


def config_default(section: str, key: str) -> str:
    if (section, key) in CONFIG_DEFAULT_DISPLAY:
        return CONFIG_DEFAULT_DISPLAY[(section, key)]
    if section != "global" and key in GLOBAL_DEFAULT_KEYS:
        return f":ref:`[global] {key} <config-global>`"
    return format_cli_default(CONFIG_MAP[section][key])


def config_section_pointer(section: str) -> str:
    """One sentence linking a config section to the command or backend it configures."""
    if section == "global":
        return (
            "Options of the :doc:`scenedetect </cli>` command; detectors and "
            "commands inherit ``min-scene-len`` and ``output`` from here."
        )
    entry = counterpart_for(command=section)
    if entry is None:
        entry = next((e for e in counterpart_entries() if e.config == f"[{section}]"), None)
    if entry is None:
        raise SystemExit(f"generate_cli_docs.py: no CONCORDANCE row for config section [{section}]")
    api = format_api(entry) if entry.api else ""
    if entry.command:
        if section in DETECTOR_OPTIONS:
            api += f", :ref:`option table <options-{section}>`"
        return f"Options of :ref:`{section} <command-{section}>`" + (
            f" (Python API: {api})." if api else "."
        )
    return (
        f"Settings of the {entry.cli} backend (Python API: {api}). These keys have no "
        "command-line option."
    )


def generate_config_section(ctx: click.Context, section: TemplateSection) -> str:
    rows = [
        table_row(
            f"``{key}``", config_default(section.name, key), config_key_cli(ctx, section.name, key)
        )
        for key in section.keys
    ]
    excerpt = "\n".join(INDENT + line if line else "" for line in section.text.splitlines())
    return "".join(
        [
            f"\n.. _config-{section.name}:\n",
            *generate_title(f"[{section.name}]", 3),
            config_section_pointer(section.name) + "\n\n",
            ".. list-table::\n   :class: config-keys\n   :header-rows: 1\n   :widths: 28 32 40\n\n",
            table_row("Key", "Default", "CLI option"),
            *rows,
            "\n.. code-block:: ini\n\n",
            excerpt + "\n",
        ]
    )


def write_config_sections(
    ctx: click.Context, commands: list[str], sections: dict[str, TemplateSection]
):
    text = (
        ".. NOTE: This file is auto-generated by docs/generate_cli_docs.py from CONFIG_MAP and "
        f"{TEMPLATE_PATH} and should not be modified.\n"
    )
    text += "".join(
        generate_config_section(ctx, sections[s]) for s in config_section_order(commands)
    )
    assert text.isascii()
    with open(CONFIG_SECTIONS_PATH, "wb") as f:
        f.write(text.encode())


def main():
    ctx = click.Context(scenedetect, info_name=scenedetect.name)
    options = global_options(ctx)
    visible = [
        c for c in ctx.command.list_commands(ctx) if not ctx.command.get_command(ctx, c).hidden
    ]
    check_concordance(visible, options)
    template = parse_template(TEMPLATE_PATH)
    check_template(template)
    help, commands = create_help()
    check_reverse_links()
    with open(CLI_INDEX_PATH, "wb") as f:
        f.write(generate_cli_index(commands).encode())
    write_detector_options(ctx, commands)
    write_config_sections(ctx, commands, template)
    help = patch_help(help, commands)
    help = (
        ".. NOTE: This file is auto-generated by docs/generate_cli_docs.py and should not be modified.\n"
        + help
    )
    with open("docs/cli.rst", "wb") as f:
        f.write(help.encode())


if __name__ == "__main__":
    main()
