#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Implementation of the PySceneDetect application itself (the `scenedetect` command). The main CLI
entry-point function is :func:scenedetect_cli, which is a chained command group.

Commands are first parsed into a context (`CliContext`), which is then passed to a controller which
performs scene detection and other required actions (`run_scenedetect`).
"""

# Some parts of this file need word wrap to be displayed.

import inspect
import logging
import os
import os.path
import typing as ty
from copy import deepcopy

import click

import scenedetect
import scenedetect._cli.commands as cli_commands
from scenedetect._cli.config import (
    CHOICE_MAP,
    CONFIG_FILE_PATH,
    CONFIG_MAP,
    DEFAULT_JPG_QUALITY,
    DEFAULT_WEBP_QUALITY,
)
from scenedetect._cli.context import USER_CONFIG, CliContext, check_split_video_requirements
from scenedetect.backends import AVAILABLE_BACKENDS
from scenedetect.detectors import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
)
from scenedetect.platform import get_cv2_imwrite_params, get_system_version_info

PROGRAM_VERSION = scenedetect.__version__
"""Used to avoid name conflict with named `scenedetect` command below."""

logger = logging.getLogger("pyscenedetect")

LINE_SEPARATOR = "-" * 72

# About & copyright message string shown for the 'about' CLI command (scenedetect about).
ABOUT_STRING = """
Site: http://scenedetect.com/
Docs: https://www.scenedetect.com/docs/
Code: https://github.com/Breakthrough/PySceneDetect/

Copyright (C) 2014-2024 Brandon Castellano. All rights reserved.

PySceneDetect is released under the BSD 3-Clause license. See the
LICENSE file or visit [ https://www.scenedetect.com/copyright/ ].
This software uses the following third-party components:

  > NumPy [Copyright (C) 2018, Numpy Developers]
  > OpenCV [Copyright (C) 2018, OpenCV Team]
  > click [Copyright (C) 2018, Armin Ronacher]
  > simpletable [Copyright (C) 2014 Matheus Vieira Portela]
  > PyAV [Copyright (C) 2017, Mike Boers and others]
  > MoviePy [Copyright (C) 2015 Zulko]

This software may also invoke the following third-party executables:

  > FFmpeg [Copyright (C) 2018, Fabrice Bellard]
  > mkvmerge [Copyright (C) 2005-2016, Matroska]

Certain distributions of PySceneDetect may include ffmpeg. See
the included LICENSE-FFMPEG or visit [ https://ffmpeg.org ].

Binary distributions of PySceneDetect include a compiled Python
distribution. See the included LICENSE-PYTHON file, or visit
[ https://docs.python.org/3/license.html ].

THE SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY, EXPRESS OR IMPLIED.
"""


class Command(click.Command):
    """Custom formatting for commands."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Writes the help into the formatter if it exists."""
        if ctx.parent:
            formatter.write(click.style("`%s` Command" % ctx.command.name, fg="cyan"))
            formatter.write_paragraph()
            formatter.write(click.style(LINE_SEPARATOR, fg="cyan"))
            formatter.write_paragraph()
        else:
            formatter.write(click.style(LINE_SEPARATOR, fg="yellow"))
            formatter.write_paragraph()
            formatter.write(click.style("PySceneDetect Help", fg="yellow"))
            formatter.write_paragraph()
            formatter.write(click.style(LINE_SEPARATOR, fg="yellow"))
            formatter.write_paragraph()

        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_help_text(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Writes the help text to the formatter if it exists."""
        if self.help:
            base_command = ctx.parent.info_name if ctx.parent is not None else ctx.info_name
            formatted_help = self.help.format(
                scenedetect=base_command, scenedetect_with_video="%s -i video.mp4" % base_command
            )
            text = inspect.cleandoc(formatted_help).partition("\f")[0]
            formatter.write_paragraph()
            formatter.write_text(text)

    def format_epilog(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Writes the epilog into the formatter if it exists."""
        if self.epilog:
            epilog = inspect.cleandoc(self.epilog)
            formatter.write_paragraph()
            formatter.write_text(epilog)


class CommandGroup(Command, click.Group):
    """Custom formatting for command groups."""

    pass


def print_command_help(ctx: click.Context, command: click.Command):
    """Print help/usage for a given command. Modifies `ctx` in-place."""
    ctx.info_name = command.name
    ctx.command = command
    click.echo("")
    click.echo(command.get_help(ctx))


SCENEDETECT_COMMAND_HELP = """PySceneDetect is a scene cut/transition detection program. PySceneDetect takes an input video, runs detection on it, and uses the resulting scene information to generate output. The syntax for using PySceneDetect is:

    {scenedetect_with_video} [detector] [commands]

For [detector] use `detect-adaptive` or `detect-content` to find fast cuts, and `detect-threshold` for fades in/out. If [detector] is not specified, a default detector will be used.

Examples:

Split video wherever a new scene is detected:

    {scenedetect_with_video} split-video

Save scene list in CSV format with images at the start, middle, and end of each scene:

    {scenedetect_with_video} list-scenes save-images

Skip the first 10 seconds of the input video:

    {scenedetect_with_video} time --start 10s detect-content

Show summary of all options and commands:

    {scenedetect} --help

Global options (e.g. -i/--input, -c/--config) must be specified before any commands and their options. The order of commands is not strict, but each command must only be specified once."""


@click.group(
    cls=CommandGroup,
    chain=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
    invoke_without_command=True,
    epilog="""Type "scenedetect [command] --help" for command usage. See https://scenedetect.com/docs/ for online docs.""",
    help=SCENEDETECT_COMMAND_HELP,
)
# *NOTE*: Although input is required, we cannot mark it as `required=True`, otherwise we will reject
# commands of the form `scenedetect detect-content --help`.
@click.option(
    "--input",
    "-i",
    multiple=False,
    required=False,
    metavar="VIDEO",
    type=click.STRING,
    help="[REQUIRED] Input video file. Image sequences and URLs are supported.",
)
@click.option(
    "--output",
    "-o",
    multiple=False,
    required=False,
    metavar="DIR",
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=True),
    help="Output directory for created files. If unset, working directory will be used. May be overridden by command options.%s"
    % (USER_CONFIG.get_help_string("global", "output", show_default=False)),
)
@click.option(
    "--config",
    "-c",
    metavar="FILE",
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=False),
    help="Path to config file. If unset, tries to load config from %s" % (CONFIG_FILE_PATH),
)
@click.option(
    "--stats",
    "-s",
    metavar="CSV",
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False),
    help="Stats file (.csv) to write frame metrics. Existing files will be overwritten. Used for tuning detection parameters and data analysis.",
)
@click.option(
    "--framerate",
    "-f",
    metavar="FPS",
    type=click.FLOAT,
    default=None,
    help="Override framerate with value as frames/sec.",
)
@click.option(
    "--min-scene-len",
    "-m",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Minimum length of any scene. TIMECODE can be specified as number of frames (-m 10), time in seconds (-m 2.5), or timecode (-m 00:02:53.633).%s"
    % USER_CONFIG.get_help_string("global", "min-scene-len"),
)
@click.option(
    "--drop-short-scenes",
    is_flag=True,
    flag_value=True,
    default=None,
    help="Drop scenes shorter than -m/--min-scene-len, instead of combining with neighbors.%s"
    % (USER_CONFIG.get_help_string("global", "drop-short-scenes")),
)
@click.option(
    "--merge-last-scene",
    is_flag=True,
    flag_value=True,
    default=None,
    help="Merge last scene with previous if shorter than -m/--min-scene-len.%s"
    % (USER_CONFIG.get_help_string("global", "merge-last-scene")),
)
@click.option(
    "--backend",
    "-b",
    metavar="BACKEND",
    type=click.Choice(CHOICE_MAP["global"]["backend"]),
    default=None,
    help="Backend to use for video input. Backend options can be set using a config file (-c/--config). [available: %s]%s"
    % (", ".join(AVAILABLE_BACKENDS.keys()), USER_CONFIG.get_help_string("global", "backend")),
)
@click.option(
    "--crop",
    metavar="X0 Y0 X1 Y1",
    type=(int, int, int, int),
    default=None,
    help="Crop input video. Specified as two points representing top left and bottom right corner of crop region. 0 0 is top-left of the video frame. Bounds are inclusive (e.g. for a 100x100 video, the region covering the whole frame is 0 0 99 99).%s"
    % (USER_CONFIG.get_help_string("global", "crop", show_default=False)),
)
@click.option(
    "--downscale",
    "-d",
    metavar="N",
    type=click.INT,
    default=None,
    help="Integer factor to downscale video by before processing. If unset, value is selected based on resolution. Set -d 1 to disable downscaling.%s"
    % (USER_CONFIG.get_help_string("global", "downscale", show_default=False)),
)
@click.option(
    "--frame-skip",
    "-fs",
    metavar="N",
    type=click.INT,
    default=None,
    help="Skip N frames during processing. Reduces processing speed at expense of accuracy. -fs 1 skips every other frame processing 50%% of the video, -fs 2 processes 33%% of the video frames, -fs 3 processes 25%%, etc... %s"
    % USER_CONFIG.get_help_string("global", "frame-skip"),
)
@click.option(
    "--verbosity",
    "-v",
    metavar="LEVEL",
    type=click.Choice(CHOICE_MAP["global"]["verbosity"], False),
    default=None,
    help="Amount of information to show. LEVEL must be one of: %s. Overrides -q/--quiet.%s"
    % (
        ", ".join(CHOICE_MAP["global"]["verbosity"]),
        USER_CONFIG.get_help_string("global", "verbosity"),
    ),
)
@click.option(
    "--logfile",
    "-l",
    metavar="FILE",
    type=click.Path(exists=False, file_okay=True, writable=True, resolve_path=False),
    help="Save debug log to FILE. Appends to existing file if present.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    flag_value=True,
    help="Suppress output to terminal/stdout. Equivalent to setting --verbosity=none.",
)
@click.pass_context
def scenedetect(
    ctx: click.Context,
    input: ty.Optional[ty.AnyStr],
    output: ty.Optional[ty.AnyStr],
    stats: ty.Optional[ty.AnyStr],
    config: ty.Optional[ty.AnyStr],
    framerate: ty.Optional[float],
    min_scene_len: ty.Optional[str],
    drop_short_scenes: ty.Optional[bool],
    merge_last_scene: ty.Optional[bool],
    backend: ty.Optional[str],
    crop: ty.Optional[ty.Tuple[int, int, int, int]],
    downscale: ty.Optional[int],
    frame_skip: ty.Optional[int],
    verbosity: ty.Optional[str],
    logfile: ty.Optional[ty.AnyStr],
    quiet: bool,
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    ctx.handle_options(
        input_path=input,
        output=output,
        framerate=framerate,
        stats_file=stats,
        frame_skip=frame_skip,
        min_scene_len=min_scene_len,
        drop_short_scenes=drop_short_scenes,
        merge_last_scene=merge_last_scene,
        backend=backend,
        crop=crop,
        downscale=downscale,
        quiet=quiet,
        logfile=logfile,
        config=config,
        stats=stats,
        verbosity=verbosity,
    )


def add_hidden_alias(command: click.Command, alias: str):
    """Adds a copy of `command` that can be invoked under the name `alias`."""
    hidden_command = deepcopy(command)
    hidden_command.hidden = True
    scenedetect.add_command(hidden_command, alias)


@click.command("help", cls=Command)
@click.argument(
    "command_name",
    required=False,
    type=click.STRING,
)
@click.pass_context
def help_command(ctx: click.Context, command_name: str):
    """Print full help reference."""
    # TODO: Other commands still seem to run if this is specified.
    assert isinstance(ctx.parent.command, click.MultiCommand)
    parent_command = ctx.parent.command
    all_commands = set(parent_command.list_commands(ctx))
    if command_name is not None:
        if command_name not in all_commands:
            error_strs = [
                "unknown command. List of valid commands:",
                "  %s" % ", ".join(sorted(all_commands)),
            ]
            raise click.BadParameter("\n".join(error_strs), param_hint="command")
        click.echo("")
        print_command_help(ctx, parent_command.get_command(ctx, command_name))
    else:
        click.echo(ctx.parent.get_help())
        for command in sorted(all_commands):
            print_command_help(ctx, parent_command.get_command(ctx, command))
    ctx.exit()


@click.command("about", cls=Command, add_help_option=False)
@click.pass_context
def about_command(ctx: click.Context):
    """Print license/copyright info."""
    click.echo("")
    click.echo(click.style(LINE_SEPARATOR, fg="cyan"))
    click.echo(click.style(" About PySceneDetect %s" % PROGRAM_VERSION, fg="yellow"))
    click.echo(click.style(LINE_SEPARATOR, fg="cyan"))
    click.echo(ABOUT_STRING)
    ctx.exit()


@click.command("version", cls=Command, add_help_option=False)
@click.pass_context
def version_command(ctx: click.Context):
    """Print PySceneDetect version."""
    click.echo("")
    click.echo(get_system_version_info())
    ctx.exit()


TIME_COMMAND_HELP = """Set start/end/duration of input video.

Values can be specified as seconds (SSSS.nn), frames (NNNN), or timecode (HH:MM:SS.nnn). For example, to process only the first minute of a video:

    {scenedetect_with_video} time --end 00:01:00

    {scenedetect_with_video} time --duration 60.0

Note that --end and --duration are mutually exclusive (i.e. only one of the two can be set). Lastly, the following is an example using absolute frame numbers to process frames 0 through 1000:

    {scenedetect_with_video} time --start 0 --end 1000
"""


@click.command("time", cls=Command, help=TIME_COMMAND_HELP)
@click.option(
    "--start",
    "-s",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Time in video to start detection. TIMECODE can be specified as seconds (--start=100.0), frames (--start=100), or timecode (--start=00:01:40.000).",
)
@click.option(
    "--duration",
    "-d",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Maximum time in video to process. TIMECODE format is the same as other arguments. Mutually exclusive with -e/--end.",
)
@click.option(
    "--end",
    "-e",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Time in video to end detecting scenes. TIMECODE format is the same as other arguments. Mutually exclusive with -d/--duration",
)
@click.pass_context
def time_command(
    ctx: click.Context,
    start: ty.Optional[str],
    duration: ty.Optional[str],
    end: ty.Optional[str],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    if duration is not None and end is not None:
        raise click.BadParameter(
            "Only one of --duration/-d or --end/-e can be specified, not both.",
            param_hint="time",
        )
    logger.debug("Setting video time:\n    start: %s, duration: %s, end: %s", start, duration, end)
    # *NOTE*: The Python API uses 0-based frame indices, but the CLI uses 1-based indices to
    # match the default start number used by `ffmpeg` when saving frames as images. As such,
    # we must correct start time if set as frames. See the test_cli_time* tests for for details.
    ctx.start_time = ctx.parse_timecode(start, correct_pts=True)
    ctx.end_time = ctx.parse_timecode(end)
    ctx.duration = ctx.parse_timecode(duration)
    if ctx.start_time and ctx.end_time and (ctx.start_time + 1) > ctx.end_time:
        raise click.BadParameter("-e/--end time must be greater than -s/--start")


DETECT_CONTENT_HELP = """Find fast cuts using differences in HSL (filtered).

For each frame, a score from 0 to 255.0 is calculated which represents the difference in content between the current and previous frame (higher = more different). A cut is generated when a frame score exceeds -t/--threshold. Frame scores are saved under the "content_val" column in a statsfile.

Scores are calculated from several components which are also recorded in the statsfile:

  - *delta_hue*: Difference between pixel hue values of adjacent frames.

  - *delta_sat*: Difference between pixel saturation values of adjacent frames.

  - *delta_lum*: Difference between pixel luma (brightness) values of adjacent frames.

  - *delta_edges*: Difference between calculated edges of adjacent frames. Typically larger than other components, so threshold may need to be increased to compensate.

Once calculated, these components are multiplied by the specified -w/--weights to calculate the final frame score ("content_val").  Weights are set as a set of 4 numbers in the form (*delta_hue*, *delta_sat*, *delta_lum*, *delta_edges*). For example, "--weights 1.0 0.5 1.0 0.2 --threshold 32" is a good starting point for trying edge detection. The final sum is normalized by the weight of all components, so they need not equal 100%. Edge detection is disabled by default to improve performance.

Examples:

    {scenedetect_with_video} detect-content

    {scenedetect_with_video} detect-content --threshold 27.5
"""


@click.command("detect-content", cls=Command, help=DETECT_CONTENT_HELP)
@click.option(
    "--threshold",
    "-t",
    metavar="VAL",
    type=click.FloatRange(
        CONFIG_MAP["detect-content"]["threshold"].min_val,
        CONFIG_MAP["detect-content"]["threshold"].max_val,
    ),
    default=None,
    help='The max difference (0.0 to 255.0) that adjacent frames score must exceed to trigger a cut. Lower values are more sensitive to shot changes. Refers to "content_val" in stats file.%s'
    % (USER_CONFIG.get_help_string("detect-content", "threshold")),
)
@click.option(
    "--weights",
    "-w",
    type=(float, float, float, float),
    default=None,
    metavar="HUE SAT LUM EDGE",
    help="Weights of 4 components used to calculate frame score from (delta_hue, delta_sat, delta_lum, delta_edges).%s"
    % (USER_CONFIG.get_help_string("detect-content", "weights")),
)
@click.option(
    "--luma-only",
    "-l",
    is_flag=True,
    flag_value=True,
    help="Only use luma (brightness) channel. Useful for greyscale videos. Equivalent to setting -w 0 0 1 0.%s"
    % (USER_CONFIG.get_help_string("detect-content", "luma-only")),
)
@click.option(
    "--kernel-size",
    "-k",
    metavar="N",
    type=click.INT,
    default=None,
    help="Size of kernel for expanding detected edges. Must be odd integer greater than or equal to 3. If unset, kernel size is estimated using video resolution.%s"
    % (USER_CONFIG.get_help_string("detect-content", "kernel-size")),
)
@click.option(
    "--min-scene-len",
    "-m",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Minimum length of any scene. Overrides global option -m/--min-scene-len. %s"
    % (
        ""
        if USER_CONFIG.is_default("detect-content", "min-scene-len")
        else USER_CONFIG.get_help_string("detect-content", "min-scene-len")
    ),
)
@click.option(
    "--filter-mode",
    "-f",
    metavar="MODE",
    type=click.Choice(CHOICE_MAP["detect-content"]["filter-mode"], False),
    default=None,
    help="Mode used to enforce -m/--min-scene-len option. Can be one of: %s. %s"
    % (
        ", ".join(CHOICE_MAP["detect-content"]["filter-mode"]),
        USER_CONFIG.get_help_string("detect-content", "filter-mode"),
    ),
)
@click.pass_context
def detect_content_command(
    ctx: click.Context,
    threshold: ty.Optional[float],
    weights: ty.Optional[ty.Tuple[float, float, float, float]],
    luma_only: bool,
    kernel_size: ty.Optional[int],
    min_scene_len: ty.Optional[str],
    filter_mode: ty.Optional[str],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)
    detector_args = ctx.get_detect_content_params(
        threshold=threshold,
        luma_only=luma_only,
        min_scene_len=min_scene_len,
        weights=weights,
        kernel_size=kernel_size,
        filter_mode=filter_mode,
    )
    ctx.add_detector(ContentDetector, detector_args)


DETECT_ADAPTIVE_HELP = """Find fast cuts using diffs in HSL colorspace (rolling average).

Two-pass algorithm that first calculates frame scores with `detect-content`, and then applies a rolling average when processing the result. This can help mitigate false detections in situations such as camera movement.

Examples:

    {scenedetect_with_video} detect-adaptive

    {scenedetect_with_video} detect-adaptive --threshold 3.2
"""


@click.command("detect-adaptive", cls=Command, help=DETECT_ADAPTIVE_HELP)
@click.option(
    "--threshold",
    "-t",
    metavar="VAL",
    type=click.FLOAT,
    default=None,
    help='Threshold (float) that frame score must exceed to trigger a cut. Refers to "adaptive_ratio" in stats file.%s'
    % (USER_CONFIG.get_help_string("detect-adaptive", "threshold")),
)
@click.option(
    "--min-content-val",
    "-c",
    metavar="VAL",
    type=click.FLOAT,
    default=None,
    help='Minimum threshold (float) that "content_val" must exceed to trigger a cut.%s'
    % (USER_CONFIG.get_help_string("detect-adaptive", "min-content-val")),
)
@click.option(
    "--frame-window",
    "-f",
    metavar="VAL",
    type=click.INT,
    default=None,
    help="Size of window to detect deviations from mean. Represents how many frames before/after the current one to use for mean.%s"
    % (USER_CONFIG.get_help_string("detect-adaptive", "frame-window")),
)
@click.option(
    "--weights",
    "-w",
    type=(float, float, float, float),
    default=None,
    help='Weights of 4 components ("delta_hue", "delta_sat", "delta_lum", "delta_edges") used to calculate "content_val".%s'
    % (USER_CONFIG.get_help_string("detect-content", "weights")),
)
@click.option(
    "--luma-only",
    "-l",
    is_flag=True,
    flag_value=True,
    help='Only use luma (brightness) channel. Useful for greyscale videos. Equivalent to "--weights 0 0 1 0".%s'
    % (USER_CONFIG.get_help_string("detect-content", "luma-only")),
)
@click.option(
    "--kernel-size",
    "-k",
    metavar="N",
    type=click.INT,
    default=None,
    help="Size of kernel for expanding detected edges. Must be odd number >= 3. If unset, size is estimated using video resolution.%s"
    % (USER_CONFIG.get_help_string("detect-content", "kernel-size")),
)
@click.option(
    "--min-scene-len",
    "-m",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Minimum length of any scene. Overrides global option -m/--min-scene-len. TIMECODE can be specified in frames (-m 100), in seconds with `s` suffix (-m 3.5s), or timecode (-m 00:01:52.778).%s"
    % (
        ""
        if USER_CONFIG.is_default("detect-adaptive", "min-scene-len")
        else USER_CONFIG.get_help_string("detect-adaptive", "min-scene-len")
    ),
)
@click.pass_context
def detect_adaptive_command(
    ctx: click.Context,
    threshold: ty.Optional[float],
    min_content_val: ty.Optional[float],
    frame_window: ty.Optional[int],
    weights: ty.Optional[ty.Tuple[float, float, float, float]],
    luma_only: bool,
    kernel_size: ty.Optional[int],
    min_scene_len: ty.Optional[str],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)
    detector_args = ctx.get_detect_adaptive_params(
        threshold=threshold,
        min_content_val=min_content_val,
        frame_window=frame_window,
        luma_only=luma_only,
        min_scene_len=min_scene_len,
        weights=weights,
        kernel_size=kernel_size,
    )
    ctx.add_detector(AdaptiveDetector, detector_args)


DETECT_THRESHOLD_HELP = """Find fade in/out using averaging.

Detects fade-in and fade-out events using average pixel values. Resulting cuts are placed between adjacent fade-out and fade-in events.

Examples:

    {scenedetect_with_video} detect-threshold

    {scenedetect_with_video} detect-threshold --threshold 15
"""


@click.command("detect-threshold", cls=Command, help=DETECT_THRESHOLD_HELP)
@click.option(
    "--threshold",
    "-t",
    metavar="VAL",
    type=click.FloatRange(
        CONFIG_MAP["detect-threshold"]["threshold"].min_val,
        CONFIG_MAP["detect-threshold"]["threshold"].max_val,
    ),
    default=None,
    help='Threshold (integer) that frame score must exceed to start a new scene. Refers to "delta_rgb" in stats file.%s'
    % (USER_CONFIG.get_help_string("detect-threshold", "threshold")),
)
@click.option(
    "--fade-bias",
    "-f",
    metavar="PERCENT",
    type=click.FloatRange(
        CONFIG_MAP["detect-threshold"]["fade-bias"].min_val,
        CONFIG_MAP["detect-threshold"]["fade-bias"].max_val,
    ),
    default=None,
    help="Percent (%%) from -100 to 100 of timecode skew of cut placement. -100 indicates the start frame, +100 indicates the end frame, and 0 is the middle of both.%s"
    % (USER_CONFIG.get_help_string("detect-threshold", "fade-bias")),
)
@click.option(
    "--add-last-scene",
    "-l",
    is_flag=True,
    flag_value=True,
    help="If set and video ends after a fade-out event, generate a final cut at the last fade-out position.%s"
    % (USER_CONFIG.get_help_string("detect-threshold", "add-last-scene")),
)
@click.option(
    "--min-scene-len",
    "-m",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Minimum length of any scene. Overrides global option -m/--min-scene-len. TIMECODE can be specified in frames (-m 100), in seconds with `s` suffix (-m 3.5s), or timecode (-m 00:01:52.778).%s"
    % (
        ""
        if USER_CONFIG.is_default("detect-threshold", "min-scene-len")
        else USER_CONFIG.get_help_string("detect-threshold", "min-scene-len")
    ),
)
@click.pass_context
def detect_threshold_command(
    ctx: click.Context,
    threshold: ty.Optional[float],
    fade_bias: ty.Optional[float],
    add_last_scene: bool,
    min_scene_len: ty.Optional[str],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)
    detector_args = ctx.get_detect_threshold_params(
        threshold=threshold,
        fade_bias=fade_bias,
        add_last_scene=add_last_scene,
        min_scene_len=min_scene_len,
    )
    ctx.add_detector(ThresholdDetector, detector_args)


DETECT_HIST_HELP = """Find fast cuts by differencing YUV histograms.

Uses Y channel after converting each frame to YUV to create a histogram of each frame. Histograms between frames are compared to determine a score for how similar they are.

Saved as the `hist_diff` metric in a statsfile.

Examples:

    {scenedetect_with_video} detect-hist

    {scenedetect_with_video} detect-hist --threshold 0.1 --bins 240
"""


@click.command("detect-hist", cls=Command, help=DETECT_HIST_HELP)
@click.option(
    "--threshold",
    "-t",
    metavar="VAL",
    type=click.FloatRange(
        CONFIG_MAP["detect-hist"]["threshold"].min_val,
        CONFIG_MAP["detect-hist"]["threshold"].max_val,
    ),
    default=None,
    help="Max difference (0.0 to 1.0) between histograms of adjacent frames. Lower "
    "values are more sensitive to changes.%s"
    % (USER_CONFIG.get_help_string("detect-hist", "threshold")),
)
@click.option(
    "--bins",
    "-b",
    metavar="NUM",
    type=click.IntRange(
        CONFIG_MAP["detect-hist"]["bins"].min_val, CONFIG_MAP["detect-hist"]["bins"].max_val
    ),
    default=None,
    help="The number of bins to use for the histogram calculation.%s"
    % (USER_CONFIG.get_help_string("detect-hist", "bins")),
)
@click.option(
    "--min-scene-len",
    "-m",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Minimum length of any scene. Overrides global min-scene-len (-m) setting."
    " TIMECODE can be specified as exact number of frames, a time in seconds followed by s,"
    " or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.%s"
    % (
        ""
        if USER_CONFIG.is_default("detect-hist", "min-scene-len")
        else USER_CONFIG.get_help_string("detect-hist", "min-scene-len")
    ),
)
@click.pass_context
def detect_hist_command(
    ctx: click.Context,
    threshold: ty.Optional[float],
    bins: ty.Optional[int],
    min_scene_len: ty.Optional[str],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)
    detector_args = ctx.get_detect_hist_params(
        threshold=threshold, bins=bins, min_scene_len=min_scene_len
    )
    ctx.add_detector(HistogramDetector, detector_args)


DETECT_HASH_HELP = """Find fast cuts using perceptual hashing.

The perceptual hash is taken of adjacent frames, and used to calculate the hamming distance between them. The distance is then normalized by the squared size of the hash, and compared to the threshold.

Saved as the `hash_dist` metric in a statsfile.

Examples:

    {scenedetect_with_video} detect-hash

    {scenedetect_with_video} detect-hash --size 32 --lowpass 3
"""


@click.command("detect-hash", cls=Command, help=DETECT_HASH_HELP)
@click.option(
    "--threshold",
    "-t",
    metavar="VAL",
    type=click.FloatRange(
        CONFIG_MAP["detect-hash"]["threshold"].min_val,
        CONFIG_MAP["detect-hash"]["threshold"].max_val,
    ),
    default=None,
    help=(
        "Max distance between hash values (0.0 to 1.0) of adjacent frames. Lower values are "
        "more sensitive to changes.%s" % (USER_CONFIG.get_help_string("detect-hash", "threshold"))
    ),
)
@click.option(
    "--size",
    "-s",
    metavar="SIZE",
    type=click.IntRange(
        CONFIG_MAP["detect-hash"]["size"].min_val, CONFIG_MAP["detect-hash"]["size"].max_val
    ),
    default=None,
    help="Size of square of low frequency data to include from the discrete cosine transform.%s"
    % (USER_CONFIG.get_help_string("detect-hash", "size")),
)
@click.option(
    "--lowpass",
    "-l",
    metavar="FRAC",
    type=click.IntRange(
        CONFIG_MAP["detect-hash"]["lowpass"].min_val, CONFIG_MAP["detect-hash"]["lowpass"].max_val
    ),
    default=None,
    help=(
        "How much high frequency information to filter from the DCT. 2 means keep lower 1/2 of "
        "the frequency data, 4 means only keep 1/4, etc...%s"
        % (USER_CONFIG.get_help_string("detect-hash", "lowpass"))
    ),
)
@click.option(
    "--min-scene-len",
    "-m",
    metavar="TIMECODE",
    type=click.STRING,
    default=None,
    help="Minimum length of any scene. Overrides global min-scene-len (-m) setting."
    " TIMECODE can be specified as exact number of frames, a time in seconds followed by s,"
    " or a timecode in the format HH:MM:SS or HH:MM:SS.nnn.%s"
    % (
        ""
        if USER_CONFIG.is_default("detect-hash", "min-scene-len")
        else USER_CONFIG.get_help_string("detect-hash", "min-scene-len")
    ),
)
@click.pass_context
def detect_hash_command(
    ctx: click.Context,
    threshold: ty.Optional[float],
    size: ty.Optional[int],
    lowpass: ty.Optional[int],
    min_scene_len: ty.Optional[str],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)
    detector_args = ctx.get_detect_hash_params(
        threshold=threshold, size=size, lowpass=lowpass, min_scene_len=min_scene_len
    )
    ctx.add_detector(HashDetector, detector_args)


LOAD_SCENES_HELP = """Load scenes from CSV instead of detecting. Can be used with CSV generated by `list-scenes`. Scenes are loaded using the specified column as cut locations (frame number or timecode).

Examples:

    {scenedetect_with_video} load-scenes -i scenes.csv

    {scenedetect_with_video} load-scenes -i scenes.csv --start-col-name "Start Timecode"
"""


@click.command("load-scenes", cls=Command, help=LOAD_SCENES_HELP)
@click.option(
    "--input",
    "-i",
    multiple=False,
    metavar="FILE",
    required=True,
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=True),
    help="Scene list to read cut information from.",
)
@click.option(
    "--start-col-name",
    "-c",
    metavar="STRING",
    type=click.STRING,
    default=None,
    help="Name of column used to mark scene cuts.%s"
    % (USER_CONFIG.get_help_string("load-scenes", "start-col-name")),
)
@click.pass_context
def load_scenes_command(
    ctx: click.Context, input: ty.Optional[str], start_col_name: ty.Optional[str]
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    logger.debug("Will load scenes from %s (start_col_name = %s)", input, start_col_name)
    if ctx.scene_manager.get_num_detectors() > 0:
        raise click.ClickException("The load-scenes command cannot be used with detectors.")
    if ctx.load_scenes_input:
        raise click.ClickException("The load-scenes command must only be specified once.")
    input = os.path.abspath(input)
    if not os.path.exists(input):
        raise click.BadParameter(
            f"Could not load scenes, file does not exist: {input}", param_hint="-i/--input"
        )
    ctx.load_scenes_input = input
    ctx.load_scenes_column_name = ctx.config.get_value(
        "load-scenes", "start-col-name", start_col_name
    )


SAVE_HTML_HELP = """Save scene list to HTML file.

To customize image generation, specify the `save-images` command before `save-html`. This command always uses the result of the preceeding `save-images` command, or runs it with the default config values unless `--no-images` is set.
"""


@click.command("save-html", cls=Command, help=SAVE_HTML_HELP)
@click.option(
    "--filename",
    "-f",
    metavar="NAME",
    default="$VIDEO_NAME-Scenes.html",
    type=click.STRING,
    help="Filename format to use for the scene list HTML file. You can use the $VIDEO_NAME macro in the file name. Note that you may have to wrap the format name using single quotes.%s"
    % (USER_CONFIG.get_help_string("save-html", "filename")),
)
@click.option(
    "--no-images",
    "-n",
    is_flag=True,
    flag_value=True,
    help="Do not include images with the result.%s"
    % (USER_CONFIG.get_help_string("save-html", "no-images")),
)
@click.option(
    "--image-width",
    "-w",
    metavar="pixels",
    type=click.INT,
    help="Width in pixels of the images in the resulting HTML table.%s"
    % (USER_CONFIG.get_help_string("save-html", "image-width", show_default=False)),
)
@click.option(
    "--image-height",
    "-h",
    metavar="pixels",
    type=click.INT,
    help="Height in pixels of the images in the resulting HTML table.%s"
    % (USER_CONFIG.get_help_string("save-html", "image-height", show_default=False)),
)
@click.option(
    "--show",
    "-s",
    is_flag=True,
    flag_value=True,
    default=None,
    help="Automatically open resulting HTML when processing is complete.%s"
    % (USER_CONFIG.get_help_string("save-html", "show")),
)
@click.pass_context
def save_html_command(
    ctx: click.Context,
    filename: ty.Optional[ty.AnyStr],
    no_images: bool,
    image_width: ty.Optional[int],
    image_height: ty.Optional[int],
    show: bool,
):
    if ctx.command.name == "save-html":
        logger.warning("WARNING: export-html is deprecated, use save-html instead.")
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)
    # Make sure a save-images command is in the pipeline for us to use the results from if we need
    # to include images.
    include_images = not ctx.config.get_value("save-html", "no-images", no_images)
    if include_images and not ctx.save_images:
        save_images_command.callback()
    save_html_args = {
        "filename": ctx.config.get_value("save-html", "filename", filename),
        "image_width": ctx.config.get_value("save-html", "image-width", image_width),
        "image_height": ctx.config.get_value("save-html", "image-height", image_height),
        "no_images": ctx.config.get_value("save-html", "no-images", no_images),
        "show": ctx.config.get_value("save-html", "show", show),
    }
    ctx.add_command(cli_commands.save_html, save_html_args)


LIST_SCENES_HELP = """Create scene list CSV file (will be named $VIDEO_NAME-Scenes.csv by default).

Examples:

Default:

    {scenedetect_with_video} list-scenes

Without cut list (RFC 4180 compliant CSV):

    {scenedetect_with_video} list-scenes --skip-cuts
"""


@click.command("list-scenes", cls=Command, help=LIST_SCENES_HELP)
@click.option(
    "--output",
    "-o",
    metavar="DIR",
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help="Output directory to save videos to. Overrides global option -o/--output.%s"
    % (USER_CONFIG.get_help_string("list-scenes", "output", show_default=False)),
)
@click.option(
    "--filename",
    "-f",
    metavar="NAME",
    default="$VIDEO_NAME-Scenes.csv",
    type=click.STRING,
    help="Filename format to use for the scene list CSV file. You can use the $VIDEO_NAME macro in the file name. Note that you may have to wrap the name using single quotes or use escape characters (e.g. -f \\$VIDEO_NAME-Scenes.csv).%s"
    % (USER_CONFIG.get_help_string("list-scenes", "filename")),
)
@click.option(
    "--no-output-file",
    "-n",
    is_flag=True,
    flag_value=True,
    default=None,
    help="Only print scene list.%s"
    % (USER_CONFIG.get_help_string("list-scenes", "no-output-file")),
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    flag_value=True,
    default=None,
    help="Suppress printing scene list.%s" % (USER_CONFIG.get_help_string("list-scenes", "quiet")),
)
@click.option(
    "--skip-cuts",
    "-s",
    is_flag=True,
    flag_value=True,
    default=None,
    help="Skip cutting list as first row in the CSV file. Set for RFC 4180 compliant output.%s"
    % (USER_CONFIG.get_help_string("list-scenes", "skip-cuts")),
)
@click.pass_context
def list_scenes_command(
    ctx: click.Context,
    output: ty.Optional[ty.AnyStr],
    filename: ty.Optional[ty.AnyStr],
    no_output_file: ty.Optional[bool],
    quiet: ty.Optional[bool],
    skip_cuts: ty.Optional[bool],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    list_scenes_args = {
        "col_separator": ctx.config.get_value("list-scenes", "col-separator"),
        "cut_format": ctx.config.get_value("list-scenes", "cut-format"),
        "display_scenes": ctx.config.get_value("list-scenes", "display-scenes"),
        "display_cuts": ctx.config.get_value("list-scenes", "display-cuts"),
        "no_output_file": ctx.config.get_value("list-scenes", "no-output-file", no_output_file),
        "filename": ctx.config.get_value("list-scenes", "filename", filename),
        "skip_cuts": ctx.config.get_value("list-scenes", "skip-cuts", skip_cuts),
        "output": ctx.config.get_value("list-scenes", "output", output),
        "quiet": ctx.config.get_value("list-scenes", "quiet", quiet) or ctx.quiet_mode,
        "row_separator": ctx.config.get_value("list-scenes", "row-separator"),
    }
    ctx.add_command(cli_commands.list_scenes, list_scenes_args)


SPLIT_VIDEO_HELP = """Split input video using ffmpeg or mkvmerge.

Examples:

Default:

    {scenedetect_with_video} split-video

Codec-copy mode (not frame accurate):

    {scenedetect_with_video} split-video --copy

Customized filenames:

    {scenedetect_with_video} split-video --filename \\$VIDEO_NAME-Clip-\\$SCENE_NUMBER
"""


@click.command("split-video", cls=Command, help=SPLIT_VIDEO_HELP)
@click.option(
    "--output",
    "-o",
    metavar="DIR",
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help="Output directory to save videos to. Overrides global option -o/--output.%s"
    % (USER_CONFIG.get_help_string("split-video", "output", show_default=False)),
)
@click.option(
    "--filename",
    "-f",
    metavar="NAME",
    default=None,
    type=click.STRING,
    help="File name format to use when saving videos, with or without extension. You can use $VIDEO_NAME and $SCENE_NUMBER macros in the filename. You may have to wrap the format in single quotes or use escape characters to avoid variable expansion (e.g. -f \\$VIDEO_NAME-Scene-\\$SCENE_NUMBER).%s"
    % (USER_CONFIG.get_help_string("split-video", "filename")),
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    flag_value=True,
    default=False,
    help="Hide output from external video splitting tool.%s"
    % (USER_CONFIG.get_help_string("split-video", "quiet")),
)
@click.option(
    "--copy",
    "-c",
    is_flag=True,
    flag_value=True,
    help="Copy instead of re-encode. Faster but less precise.%s"
    % (USER_CONFIG.get_help_string("split-video", "copy")),
)
@click.option(
    "--high-quality",
    "-hq",
    is_flag=True,
    flag_value=True,
    help="Encode video with higher quality, overrides -f option if present. Equivalent to: --rate-factor=17 --preset=slow%s"
    % (USER_CONFIG.get_help_string("split-video", "high-quality")),
)
@click.option(
    "--rate-factor",
    "-crf",
    metavar="RATE",
    default=None,
    type=click.IntRange(
        CONFIG_MAP["split-video"]["rate-factor"].min_val,
        CONFIG_MAP["split-video"]["rate-factor"].max_val,
    ),
    help="Video encoding quality (x264 constant rate factor), from 0-100, where lower is higher quality (larger output). 0 indicates lossless.%s"
    % (USER_CONFIG.get_help_string("split-video", "rate-factor")),
)
@click.option(
    "--preset",
    "-p",
    metavar="LEVEL",
    default=None,
    type=click.Choice(CHOICE_MAP["split-video"]["preset"]),
    help="Video compression quality (x264 preset). Can be one of: %s. Faster modes take less time but output may be larger.%s"
    % (
        ", ".join(CHOICE_MAP["split-video"]["preset"]),
        USER_CONFIG.get_help_string("split-video", "preset"),
    ),
)
@click.option(
    "--args",
    "-a",
    metavar="ARGS",
    type=click.STRING,
    default=None,
    help='Override codec arguments passed to FFmpeg when splitting scenes. Use double quotes (") around arguments. Must specify at least audio/video codec.%s'
    % (USER_CONFIG.get_help_string("split-video", "args")),
)
@click.option(
    "--mkvmerge",
    "-m",
    is_flag=True,
    flag_value=True,
    help="Split video using mkvmerge. Faster than re-encoding, but less precise. If set, options other than -f/--filename, -q/--quiet and -o/--output will be ignored. Note that mkvmerge automatically appends the $SCENE_NUMBER suffix.%s"
    % (USER_CONFIG.get_help_string("split-video", "mkvmerge")),
)
@click.pass_context
def split_video_command(
    ctx: click.Context,
    output: ty.Optional[ty.AnyStr],
    filename: ty.Optional[ty.AnyStr],
    quiet: bool,
    copy: bool,
    high_quality: bool,
    rate_factor: ty.Optional[int],
    preset: ty.Optional[str],
    args: ty.Optional[str],
    mkvmerge: bool,
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    check_split_video_requirements(use_mkvmerge=mkvmerge)
    if "%" in ctx.video_stream.path or "://" in ctx.video_stream.path:
        error = "The split-video command is incompatible with image sequences/URLs."
        raise click.BadParameter(error, param_hint="split-video")

    # Overwrite flags if no encoder flags/options were set via the CLI to avoid conflicting options
    # (e.g. `--copy` should override any `high-quality = yes` setting in the config file).
    if not (mkvmerge or copy or high_quality or args or rate_factor or preset):
        mkvmerge = ctx.config.get_value("split-video", "mkvmerge")
        copy = ctx.config.get_value("split-video", "copy")
        high_quality = ctx.config.get_value("split-video", "high-quality")
        rate_factor = ctx.config.get_value("split-video", "rate-factor")
        preset = ctx.config.get_value("split-video", "preset")
        args = ctx.config.get_value("split-video", "args")

    # Disallow certain combinations of options.
    if mkvmerge or copy:
        command = "mkvmerge (-m)" if mkvmerge else "copy (-c)"
        if high_quality:
            raise click.BadParameter(
                "high-quality (-hq) cannot be used with %s" % (command),
                param_hint="split-video",
            )
        if args:
            raise click.BadParameter(
                "args (-a) cannot be used with %s" % (command), param_hint="split-video"
            )
        if rate_factor:
            raise click.BadParameter(
                "rate-factor (crf) cannot be used with %s" % (command), param_hint="split-video"
            )
        if preset:
            raise click.BadParameter(
                "preset (-p) cannot be used with %s" % (command), param_hint="split-video"
            )

    # mkvmerge-Specific Options
    if mkvmerge and copy:
        logger.warning("copy mode (-c) ignored due to mkvmerge mode (-m).")

    # ffmpeg-Specific Options
    if copy:
        args = "-map 0:v:0 -map 0:a? -map 0:s? -c:v copy -c:a copy"
    elif not args:
        if rate_factor is None:
            rate_factor = 22 if not high_quality else 17
        if preset is None:
            preset = "veryfast" if not high_quality else "slow"
        args = (
            "-map 0:v:0 -map 0:a? -map 0:s? "
            f"-c:v libx264 -preset {preset} -crf {rate_factor} -c:a aac"
        )
    if filename:
        logger.info("Output file name format: %s", filename)

    split_video_args = {
        "name_format": ctx.config.get_value("split-video", "filename", filename),
        "use_mkvmerge": mkvmerge,
        "output": ctx.config.get_value("split-video", "output", output),
        "show_output": not ctx.config.get_value("split-video", "quiet", quiet),
        "ffmpeg_args": args,
    }
    ctx.add_command(cli_commands.split_video, split_video_args)


SAVE_IMAGES_HELP = """Save images from each detected scene.

Examples:

    {scenedetect_with_video} save-images --num-images 5

    {scenedetect_with_video} save-images --width 1024

    {scenedetect_with_video} save-images --filename \\$SCENE_NUMBER-img\\$IMAGE_NUMBER
"""


@click.command("save-images", cls=Command, help=SAVE_IMAGES_HELP)
@click.option(
    "--output",
    "-o",
    metavar="DIR",
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help="Output directory for images. Overrides global option -o/--output.%s"
    % (USER_CONFIG.get_help_string("save-images", "output", show_default=False)),
)
@click.option(
    "--filename",
    "-f",
    metavar="NAME",
    default=None,
    type=click.STRING,
    help="Filename format *without* extension to use when saving images. You can use the $VIDEO_NAME, $SCENE_NUMBER, $IMAGE_NUMBER, and $FRAME_NUMBER macros in the file name. You may have to use escape characters (e.g. -f \\$SCENE_NUMBER-Image-\\$IMAGE_NUMBER) or single quotes.%s"
    % (USER_CONFIG.get_help_string("save-images", "filename")),
)
@click.option(
    "--num-images",
    "-n",
    metavar="N",
    default=None,
    type=click.INT,
    help="Number of images to generate per scene. Will always include start/end frame, unless -n 1, in which case the image will be the frame at the mid-point of the scene.%s"
    % (USER_CONFIG.get_help_string("save-images", "num-images")),
)
@click.option(
    "--jpeg",
    "-j",
    is_flag=True,
    flag_value=True,
    help="Set output format to JPEG (default).%s"
    % (USER_CONFIG.get_help_string("save-images", "format", show_default=False)),
)
@click.option(
    "--webp",
    "-w",
    is_flag=True,
    flag_value=True,
    help="Set output format to WebP",
)
@click.option(
    "--quality",
    "-q",
    metavar="Q",
    default=None,
    type=click.IntRange(0, 100),
    help="JPEG/WebP encoding quality, from 0-100 (higher indicates better quality). For WebP, 100 indicates lossless. [default: JPEG: 95, WebP: 100]%s"
    % (USER_CONFIG.get_help_string("save-images", "quality", show_default=False)),
)
@click.option(
    "--png",
    "-p",
    is_flag=True,
    flag_value=True,
    help="Set output format to PNG.",
)
@click.option(
    "--compression",
    "-c",
    metavar="C",
    default=None,
    type=click.IntRange(0, 9),
    help="PNG compression rate, from 0-9. Higher values produce smaller files but result in longer compression time. This setting does not affect image quality, only file size.%s"
    % (USER_CONFIG.get_help_string("save-images", "compression")),
)
@click.option(
    "-m",
    "--frame-margin",
    metavar="N",
    default=None,
    type=click.INT,
    help="Number of frames to ignore at beginning/end of scenes when saving images. Controls temporal padding on scene boundaries.%s"
    % (USER_CONFIG.get_help_string("save-images", "num-images")),
)
@click.option(
    "--scale",
    "-s",
    metavar="S",
    default=None,
    type=click.FLOAT,
    help="Factor to scale images by. Ignored if -W/--width or -H/--height is set.%s"
    % (USER_CONFIG.get_help_string("save-images", "scale", show_default=False)),
)
@click.option(
    "--height",
    "-H",
    metavar="H",
    default=None,
    type=click.INT,
    help="Height (pixels) of images.%s"
    % (USER_CONFIG.get_help_string("save-images", "height", show_default=False)),
)
@click.option(
    "--width",
    "-W",
    metavar="W",
    default=None,
    type=click.INT,
    help="Width (pixels) of images.%s"
    % (USER_CONFIG.get_help_string("save-images", "width", show_default=False)),
)
@click.pass_context
def save_images_command(
    ctx: click.Context,
    output: ty.Optional[ty.AnyStr] = None,
    filename: ty.Optional[ty.AnyStr] = None,
    num_images: ty.Optional[int] = None,
    jpeg: bool = False,
    webp: bool = False,
    quality: ty.Optional[int] = None,
    png: bool = False,
    compression: ty.Optional[int] = None,
    frame_margin: ty.Optional[int] = None,
    scale: ty.Optional[float] = None,
    height: ty.Optional[int] = None,
    width: ty.Optional[int] = None,
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    if "://" in ctx.video_stream.path:
        error_str = "\nThe save-images command is incompatible with URLs."
        logger.error(error_str)
        raise click.BadParameter(error_str, param_hint="save-images")
    num_flags = sum([1 if flag else 0 for flag in [jpeg, webp, png]])
    if num_flags > 1:
        logger.error(".")
        raise click.BadParameter("Only one image type can be specified.", param_hint="save-images")
    elif num_flags == 0:
        image_format = ctx.config.get_value("save-images", "format").lower()
        jpeg = image_format == "jpeg"
        webp = image_format == "webp"
        png = image_format == "png"

    if not any((scale, height, width)):
        scale = ctx.config.get_value("save-images", "scale")
        height = ctx.config.get_value("save-images", "height")
        width = ctx.config.get_value("save-images", "width")
    scale_method = ctx.config.get_value("save-images", "scale-method")
    quality = (
        (DEFAULT_WEBP_QUALITY if webp else DEFAULT_JPG_QUALITY)
        if ctx.config.is_default("save-images", "quality")
        else ctx.config.get_value("save-images", "quality")
    )
    compression = ctx.config.get_value("save-images", "compression", compression)
    image_extension = "jpg" if jpeg else "png" if png else "webp"
    valid_params = get_cv2_imwrite_params()
    if image_extension not in valid_params or valid_params[image_extension] is None:
        error_strs = [
            "Image encoder type `%s` not supported." % image_extension.upper(),
            "The specified encoder type could not be found in the current OpenCV module.",
            "To enable this output format, please update the installed version of OpenCV.",
            "If you build OpenCV, ensure the the proper dependencies are enabled. ",
        ]
        logger.debug("\n".join(error_strs))
        raise click.BadParameter("\n".join(error_strs), param_hint="save-images")
    output = ctx.config.get_value("save-images", "output", output)

    save_images_args = {
        "encoder_param": compression if png else quality,
        "frame_margin": ctx.config.get_value("save-images", "frame-margin", frame_margin),
        "height": height,
        "image_extension": image_extension,
        "filename": ctx.config.get_value("save-images", "filename", filename),
        "interpolation": scale_method,
        "num_images": ctx.config.get_value("save-images", "num-images", num_images),
        "output": output,
        "scale": scale,
        "show_progress": not ctx.quiet_mode,
        "threading": ctx.config.get_value("save-images", "threading"),
        "width": width,
    }
    ctx.add_command(cli_commands.save_images, save_images_args)

    # Record that we added a save-images command to the pipeline so we can allow save-html
    # to run afterwards (it is dependent on the output).
    ctx.save_images = True


SAVE_EDL_HELP = """Save cuts in EDL format (CMX 3600)."""


@click.command("save-edl", cls=Command, help=SAVE_EDL_HELP)
@click.option(
    "--filename",
    "-f",
    metavar="NAME",
    default=None,
    type=click.STRING,
    help="Filename format to use.%s" % (USER_CONFIG.get_help_string("save-edl", "filename")),
)
@click.option(
    "--title",
    "-t",
    metavar="NAME",
    default=None,
    type=click.STRING,
    help="Title format to use.%s" % (USER_CONFIG.get_help_string("save-edl", "title")),
)
@click.option(
    "--reel",
    "-r",
    metavar="REEL",
    default=None,
    type=click.STRING,
    help="Reel name to use.%s" % (USER_CONFIG.get_help_string("save-edl", "reel")),
)
@click.option(
    "--output",
    "-o",
    metavar="DIR",
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help="Output directory to save EDL file to. Overrides global option -o/--output.%s"
    % (USER_CONFIG.get_help_string("save-edl", "output", show_default=False)),
)
@click.pass_context
def save_edl_command(
    ctx: click.Context,
    filename: ty.Optional[ty.AnyStr],
    title: ty.Optional[ty.AnyStr],
    reel: ty.Optional[ty.AnyStr],
    output: ty.Optional[ty.AnyStr],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    save_edl_args = {
        "filename": ctx.config.get_value("save-edl", "filename", filename),
        "title": ctx.config.get_value("save-edl", "title", title),
        "reel": ctx.config.get_value("save-edl", "reel", reel),
        "output": ctx.config.get_value("save-edl", "output", output),
    }
    ctx.add_command(cli_commands.save_edl, save_edl_args)


SAVE_QP_HELP = """Save cuts as keyframes (I-frames) for video encoding.

The resulting QP file can be used with the `--qpfile` argument in x264/x265.
"""


@click.command("save-qp", cls=Command, help=SAVE_QP_HELP)
@click.option(
    "--filename",
    "-f",
    metavar="NAME",
    default=None,
    type=click.STRING,
    help="Filename format to use.%s" % (USER_CONFIG.get_help_string("save-qp", "filename")),
)
@click.option(
    "--output",
    "-o",
    metavar="DIR",
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help="Output directory to save QP file to. Overrides global option -o/--output.%s"
    % (USER_CONFIG.get_help_string("save-qp", "output", show_default=False)),
)
@click.option(
    "--disable-shift",
    "-d",
    is_flag=True,
    flag_value=True,
    default=None,
    help="Disable shifting frame numbers by start time.%s"
    % (USER_CONFIG.get_help_string("save-qp", "disable-shift")),
)
@click.pass_context
def save_qp_command(
    ctx: click.Context,
    filename: ty.Optional[ty.AnyStr],
    output: ty.Optional[ty.AnyStr],
    disable_shift: ty.Optional[bool],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    save_qp_args = {
        "filename": ctx.config.get_value("save-qp", "filename", filename),
        "output": ctx.config.get_value("save-qp", "output", output),
        "disable_shift": ctx.config.get_value("save-qp", "disable-shift", disable_shift),
    }
    ctx.add_command(cli_commands.save_qp, save_qp_args)


SAVE_XML_HELP = """[IN DEVELOPMENT] Save cuts in XML format."""


@click.command("save-xml", cls=Command, help=SAVE_XML_HELP, hidden=True)
@click.option(
    "--filename",
    "-f",
    metavar="NAME",
    default=None,
    type=click.STRING,
    help="Filename format to use.%s" % (USER_CONFIG.get_help_string("save-xml", "filename")),
)
@click.option(
    "--format",
    metavar="TYPE",
    type=click.Choice(CHOICE_MAP["save-xml"]["format"], False),
    default=None,
    help="Format to export. TYPE must be one of: %s.%s"
    % (
        ", ".join(CHOICE_MAP["save-xml"]["format"]),
        USER_CONFIG.get_help_string("save-xml", "format"),
    ),
)
@click.option(
    "--output",
    "-o",
    metavar="DIR",
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help="Output directory to save XML file to. Overrides global option -o/--output.%s"
    % (USER_CONFIG.get_help_string("save-xml", "output", show_default=False)),
)
@click.pass_context
def save_xml_command(
    ctx: click.Context,
    filename: ty.Optional[ty.AnyStr],
    format: ty.Optional[ty.AnyStr],
    output: ty.Optional[ty.AnyStr],
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    save_xml_args = {
        "filename": ctx.config.get_value("save-xml", "filename", filename),
        "format": ctx.config.get_value("save-xml", "format", format),
        "output": ctx.config.get_value("save-xml", "output", output),
    }
    ctx.add_command(cli_commands.save_xml, save_xml_args)


SAVE_OTIO_HELP = """Save cuts as an OTIO timeline.

Uses the Timeline.1 schema. OTIO (OpenTimelineIO) timelines can be imported by many video editors."""


@click.command("save-otio", cls=Command, help=SAVE_OTIO_HELP)
@click.option(
    "--filename",
    "-f",
    metavar="NAME",
    default=None,
    type=click.STRING,
    help="Filename format to use.%s" % (USER_CONFIG.get_help_string("save-otio", "filename")),
)
@click.option(
    "--name",
    "-n",
    metavar="NAME",
    default=None,
    type=click.STRING,
    help="Name of timeline to use.%s" % (USER_CONFIG.get_help_string("save-otio", "name")),
)
@click.option(
    "--output",
    "-o",
    metavar="DIR",
    type=click.Path(exists=False, dir_okay=True, writable=True, resolve_path=False),
    help="Output directory to save OTIO file to. Overrides global option -o/--output.%s"
    % (USER_CONFIG.get_help_string("save-otio", "output", show_default=False)),
)
@click.option(
    "--audio",
    is_flag=True,
    flag_value=True,
    help="Include audio track (default).",
)
@click.option(
    "--no-audio",
    is_flag=True,
    flag_value=True,
    help="Exclude audio track.",
)
@click.pass_context
def save_otio_command(
    ctx: click.Context,
    filename: ty.Optional[ty.AnyStr],
    name: ty.Optional[ty.AnyStr],
    output: ty.Optional[ty.AnyStr],
    audio: bool,
    no_audio: bool,
):
    ctx = ctx.obj
    assert isinstance(ctx, CliContext)

    if audio and no_audio:
        raise click.BadArgumentUsage("Only one of --audio or --no-audio can be specified.")

    save_otio_args = {
        "filename": ctx.config.get_value("save-otio", "filename", filename),
        "name": ctx.config.get_value("save-otio", "name", name),
        "output": ctx.config.get_value("save-otio", "output", output),
        "audio": ctx.config.get_value(
            "save-otio", "audio", True if audio else False if no_audio else None
        ),
    }
    ctx.add_command(cli_commands.save_otio, save_otio_args)


# ----------------------------------------------------------------------
# CLI Sub-Command Registration
# ----------------------------------------------------------------------

# Informational
scenedetect.add_command(about_command)
scenedetect.add_command(help_command)
scenedetect.add_command(version_command)

# Input
scenedetect.add_command(load_scenes_command)
scenedetect.add_command(time_command)

# Detectors
scenedetect.add_command(detect_adaptive_command)
scenedetect.add_command(detect_content_command)
scenedetect.add_command(detect_hash_command)
scenedetect.add_command(detect_hist_command)
scenedetect.add_command(detect_threshold_command)

# Output
scenedetect.add_command(list_scenes_command)
scenedetect.add_command(save_edl_command)
scenedetect.add_command(save_html_command)
scenedetect.add_command(save_images_command)
scenedetect.add_command(save_qp_command)
scenedetect.add_command(save_xml_command)
scenedetect.add_command(save_otio_command)
scenedetect.add_command(split_video_command)

# Deprecated Commands (Hidden From Help Output)
add_hidden_alias(save_html_command, "export-html")  # Deprecated in v0.6.6, replaced with save-html
