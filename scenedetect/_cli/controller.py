# -*- coding: utf-8 -*-
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
from string import Template
import time
import typing as ty

from scenedetect.frame_timecode import FrameTimecode
from scenedetect.platform import get_and_create_path
from scenedetect.scene_manager import (
    get_scenes_from_cuts,
    save_images,
    write_scene_list,
    write_scene_list_html,
)
from scenedetect.video_splitter import split_video_mkvmerge, split_video_ffmpeg
from scenedetect.video_stream import SeekError
from scenedetect._cli.context import CliContext, check_split_video_requirements

logger = logging.getLogger('pyscenedetect')

SceneList = ty.List[ty.Tuple[FrameTimecode, FrameTimecode]]

CutList = ty.List[FrameTimecode]


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

    if context.load_scenes_input:
        # Skip detection if load-scenes was used.
        logger.info("Skipping detection, loading scenes from: %s", context.load_scenes_input)
        if context.stats_file_path:
            logger.warning("WARNING: -s/--stats will be ignored due to load-scenes.")
        scene_list, cut_list = _load_scenes(context)
        scene_list = _postprocess_scene_list(context, scene_list)
        logger.info("Loaded %d scenes.", len(scene_list))
    else:
        # Perform scene detection on input.
        scene_list, cut_list = _detect(context)
        scene_list = _postprocess_scene_list(context, scene_list)
        # Handle -s/--stats option.
        _save_stats(context)
        if scene_list:
            logger.info(
                'Detected %d scenes, average shot length %.1f seconds.', len(scene_list),
                sum([(end_time - start_time).get_seconds() for start_time, end_time in scene_list])
                / float(len(scene_list)))
        else:
            logger.info('No scenes detected.')

    # Handle list-scenes command.
    _list_scenes(context, scene_list, cut_list)

    # Handle save-images command.
    image_filenames = _save_images(context, scene_list)

    # Handle export-html command.
    _export_html(context, scene_list, cut_list, image_filenames)

    # Handle split-video command.
    _split_video(context, scene_list)


def _detect(context: CliContext) -> ty.Optional[ty.Tuple[SceneList, CutList]]:
    # Use default detector if one was not specified.
    if context.scene_manager.get_num_detectors() == 0:
        detector_type, detector_args = context.default_detector
        logger.debug('Using default detector: %s(%s)' % (detector_type.__name__, detector_args))
        context.scene_manager.add_detector(detector_type(**detector_args))

    perf_start_time = time.time()
    if context.start_time is not None:
        logger.debug('Seeking to start time...')
        try:
            context.video_stream.seek(target=context.start_time)
        except SeekError as ex:
            logger.critical('Failed to seek to %s / frame %d: %s',
                            context.start_time.get_timecode(), context.start_time.get_frames(),
                            str(ex))
            return None

    num_frames = context.scene_manager.detect_scenes(
        video=context.video_stream,
        duration=context.duration,
        end_time=context.end_time,
        frame_skip=context.frame_skip,
        show_progress=not context.quiet_mode)

    # Handle case where video failure is most likely due to multiple audio tracks (#179).
    # TODO(#380): Ensure this does not erroneusly fire.
    if num_frames <= 0 and context.video_stream.BACKEND_NAME == 'opencv':
        logger.critical(
            'Failed to read any frames from video file. This could be caused by the video'
            ' having multiple audio tracks. If so, try installing the PyAV backend:\n'
            '      pip install av\n'
            'Or remove the audio tracks by running either:\n'
            '      ffmpeg -i input.mp4 -c copy -an output.mp4\n'
            '      mkvmerge -o output.mkv input.mp4\n'
            'For details, see https://scenedetect.com/faq/')
        return None

    perf_duration = time.time() - perf_start_time
    logger.info('Processed %d frames in %.1f seconds (average %.2f FPS).', num_frames,
                perf_duration,
                float(num_frames) / perf_duration)

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
        path = get_and_create_path(context.stats_file_path, context.output_dir)
        logger.info('Saving frame metrics to stats file: %s', path)
        with open(path, mode="w") as file:
            context.stats_manager.save_to_csv(csv_file=file)
    else:
        logger.debug('No frame metrics updated, skipping update of the stats file.')


def _list_scenes(context: CliContext, scene_list: SceneList, cut_list: CutList) -> None:
    """Handles the `list-scenes` command."""
    if not context.list_scenes:
        return
    # Write scene list CSV to if required.
    if context.scene_list_output:
        scene_list_filename = Template(
            context.scene_list_name_format).safe_substitute(VIDEO_NAME=context.video_stream.name)
        if not scene_list_filename.lower().endswith('.csv'):
            scene_list_filename += '.csv'
        scene_list_path = get_and_create_path(
            scene_list_filename,
            context.scene_list_dir if context.scene_list_dir is not None else context.output_dir)
        logger.info('Writing scene list to CSV file:\n  %s', scene_list_path)
        with open(scene_list_path, 'wt') as scene_list_file:
            write_scene_list(
                output_csv_file=scene_list_file,
                scene_list=scene_list,
                include_cut_list=not context.skip_cuts,
                cut_list=cut_list)
    # Suppress output if requested.
    if context.list_scenes_quiet:
        return
    # Print scene list.
    if context.display_scenes:
        logger.info(
            """Scene List:
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
%s
-----------------------------------------------------------------------""", '\n'.join([
                " |  %5d  | %11d | %s | %11d | %s |" %
                (i + 1, start_time.get_frames() + 1, start_time.get_timecode(),
                 end_time.get_frames(), end_time.get_timecode())
                for i, (start_time, end_time) in enumerate(scene_list)
            ]))
    # Print cut list.
    if cut_list and context.display_cuts:
        logger.info("Comma-separated timecode list:\n  %s",
                    ",".join([context.cut_format.format(cut) for cut in cut_list]))


def _save_images(context: CliContext,
                 scene_list: SceneList) -> ty.Optional[ty.Dict[int, ty.List[str]]]:
    """Handles the `save-images` command."""
    if not context.save_images:
        return None
    # Command can override global output directory setting.
    output_dir = (context.output_dir if context.image_dir is None else context.image_dir)
    return save_images(
        scene_list=scene_list,
        video=context.video_stream,
        num_images=context.num_images,
        frame_margin=context.frame_margin,
        image_extension=context.image_extension,
        encoder_param=context.image_param,
        image_name_template=context.image_name_format,
        output_dir=output_dir,
        show_progress=not context.quiet_mode,
        scale=context.scale,
        height=context.height,
        width=context.width,
        interpolation=context.scale_method)


def _export_html(context: CliContext, scene_list: SceneList, cut_list: CutList,
                 image_filenames: ty.Optional[ty.Dict[int, ty.List[str]]]) -> None:
    """Handles the `export-html` command."""
    if not context.export_html:
        return
    # Command can override global output directory setting.
    output_dir = (context.output_dir if context.image_dir is None else context.image_dir)
    html_filename = Template(
        context.html_name_format).safe_substitute(VIDEO_NAME=context.video_stream.name)
    if not html_filename.lower().endswith('.html'):
        html_filename += '.html'
    html_path = get_and_create_path(html_filename, output_dir)
    logger.info('Exporting to html file:\n %s:', html_path)
    if not context.html_include_images:
        image_filenames = None
    write_scene_list_html(
        html_path,
        scene_list,
        cut_list,
        image_filenames=image_filenames,
        image_width=context.image_width,
        image_height=context.image_height)


def _split_video(context: CliContext, scene_list: SceneList) -> None:
    """Handles the `split-video` command."""
    if not context.split_video:
        return
    output_path_template = context.split_name_format
    # Add proper extension to filename template if required.
    dot_pos = output_path_template.rfind('.')
    extension_length = 0 if dot_pos < 0 else len(output_path_template) - (dot_pos + 1)
    # If using mkvmerge, force extension to .mkv.
    if context.split_mkvmerge and not output_path_template.endswith('.mkv'):
        output_path_template += '.mkv'
    # Otherwise, if using ffmpeg, only add an extension if one doesn't exist.
    elif not 2 <= extension_length <= 4:
        output_path_template += '.mp4'
    # Ensure the appropriate tool is available before handling split-video.
    check_split_video_requirements(context.split_mkvmerge)
    # Command can override global output directory setting.
    output_dir = context.output_dir if context.split_dir is None else context.split_dir
    if context.split_mkvmerge:
        split_video_mkvmerge(
            input_video_path=context.video_stream.path,
            scene_list=scene_list,
            output_dir=output_dir,
            output_file_template=output_path_template,
            show_output=not (context.quiet_mode or context.split_quiet),
        )
    else:
        split_video_ffmpeg(
            input_video_path=context.video_stream.path,
            scene_list=scene_list,
            output_dir=output_dir,
            output_file_template=output_path_template,
            arg_override=context.split_args,
            show_progress=not context.quiet_mode,
            show_output=not (context.quiet_mode or context.split_quiet),
        )
    if scene_list:
        logger.info('Video splitting completed, scenes written to disk.')


def _load_scenes(context: CliContext) -> ty.Tuple[SceneList, CutList]:
    assert context.load_scenes_input
    assert os.path.exists(context.load_scenes_input)

    with open(context.load_scenes_input, 'r') as input_file:
        file_reader = csv.reader(input_file)
        csv_headers = next(file_reader)
        if not context.load_scenes_column_name in csv_headers:
            csv_headers = next(file_reader)
        # Check to make sure column headers are present
        if context.load_scenes_column_name not in csv_headers:
            raise ValueError('specified column header for scene start is not present')

        col_idx = csv_headers.index(context.load_scenes_column_name)

        cut_list = sorted(
            FrameTimecode(row[col_idx], fps=context.video_stream.frame_rate) - 1
            for row in file_reader)
        # `SceneDetector` works on cuts, so we have to skip the first scene and use the first frame
        # of the next scene as the cut point. This can be fixed if we used `SparseSceneDetector`
        # but this part of the API is being reworked and hasn't been used by any detectors yet.
        if cut_list:
            cut_list = cut_list[1:]

        start_time = context.video_stream.base_timecode
        if context.start_time is not None:
            start_time = context.start_time
            cut_list = [cut for cut in cut_list if cut > context.start_time]

        end_time = context.video_stream.duration
        if context.end_time is not None or context.duration is not None:
            if context.end_time is not None:
                end_time = context.end_time
            elif context.duration is not None:
                end_time = start_time + context.duration
            end_time = min(end_time, context.video_stream.duration)
        cut_list = [cut for cut in cut_list if cut < end_time]

        return get_scenes_from_cuts(
            cut_list=cut_list, start_pos=start_time, end_pos=end_time), cut_list


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
