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
"""Logic for PySceneDetect commands that operate on the result of the processing pipeline.

In addition to the the arguments registered with the command, commands will be called with the
current command-line context, as well as the processing result (scenes and cuts).
"""

import json
import logging
import os.path
import typing as ty
import webbrowser
from datetime import datetime
from pathlib import Path
from string import Template
from xml.dom import minidom
from xml.etree import ElementTree

import scenedetect
from scenedetect._cli.config import XmlFormat
from scenedetect._cli.context import CliContext
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.platform import get_and_create_path
from scenedetect.scene_manager import (
    CutList,
    Interpolation,
    SceneList,
    write_scene_list,
    write_scene_list_html,
)
from scenedetect.scene_manager import save_images as save_images_impl
from scenedetect.video_splitter import split_video_ffmpeg, split_video_mkvmerge

logger = logging.getLogger("pyscenedetect")


def save_html(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    image_width: int,
    image_height: int,
    filename: str,
    no_images: bool,
    show: bool,
):
    """Handles the `save-html` command."""
    (image_filenames, output) = (
        context.save_images_result
        if context.save_images_result is not None
        else (None, context.output)
    )

    html_filename = Template(filename).safe_substitute(VIDEO_NAME=context.video_stream.name)
    if not html_filename.lower().endswith(".html"):
        html_filename += ".html"
    html_path = get_and_create_path(html_filename, output)
    write_scene_list_html(
        output_html_filename=html_path,
        scene_list=scenes,
        cut_list=cuts,
        image_filenames=None if no_images else image_filenames,
        image_width=image_width,
        image_height=image_height,
    )
    if show:
        webbrowser.open(html_path)


def save_qp(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    output: str,
    filename: str,
    disable_shift: bool,
):
    """Handler for the `save-qp` command."""
    del scenes  # We only use cuts for this handler.
    qp_path = get_and_create_path(
        Template(filename).safe_substitute(VIDEO_NAME=context.video_stream.name),
        output,
    )
    start_frame = context.start_time.frame_num if context.start_time else 0
    shift_start = not disable_shift
    offset = start_frame if shift_start else 0
    with open(qp_path, "wt") as qp_file:
        qp_file.write(f"{0 if shift_start else start_frame} I -1\n")
        # Place another I frame at each detected cut.
        qp_file.writelines(f"{cut.frame_num - offset} I -1\n" for cut in cuts)
    logger.info(f"QP file written to: {qp_path}")


def list_scenes(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    no_output_file: bool,
    filename: str,
    output: str,
    skip_cuts: bool,
    quiet: bool,
    display_scenes: bool,
    display_cuts: bool,
    cut_format: str,
    col_separator: str,
    row_separator: str,
):
    """Handles the `list-scenes` command."""
    # Write scene list CSV to if required.
    if not no_output_file:
        scene_list_filename = Template(filename).safe_substitute(
            VIDEO_NAME=context.video_stream.name
        )
        if not scene_list_filename.lower().endswith(".csv"):
            scene_list_filename += ".csv"
        scene_list_path = get_and_create_path(
            scene_list_filename,
            output,
        )
        logger.info("Writing scene list to CSV file:\n  %s", scene_list_path)
        with open(scene_list_path, "w") as scene_list_file:
            write_scene_list(
                output_csv_file=scene_list_file,
                scene_list=scenes,
                include_cut_list=not skip_cuts,
                cut_list=cuts,
                col_separator=col_separator,
                row_separator=row_separator,
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
    cuts: CutList,
    num_images: int,
    frame_margin: int,
    image_extension: str,
    encoder_param: int,
    filename: str,
    output: ty.Optional[str],
    show_progress: bool,
    scale: int,
    height: int,
    width: int,
    interpolation: Interpolation,
    threading: bool,
):
    """Handles the `save-images` command."""
    del cuts  # save-images only uses scenes.

    images = save_images_impl(
        scene_list=scenes,
        video=context.video_stream,
        num_images=num_images,
        frame_margin=frame_margin,
        image_extension=image_extension,
        encoder_param=encoder_param,
        image_name_template=filename,
        output_dir=output,
        show_progress=show_progress,
        scale=scale,
        height=height,
        width=width,
        interpolation=interpolation,
        threading=threading,
    )
    # Save the result for use by `save-html` if required.
    context.save_images_result = (images, output)


def split_video(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    name_format: str,
    use_mkvmerge: bool,
    output: str,
    show_output: bool,
    ffmpeg_args: str,
):
    """Handles the `split-video` command."""
    del cuts  # split-video only uses scenes.

    if use_mkvmerge:
        name_format = name_format.removesuffix("-$SCENE_NUMBER")

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
            output_dir=output,
            output_file_template=name_format,
            show_output=show_output,
        )
    else:
        split_video_ffmpeg(
            input_video_path=context.video_stream.path,
            scene_list=scenes,
            output_dir=output,
            output_file_template=name_format,
            arg_override=ffmpeg_args,
            show_progress=not context.quiet_mode,
            show_output=show_output,
        )
    if scenes:
        logger.info("Video splitting completed, scenes written to disk.")


def save_edl(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    filename: str,
    output: str,
    title: str,
    reel: str,
):
    """Handles the `save-edl` command. Outputs in CMX 3600 format."""
    # We only use scene information.
    del cuts

    # Converts FrameTimecode to HH:MM:SS:FF
    # TODO: This should be part of the FrameTimecode object itself.
    def get_edl_timecode(timecode: FrameTimecode):
        total_seconds = timecode.get_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frames_part = int((total_seconds * timecode.get_framerate()) % timecode.get_framerate())
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames_part:02d}"

    edl_content = []

    title = Template(title).safe_substitute(VIDEO_NAME=context.video_stream.name)
    edl_content.append(f"TITLE: {title}")
    edl_content.append("FCM: NON-DROP FRAME")
    edl_content.append("")

    # Add each shot as an edit entry
    for i, (start, end) in enumerate(scenes):
        in_tc = get_edl_timecode(start)
        out_tc = get_edl_timecode(end - 1)  # Correct for presentation time
        # Format the edit entry according to CMX 3600 format
        event_line = f"{(i + 1):03d}  {reel} V     C        {in_tc} {out_tc} {in_tc} {out_tc}"
        edl_content.append(event_line)

    edl_path = get_and_create_path(
        Template(filename).safe_substitute(VIDEO_NAME=context.video_stream.name),
        output,
    )
    logger.info(f"Writing scenes in EDL format to {edl_path}")
    with open(edl_path, "w") as f:
        f.write(f"* CREATED WITH PYSCENEDETECT {scenedetect.__version__}\n")
        f.write("\n".join(edl_content))
        f.write("\n")


def _save_xml_fcpx(
    context: CliContext,
    scenes: SceneList,
    filename: str,
    output: str,
):
    """Saves scenes in Final Cut Pro X XML format."""
    ASSET_ID = "asset1"
    FORMAT_ID = "format1"
    # TODO: Need to handle other video formats!
    VIDEO_FORMAT_TODO_HANDLE_OTHERS = "FFVideoFormat1080p24"

    root = ElementTree.Element("fcpxml", version="1.9")
    resources = ElementTree.SubElement(root, "resources")
    ElementTree.SubElement(resources, "format", id="format1", name=VIDEO_FORMAT_TODO_HANDLE_OTHERS)

    video_name = context.video_stream.name

    # TODO: We should calculate duration from the scene list.
    duration = context.video_stream.duration
    duration = str(duration.get_seconds()) + "s"  # TODO: Is float okay here?
    path = Path(context.video_stream.path).absolute()
    ElementTree.SubElement(
        resources,
        "asset",
        id=ASSET_ID,
        name=video_name,
        src=str(path),
        duration=duration,
        hasVideo="1",
        hasAudio="1",  # TODO: Handle case of no audio.
        format=FORMAT_ID,
    )

    library = ElementTree.SubElement(root, "library")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event = ElementTree.SubElement(library, "event", name=f"Shot Detection {now}")
    project = ElementTree.SubElement(
        event, "project", name=video_name
    )  # TODO: Allow customizing project name.
    sequence = ElementTree.SubElement(project, "sequence", format=FORMAT_ID, duration=duration)
    spine = ElementTree.SubElement(sequence, "spine")

    for i, (start, end) in enumerate(scenes):
        start_seconds = start.get_seconds()
        duration_seconds = (end - start).get_seconds()
        clip = ElementTree.SubElement(
            spine,
            "clip",
            name=f"Shot {i + 1}",
            duration=f"{duration_seconds:.3f}s",
            start=f"{start_seconds:.3f}s",
            offset=f"{start_seconds:.3f}s",
        )
        ElementTree.SubElement(
            clip,
            "asset-clip",
            ref=ASSET_ID,
            duration=f"{duration_seconds:.3f}s",
            start=f"{start_seconds:.3f}s",
            offset="0s",
            name=f"Shot {i + 1}",
        )

    pretty_xml = minidom.parseString(ElementTree.tostring(root, encoding="unicode")).toprettyxml(
        indent="  "
    )
    xml_path = get_and_create_path(
        Template(filename).safe_substitute(VIDEO_NAME=context.video_stream.name),
        output,
    )
    logger.info(f"Writing scenes in FCPX format to {xml_path}")
    with open(xml_path, "w") as f:
        f.write(pretty_xml)


def _save_xml_fcp(
    context: CliContext,
    scenes: SceneList,
    filename: str,
    output: str,
):
    """Saves scenes in Final Cut Pro 7 XML format."""
    assert scenes
    root = ElementTree.Element("xmeml", version="5")
    project = ElementTree.SubElement(root, "project")
    ElementTree.SubElement(project, "name").text = context.video_stream.name
    sequence = ElementTree.SubElement(project, "sequence")
    ElementTree.SubElement(sequence, "name").text = context.video_stream.name

    duration = scenes[-1][1] - scenes[0][0]
    ElementTree.SubElement(sequence, "duration").text = f"{duration.get_frames()}"

    rate = ElementTree.SubElement(sequence, "rate")
    ElementTree.SubElement(rate, "timebase").text = str(context.video_stream.frame_rate)
    ElementTree.SubElement(rate, "ntsc").text = "False"

    timecode = ElementTree.SubElement(sequence, "timecode")
    tc_rate = ElementTree.SubElement(timecode, "rate")
    ElementTree.SubElement(tc_rate, "timebase").text = str(context.video_stream.frame_rate)
    ElementTree.SubElement(tc_rate, "ntsc").text = "False"
    ElementTree.SubElement(timecode, "frame").text = "0"
    ElementTree.SubElement(timecode, "displayformat").text = "NDF"

    media = ElementTree.SubElement(sequence, "media")
    video = ElementTree.SubElement(media, "video")
    format = ElementTree.SubElement(video, "format")
    ElementTree.SubElement(format, "samplecharacteristics")
    track = ElementTree.SubElement(video, "track")

    # Add clips for each shot boundary
    for i, (start, end) in enumerate(scenes):
        clip = ElementTree.SubElement(track, "clipitem")
        ElementTree.SubElement(clip, "name").text = f"Shot {i + 1}"
        ElementTree.SubElement(clip, "enabled").text = "TRUE"
        ElementTree.SubElement(clip, "rate").append(
            ElementTree.fromstring(f"<timebase>{context.video_stream.frame_rate}</timebase>")
        )
        # TODO: Are these supposed to be frame numbers or another format?
        ElementTree.SubElement(clip, "start").text = str(start.get_frames())
        ElementTree.SubElement(clip, "end").text = str(end.get_frames())
        ElementTree.SubElement(clip, "in").text = str(start.get_frames())
        ElementTree.SubElement(clip, "out").text = str(end.get_frames())

        file_ref = ElementTree.SubElement(clip, "file", id=f"file{i + 1}")
        ElementTree.SubElement(file_ref, "name").text = context.video_stream.name
        path = Path(context.video_stream.path).absolute()
        # TODO: Can we just use path.as_uri() here?
        # On Windows this should be: file://localhost/C:/Users/... according to the samples provided
        # from https://github.com/Breakthrough/PySceneDetect/issues/156#issuecomment-1076213412.
        ElementTree.SubElement(file_ref, "pathurl").text = f"file://{path}"

        media_ref = ElementTree.SubElement(file_ref, "media")
        video_ref = ElementTree.SubElement(media_ref, "video")
        ElementTree.SubElement(video_ref, "samplecharacteristics")
        link = ElementTree.SubElement(clip, "link")
        ElementTree.SubElement(link, "linkclipref").text = f"file{i + 1}"
        ElementTree.SubElement(link, "mediatype").text = "video"

    pretty_xml = minidom.parseString(ElementTree.tostring(root, encoding="unicode")).toprettyxml(
        indent="  "
    )
    xml_path = get_and_create_path(
        Template(filename).safe_substitute(VIDEO_NAME=context.video_stream.name),
        output,
    )
    logger.info(f"Writing scenes in FCP format to {xml_path}")
    with open(xml_path, "w") as f:
        f.write(pretty_xml)


def save_xml(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    filename: str,
    format: XmlFormat,
    output: str,
):
    """Handles the `save-xml` command."""
    # We only use scene information.
    del cuts

    if not scenes:
        return

    if format == XmlFormat.FCPX:
        _save_xml_fcpx(context, scenes, filename, output)
    elif format == XmlFormat.FCP:
        _save_xml_fcp(context, scenes, filename, output)
    else:
        logger.error(f"Unknown format: {format}")


def save_otio(
    context: CliContext,
    scenes: SceneList,
    cuts: CutList,
    filename: str,
    output: str,
    name: str,
):
    """Saves scenes in OTIO format."""

    del cuts  # We only use scene information

    video_name = context.video_stream.name
    video_path = os.path.abspath(context.video_stream.path)
    video_base_name = os.path.basename(context.video_stream.path)
    frame_rate = context.video_stream.frame_rate

    # List of track mapping to resource type.
    # TODO(#497): Allow exporting without an audio track.
    track_list = {"Video 1": "Video", "Audio 1": "Audio"}

    otio = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": Template(name).safe_substitute(VIDEO_NAME=video_name),
        "global_start_time": {
            "OTIO_SCHEMA": "RationalTime.1",
            "rate": frame_rate,
            "value": 0.0,
        },
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "enabled": True,
            "children": [
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": track_name,
                    "enabled": True,
                    "children": [
                        {
                            "OTIO_SCHEMA": "Clip.2",
                            "name": video_base_name,
                            "source_range": {
                                "OTIO_SCHEMA": "TimeRange.1",
                                "duration": {
                                    "OTIO_SCHEMA": "RationalTime.1",
                                    "rate": frame_rate,
                                    "value": float((end - start).get_frames()),
                                },
                                "start_time": {
                                    "OTIO_SCHEMA": "RationalTime.1",
                                    "rate": frame_rate,
                                    "value": float(start.get_frames()),
                                },
                            },
                            "enabled": True,
                            "media_references": {
                                "DEFAULT_MEDIA": {
                                    "OTIO_SCHEMA": "ExternalReference.1",
                                    "name": video_base_name,
                                    "available_range": {
                                        "OTIO_SCHEMA": "TimeRange.1",
                                        "duration": {
                                            "OTIO_SCHEMA": "RationalTime.1",
                                            "rate": frame_rate,
                                            "value": 1980.0,
                                        },
                                        "start_time": {
                                            "OTIO_SCHEMA": "RationalTime.1",
                                            "rate": frame_rate,
                                            "value": 0.0,
                                        },
                                    },
                                    "available_image_bounds": None,
                                    "target_url": video_path,
                                }
                            },
                            "active_media_reference_key": "DEFAULT_MEDIA",
                        }
                        for (start, end) in scenes
                    ],
                    "kind": track_type,
                }
                for (track_name, track_type) in track_list.items()
            ],
        },
    }

    otio_path = get_and_create_path(
        Template(filename).safe_substitute(VIDEO_NAME=context.video_stream.name),
        output,
    )
    logger.info(f"Writing scenes in OTIO format to {otio_path}")
    with open(otio_path, "w") as f:
        json.dump(otio, f, indent=4)
        f.write("\n")
