#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2023 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Logic for the PySceneDetect command."""

import csv
import logging
import os
import time
import warnings
from fractions import Fraction

from scenedetect._cli.context import CliContext
from scenedetect.backends import VideoStreamCv2, VideoStreamMoviePy
from scenedetect.common import (
    FramePosition,
    PositionPair,
    Timecode,
    parse_frame_or_time,
)
from scenedetect.platform import get_and_create_path
from scenedetect.scene_manager import CutList, SceneList, _resolve_end_time
from scenedetect.video_stream import SeekError

logger = logging.getLogger("pyscenedetect")


def run_scenedetect(context: CliContext) -> bool:
    """Perform main CLI application control logic. Run once all command-line options and
    configuration file options have been validated.

    Arguments:
        context: Prevalidated command-line option context to use for processing.

    Returns:
        False if scene detection failed, True otherwise.
    """
    # No input may have been specified depending on the commands/args that were used.
    logger.debug("Running controller.")
    if context.scene_manager is None:
        logger.debug("No input specified.")
        return True

    # Suppress warnings when reading past EOF in MoviePy (#461).
    if VideoStreamMoviePy and isinstance(context.video_stream, VideoStreamMoviePy):
        is_debug = context.config.get_value("global", "verbosity") != "debug"
        if not is_debug:
            warnings.filterwarnings("ignore", module="moviepy")

    if context.load_scenes_input:
        # Skip detection if load-scenes was used.
        logger.info("Skipping detection, loading scenes from: %s", context.load_scenes_input)
        if context.stats_file_path:
            logger.warning("WARNING: -s/--stats will be ignored due to load-scenes.")
        scenes, cuts = _load_scenes(context)
        context.start_pos = scenes[0][0] if scenes else None
        scenes = _postprocess_scene_list(context, scenes)
        logger.info("Loaded %d scenes.", len(scenes))
    else:
        # Perform scene detection on input.
        result = _detect(context)
        if result is None:
            return False
        scenes, cuts = result
        context.start_pos = scenes[0][0] if scenes else None
        scenes = _postprocess_scene_list(context, scenes)
        # Handle -s/--stats option.
        _save_stats(context)
        if scenes:
            logger.info(
                "Detected %d scenes, average shot length %.1f seconds.",
                len(scenes),
                float(
                    sum((end_pos - start_pos).elapsed for start_pos, end_pos in scenes)
                    / len(scenes)
                ),
            )
        else:
            logger.info("No scenes detected.")

    # Handle post-processing commands the user wants to run (see scenedetect._cli.commands).
    for handler, kwargs in context.commands:
        handler(context=context, scenes=scenes, cuts=cuts, **kwargs)
    return True


def _postprocess_scene_list(context: CliContext, scene_list: SceneList) -> SceneList:
    if context.min_scene_len is None:
        return scene_list
    minimum = parse_frame_or_time(context.min_scene_len)
    if minimum == 0:
        return scene_list

    def is_short(scene: PositionPair):
        start_pos, end_pos = scene
        if isinstance(minimum, int):
            return end_pos.frame_number - start_pos.frame_number < minimum
        return (end_pos - start_pos).elapsed < minimum

    # Handle --merge-last-scene. If set, when the last scene is shorter than --min-scene-len,
    # it will be merged with the previous one.
    if context.merge_last_scene and len(scene_list) > 1 and is_short(scene_list[-1]):
        new_last_scene = (scene_list[-2][0], scene_list[-1][1])
        scene_list = [*scene_list[:-2], new_last_scene]

    # Handle --drop-short-scenes.
    if context.drop_short_scenes:
        scene_list = [s for s in scene_list if not is_short(s)]

    return scene_list


def _detect(context: CliContext) -> tuple[SceneList, CutList] | None:
    perf_start_time = time.time()
    assert context.scene_manager is not None
    assert context.video_stream is not None
    assert context.frame_skip is not None

    # Reject start times past EOF before any backend seeks. OpenCV/PyAV previously
    # continued and produced inconsistent errors; MoviePy raised SeekError (#380).
    if context.start_time is not None:
        if isinstance(context.start_time, int):
            frame_count = context.video_stream.frame_count
            beyond_end = frame_count is not None and context.start_time >= frame_count
        else:
            video_duration = context.video_stream.duration
            beyond_end = video_duration is not None and context.start_time.seconds >= video_duration
        if beyond_end:
            logger.critical("start time is beyond the end of the video")
            return None
    try:
        end_time = _resolve_end_time(
            context.start_time, context.end_time, context.video_stream.frame_numbering
        )
    except ValueError as ex:
        logger.critical("%s", ex)
        return None

    context.ensure_detector()
    if context.start_time is not None:
        target_description = (
            f"frame {context.start_time}"
            if isinstance(context.start_time, int)
            else context.start_time.get_timecode()
        )
        logger.debug("Seeking to start time...")
        try:
            context.video_stream.seek(target=context.start_time)
        except SeekError as ex:
            logger.critical("Failed to seek to %s: %s", target_description, ex)
            return None

        if context.video_stream.peek_timecode() is None:
            logger.critical("No frames available at requested start %s.", target_description)
            return None

    if end_time is not None:
        if isinstance(end_time, int):
            empty_range = context.video_stream.frame_number + 1 >= end_time
        else:
            first_timecode = context.video_stream.peek_timecode()
            empty_range = first_timecode is not None and first_timecode.seconds >= end_time.seconds
        if empty_range:
            logger.critical("No frames fall within the requested detection range.")
            return None

    num_frames = context.scene_manager.detect_scenes(
        video=context.video_stream,
        duration=context.duration,
        end_time=end_time,
        frame_skip=context.frame_skip,
        show_progress=not context.quiet_mode,
    )

    # Handle case where video failure is most likely due to multiple audio tracks (#179).
    if num_frames <= 0 and isinstance(context.video_stream, VideoStreamCv2):
        logger.critical(
            "Failed to read any frames from video file. This could be caused by the video"
            " having multiple audio tracks. If so, try installing the PyAV backend:\n"
            "      pip install av\n"
            "Or remove the audio tracks by running either:\n"
            "      ffmpeg -i input.mp4 -c copy -an output.mp4\n"
            "      mkvmerge -o output.mkv input.mp4\n"
            "For details, see https://scenedetect.com/faq/"
        )
        return None

    if num_frames <= 0 and context.use_stdin:
        logger.critical(
            "Failed to read any frames from stdin. An MP4 needs its index at the start of the file"
            " to be read from a pipe (ffmpeg -movflags +faststart). Otherwise, try remuxing to MKV"
            " or MPEG-TS:\n"
            "      ffmpeg -i input.mp4 -c copy -f matroska -\n"
        )
        return None

    perf_duration = time.time() - perf_start_time
    logger.info(
        "Processed %d frames in %.1f seconds (average %.2f FPS).",
        num_frames,
        perf_duration,
        float(num_frames) / perf_duration,
    )

    # Get list of detected cuts/scenes from the SceneManager to generate the required output
    # files, based on the given commands (list-scenes, split-video, save-images, etc...).
    cut_list = context.scene_manager.get_cut_list(show_warning=False)
    scene_list = context.scene_manager.get_scene_list(start_in_scene=True)

    return scene_list, cut_list


def _save_stats(context: CliContext) -> None:
    """Handles saving the statsfile if -s/--stats was specified."""
    if not context.stats_file_path:
        return
    assert context.stats_manager is not None
    if context.stats_manager.is_save_required():
        path = get_and_create_path(context.stats_file_path, context.output)
        logger.info("Saving frame metrics to stats file: %s", path)
        with open(path, mode="w") as file:
            context.stats_manager.save_to_csv(csv_file=file)
    else:
        logger.debug("No frame metrics updated, skipping update of the stats file.")


def _load_scenes(context: CliContext) -> tuple[SceneList, CutList]:
    assert context.load_scenes_input
    assert context.load_scenes_columns
    assert os.path.exists(context.load_scenes_input)

    columns = context.load_scenes_columns
    scene_list: SceneList = []
    with open(context.load_scenes_input, newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames and reader.fieldnames[0] == "Timecode List:":
            reader = csv.DictReader(input_file)

        missing_columns = set(columns.values()) - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"Missing scene columns: {', '.join(sorted(missing_columns))}")

        for row in reader:
            if any(row[column] is None for column in columns.values()):
                raise ValueError("Scene row is missing a required boundary value.")

            start_frame = int(row[columns["start_frame"]]) - 1
            end_frame = int(row[columns["end_frame"]])
            start_seconds = _parse_csv_seconds(row[columns["start_time"]])
            end_seconds = _parse_csv_seconds(row[columns["end_time"]])

            if start_frame < 0 or end_frame <= start_frame:
                raise ValueError("Invalid scene frame range.")
            if end_seconds < start_seconds:
                raise ValueError("Scene end time precedes its start time.")

            start = FramePosition(
                timecode=Timecode(
                    start_seconds.numerator,
                    Fraction(1, start_seconds.denominator),
                ),
                frame_number=start_frame,
            )
            end = FramePosition(
                timecode=Timecode(
                    end_seconds.numerator,
                    Fraction(1, end_seconds.denominator),
                ),
                frame_number=end_frame,
            )
            scene_list.append((start, end))

    if not scene_list:
        return [], []

    start_limit = (
        parse_frame_or_time(context.start_time) if context.start_time is not None else None
    )
    stop_limit = parse_frame_or_time(context.end_time) if context.end_time is not None else None
    length = parse_frame_or_time(context.duration) if context.duration is not None else None

    if length == 0:
        return [], []

    if length is not None:
        if start_limit is None:
            origin = (
                scene_list[0][0].frame_number
                if isinstance(length, int)
                else scene_list[0][0].timecode.seconds
            )
        elif (isinstance(start_limit, int) and isinstance(length, int)) or (
            isinstance(start_limit, Fraction) and isinstance(length, Fraction)
        ):
            origin = start_limit
        else:
            matches = {
                (position.frame_number, position.timecode.seconds)
                for scene in scene_list
                for position in scene
                if (
                    position.frame_number
                    if isinstance(start_limit, int)
                    else position.timecode.seconds
                )
                == start_limit
            }
            if len(matches) != 1:
                raise ValueError(
                    "Cannot convert the requested start to the duration's units: "
                    "the CSV has no unique saved position for it."
                )

            frame_number, seconds = next(iter(matches))
            origin = frame_number if isinstance(length, int) else seconds

        stop_limit = origin + length

    selected: SceneList = []
    for start, end in scene_list:
        if start_limit is not None:
            left = start.frame_number if isinstance(start_limit, int) else start.timecode.seconds
            right = end.frame_number if isinstance(start_limit, int) else end.timecode.seconds

            # Retain a zero-elapsed row exactly at the requested start.
            if right < start_limit or (right == start_limit and left < right):
                continue
            if left < start_limit < right:
                raise ValueError(
                    "The requested range would split a saved scene. "
                    "The CSV does not contain the complete position for that cutoff."
                )

        if stop_limit is not None:
            left = start.frame_number if isinstance(stop_limit, int) else start.timecode.seconds
            right = end.frame_number if isinstance(stop_limit, int) else end.timecode.seconds

            if left >= stop_limit:
                continue
            if stop_limit < right:
                raise ValueError(
                    "The requested range would split a saved scene. "
                    "The CSV does not contain the complete position for that cutoff."
                )

        selected.append((start, end))

    cut_list = [start for start, _ in selected[1:]]
    return selected, cut_list


def _parse_csv_seconds(value: str) -> Fraction:
    """Parse a CSV time field whose unit is already known."""
    value = value.strip()
    if ":" in value:
        sign = -1 if value.startswith("-") else 1
        text = value[1:] if sign < 0 else value
        return sign * Fraction(parse_frame_or_time(text))
    return Fraction(value.removesuffix("s"))
