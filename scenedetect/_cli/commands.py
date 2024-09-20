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

import logging
import typing as ty
from string import Template

import scenedetect.scene_manager as scene_manager
from scenedetect._cli.context import CliContext
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.platform import get_and_create_path
from scenedetect.video_splitter import split_video_ffmpeg, split_video_mkvmerge

logger = logging.getLogger("pyscenedetect")

SceneList = ty.List[ty.Tuple[FrameTimecode, FrameTimecode]]

CutList = ty.List[FrameTimecode]


def list_scenes(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    scene_list_output: bool,
    scene_list_name_format: str,
    output_dir: str,
    skip_cuts: bool,
    quiet: bool,
    display_scenes: bool,
    display_cuts: bool,
    cut_format: str,
    **kwargs,
):
    """Handles the `list-scenes` command."""
    # Write scene list CSV to if required.
    if scene_list_output:
        scene_list_filename = Template(scene_list_name_format).safe_substitute(
            VIDEO_NAME=context.video_stream.name
        )
        if not scene_list_filename.lower().endswith(".csv"):
            scene_list_filename += ".csv"
        scene_list_path = get_and_create_path(
            scene_list_filename,
            output_dir,
        )
        logger.info("Writing scene list to CSV file:\n  %s", scene_list_path)
        with open(scene_list_path, "w") as scene_list_file:
            scene_manager.write_scene_list(
                output_csv_file=scene_list_file,
                scene_list=scenes,
                include_cut_list=not skip_cuts,
                cut_list=cuts,
            )
    # Suppress output if requested.
    if quiet:
        return
    # Print scene list.
    if display_scenes:
        logger.info(
            """Scene List:
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
%s
-----------------------------------------------------------------------""",
            "\n".join(
                [
                    " |  %5d  | %11d | %s | %11d | %s |"
                    % (
                        i + 1,
                        start_time.get_frames() + 1,
                        start_time.get_timecode(),
                        end_time.get_frames(),
                        end_time.get_timecode(),
                    )
                    for i, (start_time, end_time) in enumerate(scenes)
                ]
            ),
        )
    # Print cut list.
    if cuts and display_cuts:
        logger.info(
            "Comma-separated timecode list:\n  %s",
            ",".join([cut_format.format(cut) for cut in cuts]),
        )


def save_images(
    context: CliContext,
    scenes: SceneList,
    num_images: int,
    frame_margin: int,
    image_extension: str,
    encoder_param: int,
    image_name_template: str,
    output_dir: ty.Optional[str],
    show_progress: bool,
    scale: int,
    height: int,
    width: int,
    interpolation: scene_manager.Interpolation,
    **kwargs,
):
    """Handles the `save-images` command."""
    logger.info(f"Saving images to {output_dir} with format {image_extension}")
    logger.debug(f"encoder param: {encoder_param}")
    images = scene_manager.save_images(
        scene_list=scenes,
        video=context.video_stream,
        num_images=num_images,
        frame_margin=frame_margin,
        image_extension=image_extension,
        encoder_param=encoder_param,
        image_name_template=image_name_template,
        output_dir=output_dir,
        show_progress=show_progress,
        scale=scale,
        height=height,
        width=width,
        interpolation=interpolation,
    )
    context.save_images_result = (images, output_dir)


def export_html(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    image_width: int,
    image_height: int,
    html_name_format: str,
    **kwargs,
):
    """Handles the `export-html` command."""
    save_images_result = context.save_images_result
    # Command can override global output directory setting.
    output_dir = save_images_result[1] if save_images_result[1] is not None else context.output_dir
    html_filename = Template(html_name_format).safe_substitute(VIDEO_NAME=context.video_stream.name)

    if not html_filename.lower().endswith(".html"):
        html_filename += ".html"
    html_path = get_and_create_path(html_filename, output_dir)
    logger.info("Exporting to html file:\n %s:", html_path)
    scene_manager.write_scene_list_html(
        output_html_filename=html_path,
        scene_list=scenes,
        cut_list=cuts,
        image_filenames=save_images_result[0],
        image_width=image_width,
        image_height=image_height,
    )


def split_video(
    context: CliContext,
    scenes: SceneList,
    name_format: str,
    use_mkvmerge: bool,
    output_dir: str,
    show_output: bool,
    ffmpeg_args: str,
    **kwargs,
):
    """Handles the `split-video` command."""
    # Add proper extension to filename template if required.
    dot_pos = name_format.rfind(".")
    extension_length = 0 if dot_pos < 0 else len(name_format) - (dot_pos + 1)
    # If using mkvmerge, force extension to .mkv.
    if use_mkvmerge and not name_format.endswith(".mkv"):
        name_format += ".mkv"
    # Otherwise, if using ffmpeg, only add an extension if one doesn't exist.
    elif not 2 <= extension_length <= 4:
        name_format += ".mp4"
    if use_mkvmerge:
        split_video_mkvmerge(
            input_video_path=context.video_stream.path,
            scene_list=scenes,
            output_dir=output_dir,
            output_file_template=name_format,
            show_output=show_output,
        )
    else:
        split_video_ffmpeg(
            input_video_path=context.video_stream.path,
            scene_list=scenes,
            output_dir=output_dir,
            output_file_template=name_format,
            arg_override=ffmpeg_args,
            show_progress=not context.quiet_mode,
            show_output=show_output,
        )
    if scenes:
        logger.info("Video splitting completed, scenes written to disk.")
