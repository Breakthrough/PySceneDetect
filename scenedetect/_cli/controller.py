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
"""Logic for the PySceneDetect command."""

import csv
import logging
import os
import time
import typing as ty
import warnings

from scenedetect._cli.context import CliContext
from scenedetect.backends import VideoStreamCv2, VideoStreamMoviePy
from scenedetect.common import FrameTimecode
from scenedetect.platform import get_and_create_path
from scenedetect.scene_manager import CutList, SceneList, get_scenes_from_cuts
from scenedetect.video_stream import SeekError

logger = logging.getLogger("pyscenedetect")


def run_scenedetect(context: CliContext):
    """Perform main CLI application control logic. Run once all command-line options and
    configuration file options have been validated.

    Arguments:
        context: Prevalidated command-line option context to use for processing.
    """
    # No input may have been specified depending on the commands/args that were used.
    logger.debug("Running controller.")
    if context.scene_manager is None:
        logger.debug("No input specified.")
        return

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
        scenes = _postprocess_scene_list(context, scenes)
        logger.info("Loaded %d scenes.", len(scenes))
    else:
        # Perform scene detection on input.
        result = _detect(context)
        if result is None:
            return
        scenes, cuts = result
        scenes = _postprocess_scene_list(context, scenes)
        # Handle -s/--stats option.
        _save_stats(context)
        if scenes:
            logger.info(
                "Detected %d scenes, average shot length %.1f seconds.",
                len(scenes),
                sum([(end_time - start_time).get_seconds() for start_time, end_time in scenes])
                / float(len(scenes)),
            )
        else:
            logger.info("No scenes detected.")

    # Handle post-processing commands the user wants to run (see scenedetect._cli.commands).
    for handler, kwargs in context.commands:
        handler(context=context, scenes=scenes, cuts=cuts, **kwargs)


def _postprocess_scene_list(context: CliContext, scene_list: SceneList) -> SceneList:
    # Handle --merge-last-scene. If set, when the last scene is shorter than --min-scene-len,
    # it will be merged with the previous one.
    if context.merge_last_scene and context.min_scene_len is not None and context.min_scene_len > 0:
        if len(scene_list) > 1 and (scene_list[-1][1] - scene_list[-1][0]) < context.min_scene_len:
            new_last_scene = (scene_list[-2][0], scene_list[-1][1])
            scene_list = scene_list[:-2] + [new_last_scene]

    # Handle --drop-short-scenes.
    if context.drop_short_scenes and context.min_scene_len > 0:
        scene_list = [s for s in scene_list if (s[1] - s[0]) >= context.min_scene_len]

    return scene_list


def _detect(context: CliContext) -> ty.Optional[ty.Tuple[SceneList, CutList]]:
    perf_start_time = time.time()

    context.ensure_detector()
    if context.start_time is not None:
        logger.debug("Seeking to start time...")
        try:
            context.video_stream.seek(target=context.start_time)
        except SeekError as ex:
            logger.critical(
                "Failed to seek to %s / frame %d: %s",
                context.start_time.get_timecode(),
                context.start_time.get_frames(),
                str(ex),
            )
            return None

    num_frames = context.scene_manager.detect_scenes(
        video=context.video_stream,
        duration=context.duration,
        end_time=context.end_time,
        frame_skip=context.frame_skip,
        show_progress=not context.quiet_mode,
    )

    # Handle case where video failure is most likely due to multiple audio tracks (#179).
    # TODO(#380): Ensure this does not erroneusly fire.
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
    if context.stats_manager.is_save_required():
        path = get_and_create_path(context.stats_file_path, context.output)
        logger.info("Saving frame metrics to stats file: %s", path)
        with open(path, mode="w") as file:
            context.stats_manager.save_to_csv(csv_file=file)
    else:
        logger.debug("No frame metrics updated, skipping update of the stats file.")


def _load_scenes(context: CliContext) -> ty.Tuple[SceneList, CutList]:
    assert context.load_scenes_input
    assert os.path.exists(context.load_scenes_input)

    with open(context.load_scenes_input) as input_file:
        file_reader = csv.reader(input_file)
        csv_headers = next(file_reader)
        if context.load_scenes_column_name not in csv_headers:
            csv_headers = next(file_reader)
        # Check to make sure column headers are present and then load the data.
        if context.load_scenes_column_name not in csv_headers:
            raise ValueError("specified column header for scene start is not present")
        col_idx = csv_headers.index(context.load_scenes_column_name)
        cut_list = sorted(
            FrameTimecode(row[col_idx], fps=context.video_stream.frame_rate) - 1
            for row in file_reader
        )
        # `SceneDetector` works on cuts, so we have to skip the first scene and place the first
        # cut point where the next scenes starts.
        if cut_list:
            cut_list = cut_list[1:]

        start_time = context.video_stream.base_timecode
        if context.start_time is not None:
            start_time = context.start_time
            cut_list = [cut for cut in cut_list if cut > context.start_time]

        end_time = context.video_stream.duration
        if context.end_time is not None:
            end_time = min(context.end_time, context.video_stream.duration)
        elif context.duration is not None:
            end_time = min(start_time + context.duration, context.video_stream.duration)

        cut_list = [cut for cut in cut_list if cut < end_time]
        scene_list = get_scenes_from_cuts(cut_list=cut_list, start_pos=start_time, end_pos=end_time)

        return (scene_list, cut_list)
