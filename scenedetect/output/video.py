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
# This software may also invoke mkvmerge or FFmpeg, if available.
# FFmpeg is a trademark of Fabrice Bellard.
# mkvmerge is Copyright (C) 2005-2016, Matroska.
# Certain distributions of PySceneDetect may include the above software;
# see the included LICENSE-FFMPEG and LICENSE-MKVMERGE files.
#
"""The ``scenedetect.output.video`` module contains functions to split existing videos into clips
using ffmpeg or mkvmerge.

These programs can be obtained from following URLs (note that mkvmerge is a part mkvtoolnix):

 * FFmpeg:   [ https://ffmpeg.org/download.html ]
 * mkvmerge: [ https://mkvtoolnix.download/downloads.html ]

If you are a Linux user, you can likely obtain the above programs from your package manager.

Once installed, ensure the program can be accessed system-wide by calling the `mkvmerge` or `ffmpeg`
command from a terminal/command prompt. PySceneDetect will automatically use whichever program is
available on the computer, depending on the specified command-line options.
"""

import logging
import math
import subprocess
import time
import typing as ty
from dataclasses import dataclass
from pathlib import Path

from scenedetect.common import FrameTimecode, TimecodePair
from scenedetect.platform import CommandTooLong, Template, get_ffmpeg_path, invoke_command, tqdm

logger = logging.getLogger("pyscenedetect")

_COMMAND_TOO_LONG_STRING = """
Cannot split video due to too many scenes (resulting command
is too large to process). To work around this issue, you can
split the video manually by exporting a list of cuts with the
`list-scenes` command.
See https://github.com/Breakthrough/PySceneDetect/issues/164
for details.  Sorry about that!
"""

_FFMPEG_PATH: ty.Optional[str] = get_ffmpeg_path()
"""Relative path to the ffmpeg binary on this system, if any (will be None if not available)."""

_DEFAULT_FFMPEG_ARGS = (
    "-map 0:v:0 -map 0:a? -map 0:s? -c:v libx264 -preset veryfast -crf 22 -c:a aac"
)
"""Default arguments passed to ffmpeg when invoking the `split_video_ffmpeg` function."""

##
## Command Availability Checking Functions
##


def is_mkvmerge_available() -> bool:
    """Is mkvmerge Available: Gracefully checks if mkvmerge command is available.

    Returns:
        True if `mkvmerge` can be invoked, False otherwise.
    """
    ret_val = None
    try:
        ret_val = subprocess.call(["mkvmerge", "--quiet"])
    except OSError:
        return False
    if ret_val is not None and ret_val != 2:
        return False
    return True


def is_ffmpeg_available() -> bool:
    """Is ffmpeg Available: Gracefully checks if ffmpeg command is available.

    Returns:
        True if `ffmpeg` can be invoked, False otherwise.
    """
    return _FFMPEG_PATH is not None


##
## Output Naming
##


@dataclass
class VideoMetadata:
    """Information about the video being split."""

    name: str
    """Expected name of the video. May differ from `path`."""
    path: Path
    """Path to the input file."""
    total_scenes: int
    """Total number of scenes that will be written."""


@dataclass
class SceneMetadata:
    """Information about the scene being extracted."""

    index: int
    """0-based index of this scene."""
    start: FrameTimecode
    """First frame."""
    end: FrameTimecode
    """Last frame."""


PathFormatter = ty.Callable[[VideoMetadata, SceneMetadata], ty.AnyStr]


def default_formatter(template: str) -> PathFormatter:
    """Formats filenames using a template string which allows the following variables:

    `$VIDEO_NAME`, `$SCENE_NUMBER`, `$START_TIME`, `$END_TIME`, `$START_FRAME`, `$END_FRAME`
    """
    MIN_DIGITS = 3
    format_scene_number: PathFormatter = lambda video, scene: (
        ("%0" + str(max(MIN_DIGITS, math.floor(math.log(video.total_scenes, 10)) + 1)) + "d")
        % (scene.index + 1)
    )
    formatter: PathFormatter = lambda video, scene: Template(template).safe_substitute(
        VIDEO_NAME=video.name,
        SCENE_NUMBER=format_scene_number(video, scene),
        START_TIME=str(scene.start.get_timecode().replace(":", ";")),
        END_TIME=str(scene.end.get_timecode().replace(":", ";")),
        START_FRAME=str(scene.start.frame_num),
        END_FRAME=str(scene.end.frame_num),
    )
    return formatter


##
## Split Video Functions
##


def split_video_mkvmerge(
    input_video_path: str,
    scene_list: ty.Iterable[TimecodePair],
    output_dir: ty.Optional[ty.Union[str, Path]] = None,
    output_file_template: ty.Optional[ty.Union[str, Path]] = "$VIDEO_NAME.mkv",
    video_name: ty.Optional[str] = None,
    show_output: bool = False,
    suppress_output=None,
) -> int:
    """Split `input_video_path` using `mkvmerge` based on the scenes in `scene_list`.

    Arguments:
        input_video_path: Path to the video to be split.
        scene_list : List of scenes as pairs of FrameTimecodes denoting the start/end times.
        output_dir: Directory to output videos. If not set, output will be in working directory.
        output_file_template: Template to use for generating output files. Note that mkvmerge always
            adds the suffix "-$SCENE_NUMBER" to the output paths. Only the $VIDEO_NAME variable
            is supported by this function.
        video_name: Name of the video to be substituted in output_file_template for
            $VIDEO_NAME. If not specified, will be obtained from the filename.
        show_output: If False, adds the --quiet flag when invoking `mkvmerge`.
        suppress_output: [DEPRECATED] DO NOT USE. For backwards compatibility only.
    Returns:
        Return code of invoking mkvmerge (0 on success). If scene_list is empty, will
        still return 0, but no commands will be invoked.
    """
    # Handle backwards compatibility with v0.5 API.
    if isinstance(input_video_path, list):
        logger.error("Using a list of paths is deprecated. Pass a single path instead.")
        if len(input_video_path) > 1:
            raise ValueError("Concatenating multiple input videos is not supported.")
        input_video_path = input_video_path[0]
    if suppress_output is not None:
        logger.error("suppress_output is deprecated, use show_output instead.")
        show_output = not suppress_output

    if not scene_list:
        return 0

    if video_name is None:
        video_name = Path(input_video_path).stem

    # mkvmerge doesn't support adding scene metadata to filenames. It always adds the scene
    # number prefixed with a dash to the filenames.
    template = Template(output_file_template)
    output_path = template.safe_substitute(VIDEO_NAME=video_name)
    if output_dir:
        output_path = Path(output_dir) / output_path
    output_path = Path(output_path)
    logger.info(f"Splitting video with mkvmerge, path template: {output_path}")
    # If there is only one scene, mkvmerge omits the suffix for the output. To make the filenames
    # consistent with the output when there are multiple scenes present, we append "-001".
    if len(scene_list) == 1:
        output_path = output_path.with_stem(output_path.stem + "-001")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    call_list = ["mkvmerge"]
    if not show_output:
        call_list.append("--quiet")
    call_list += [
        "-o",
        str(output_path),
        "--split",
        "parts:%s"
        % ",".join(
            [
                "%s-%s" % (start_time.get_timecode(), end_time.get_timecode())
                for start_time, end_time in scene_list
            ]
        ),
        input_video_path,
    ]
    total_frames = scene_list[-1][1].frame_num - scene_list[0][0].frame_num
    processing_start_time = time.time()
    ret_val = 0
    try:
        # TODO: Capture stdout/stderr and show that if the command fails.
        ret_val = invoke_command(call_list)
        if show_output:
            logger.info(
                "Average processing speed %.2f frames/sec.",
                float(total_frames) / (time.time() - processing_start_time),
            )
    except CommandTooLong:
        logger.error(_COMMAND_TOO_LONG_STRING)
    except OSError:
        logger.error(
            "mkvmerge could not be found on the system."
            " Please install mkvmerge to enable video output support."
        )
    if ret_val != 0:
        logger.error("Error splitting video (mkvmerge returned %d).", ret_val)
    return ret_val


def split_video_ffmpeg(
    input_video_path: str,
    scene_list: ty.Iterable[TimecodePair],
    output_dir: ty.Optional[Path] = None,
    output_file_template: str = "$VIDEO_NAME-Scene-$SCENE_NUMBER.mp4",
    video_name: ty.Optional[str] = None,
    arg_override: str = _DEFAULT_FFMPEG_ARGS,
    show_progress: bool = False,
    show_output: bool = False,
    suppress_output=None,
    hide_progress=None,
    formatter: ty.Optional[PathFormatter] = None,
) -> int:
    """Split `input_video_path` using `ffmpeg` based on the scenes in `scene_list`.

    Arguments:
        input_video_path: Path to the video to be split.
        scene_list: List of scenes (pairs of FrameTimecodes) denoting the start/end of each scene.
        output_dir: Directory to output videos. If not set, output will be in working directory.
        output_file_template: Template to use for generating output filenames.
            The following variables will be replaced in the template for each scene:
            $VIDEO_NAME, $SCENE_NUMBER, $START_TIME, $END_TIME, $START_FRAME, $END_FRAME
        video_name: Name of the video to be substituted in output_file_template. If not
            passed will be calculated from input_video_path automatically.
        arg_override: Allows overriding the arguments passed to ffmpeg for encoding.
        show_progress: If True, will show progress bar provided by tqdm (if installed).
        show_output: If True, will show output from ffmpeg for first split.
        suppress_output: [DEPRECATED] DO NOT USE. For backwards compatibility only.
        hide_progress: [DEPRECATED] DO NOT USE. For backwards compatibility only.
        formatter: Custom formatter callback. Overrides `output_file_template`.

    Returns:
        Return code of invoking ffmpeg (0 on success). If scene_list is empty, will
        still return 0, but no commands will be invoked.
    """
    # Handle backwards compatibility with v0.5 API.
    if isinstance(input_video_path, list):
        logger.error("Using a list of paths is deprecated. Pass a single path instead.")
        if len(input_video_path) > 1:
            raise ValueError("Concatenating multiple input videos is not supported.")
        input_video_path = input_video_path[0]
    if suppress_output is not None:
        logger.error("suppress_output is deprecated, use show_output instead.")
        show_output = not suppress_output
    if hide_progress is not None:
        logger.error("hide_progress is deprecated, use show_progress instead.")
        show_progress = not hide_progress

    if not scene_list:
        return 0

    logger.info("Splitting video with ffmpeg, output path template:\n  %s", output_file_template)
    if output_dir:
        logger.info("Output folder:\n  %s", output_file_template)

    if video_name is None:
        video_name = Path(input_video_path).stem

    arg_override = arg_override.replace('\\"', '"')

    ret_val = 0
    arg_override = arg_override.split(" ")
    scene_num_format = "%0"
    scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + "d"

    if formatter is None:
        formatter = default_formatter(output_file_template)
    video_metadata = VideoMetadata(
        name=video_name, path=input_video_path, total_scenes=len(scene_list)
    )

    try:
        progress_bar = None
        total_frames = scene_list[-1][1].frame_num - scene_list[0][0].frame_num
        if show_progress:
            progress_bar = tqdm(total=total_frames, unit="frame", miniters=1, dynamic_ncols=True)
        processing_start_time = time.time()
        for i, (start_time, end_time) in enumerate(scene_list):
            duration = end_time - start_time
            scene_metadata = SceneMetadata(index=i, start=start_time, end=end_time)
            output_path = Path(formatter(scene=scene_metadata, video=video_metadata))
            if output_dir:
                output_path = Path(output_dir) / output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Gracefully handle case where FFMPEG_PATH might be unset.
            call_list = [_FFMPEG_PATH if _FFMPEG_PATH is not None else "ffmpeg"]
            if not show_output:
                call_list += ["-v", "quiet"]
            elif i > 0:
                # Only show ffmpeg output for the first call, which will display any
                # errors if it fails, and then break the loop. We only show error messages
                # for the remaining calls.
                call_list += ["-v", "error"]
            call_list += [
                "-nostdin",
                "-y",
                "-ss",
                str(start_time.seconds),
                "-i",
                input_video_path,
                "-t",
                str(duration.seconds),
            ]
            call_list += arg_override
            call_list += ["-sn"]
            call_list += [str(output_path)]
            ret_val = invoke_command(call_list)
            if show_output and i == 0 and len(scene_list) > 1:
                logger.info(
                    "Output from ffmpeg for Scene 1 shown above, splitting remaining scenes..."
                )
            if ret_val != 0:
                # TODO: Capture stdout/stderr and display it on any failed calls.
                logger.error("Error splitting video (ffmpeg returned %d).", ret_val)
                break
            if progress_bar:
                progress_bar.update(duration.frame_num)

        if progress_bar:
            progress_bar.close()
        if show_output:
            logger.info(
                "Average processing speed %.2f frames/sec.",
                float(total_frames) / (time.time() - processing_start_time),
            )

    except CommandTooLong:
        logger.error(_COMMAND_TOO_LONG_STRING)
    except OSError:
        logger.error(
            "ffmpeg could not be found on the system."
            " Please install ffmpeg to enable video output support."
        )
    return ret_val
