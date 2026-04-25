#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#

"""The ``scenedetect.output`` module contains functions which can be used to generate output
based on the output of scene detection. This includes saving images for each scene, exporting to
CSV/HTML, or splitting the input video into individual shots.
"""

import csv
import json
import logging
import typing as ty
from fractions import Fraction
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree

from scenedetect._thirdparty.simpletable import (
    HTMLPage,
    SimpleTable,
    SimpleTableCell,
    SimpleTableImage,
    SimpleTableRow,
)
from scenedetect.common import (
    CutList,
    FrameTimecode,
    SceneList,
)

# Commonly used classes/functions exported under the `scenedetect.output` namespace for brevity.
from scenedetect.output.image import save_images
from scenedetect.output.video import (
    PathFormatter,
    SceneMetadata,
    VideoMetadata,
    default_formatter,
    is_ffmpeg_available,
    is_mkvmerge_available,
    split_video_ffmpeg,
    split_video_mkvmerge,
)

logger = logging.getLogger("pyscenedetect")


def write_scene_list(
    output_csv_file: ty.TextIO,
    scene_list: SceneList,
    include_cut_list: bool = True,
    cut_list: CutList | None = None,
    col_separator: str = ",",
    row_separator: str = "\n",
):
    """Writes the given list of scenes to an output file handle in CSV format.

    Arguments:
        output_csv_file: Handle to open file in write mode.
        scene_list: List of pairs of FrameTimecodes denoting each scene's start/end FrameTimecode.
        include_cut_list: Bool indicating if the first row should include the timecodes where
            each scene starts. Should be set to False if RFC 4180 compliant CSV output is required.
        cut_list: Optional list of FrameTimecode objects denoting the cut list (i.e. the frames
            in the video that need to be split to generate individual scenes). If not specified,
            the cut list is generated using the start times of each scene following the first one.
        col_separator: Delimiter to use between values. Must be single character.
        row_separator: Line terminator to use between rows.

    Raises:
        TypeError: "delimiter" must be a 1-character string
    """
    csv_writer = csv.writer(output_csv_file, delimiter=col_separator, lineterminator=row_separator)
    # If required, output the cutting list as the first row (i.e. before the header row).
    if include_cut_list:
        csv_writer.writerow(
            ["Timecode List:", *cut_list]
            if cut_list
            else [start.get_timecode() for start, _ in scene_list[1:]]
        )
    csv_writer.writerow(
        [
            "Scene Number",
            "Start Frame",
            "Start Timecode",
            "Start Time (seconds)",
            "End Frame",
            "End Timecode",
            "End Time (seconds)",
            "Length (frames)",
            "Length (timecode)",
            "Length (seconds)",
        ]
    )
    for i, (start, end) in enumerate(scene_list):
        duration = end - start
        csv_writer.writerow(
            [
                f"{i + 1:d}",
                f"{start.frame_num + 1:d}",
                start.get_timecode(),
                f"{start.seconds:.3f}",
                f"{end.frame_num:d}",
                end.get_timecode(),
                f"{end.seconds:.3f}",
                f"{duration.frame_num:d}",
                duration.get_timecode(),
                f"{duration.seconds:.3f}",
            ]
        )


def write_scene_list_html(
    output_html_filename: str,
    scene_list: SceneList,
    cut_list: CutList | None = None,
    css: str | None = None,
    css_class: str = "mytable",
    image_filenames: dict[int, list[str]] | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
):
    """Writes the given list of scenes to an output file handle in html format.

    Arguments:
        output_html_filename: filename of output html file
        scene_list: List of pairs of FrameTimecodes denoting each scene's start/end FrameTimecode.
        cut_list: Optional list of FrameTimecode objects denoting the cut list (i.e. the frames
            in the video that need to be split to generate individual scenes). If not passed,
            the start times of each scene (besides the 0th scene) is used instead.
        css: String containing all the css information for the resulting html page.
        css_class: String containing the named css class
        image_filenames: dict where key i contains a list with n elements (filenames of
            the n saved images from that scene)
        image_width: Optional desired width of images in table in pixels
        image_height: Optional desired height of images in table in pixels
    """
    logger.info("Exporting scenes to html:\n %s:", output_html_filename)
    if not css:
        css = """
        table.mytable {
            font-family: times;
            font-size:12px;
            color:#000000;
            border-width: 1px;
            border-color: #eeeeee;
            border-collapse: collapse;
            background-color: #ffffff;
            width=100%;
            max-width:550px;
            table-layout:fixed;
        }
        table.mytable th {
            border-width: 1px;
            padding: 8px;
            border-style: solid;
            border-color: #eeeeee;
            background-color: #e6eed6;
            color:#000000;
        }
        table.mytable td {
            border-width: 1px;
            padding: 8px;
            border-style: solid;
            border-color: #eeeeee;
        }
        #code {
            display:inline;
            font-family: courier;
            color: #3d9400;
        }
        #string {
            display:inline;
            font-weight: bold;
        }
        """

    # Output Timecode list
    timecode_table = SimpleTable(
        [
            ["Timecode List:"]
            + (cut_list if cut_list else [start.get_timecode() for start, _ in scene_list[1:]])
        ],
        css_class=css_class,
    )

    # Output list of scenes
    header_row = [
        "Scene Number",
        "Start Frame",
        "Start Timecode",
        "Start Time (seconds)",
        "End Frame",
        "End Timecode",
        "End Time (seconds)",
        "Length (frames)",
        "Length (timecode)",
        "Length (seconds)",
    ]
    for i, (start, end) in enumerate(scene_list):
        duration = end - start

        row = SimpleTableRow(
            [
                f"{i + 1:d}",
                f"{start.frame_num + 1:d}",
                start.get_timecode(),
                f"{start.seconds:.3f}",
                f"{end.frame_num:d}",
                end.get_timecode(),
                f"{end.seconds:.3f}",
                f"{duration.frame_num:d}",
                duration.get_timecode(),
                f"{duration.seconds:.3f}",
            ]
        )

        if image_filenames:
            for image in image_filenames[i]:
                row.add_cell(
                    SimpleTableCell(SimpleTableImage(image, width=image_width, height=image_height))
                )

        if i == 0:
            scene_table = SimpleTable(rows=[row], header_row=header_row, css_class=css_class)
        else:
            scene_table.add_row(row=row)

    # Write html file
    page = HTMLPage()
    page.add_table(timecode_table)
    page.add_table(scene_table)
    page.css = css
    page.save(output_html_filename)


def _edl_timecode(timecode: FrameTimecode) -> str:
    """Format `timecode` as ``HH:MM:SS:FF`` for a CMX 3600 EDL entry."""
    total_seconds = timecode.seconds
    framerate = timecode.framerate
    assert framerate is not None
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    frames_part = int((total_seconds * framerate) % framerate)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames_part:02d}"


def write_scene_list_edl(
    output_path: str | Path,
    scene_list: SceneList,
    title: str = "PySceneDetect",
    reel: str = "AX",
):
    """Writes the given list of scenes to `output_path` in CMX 3600 EDL format.

    Arguments:
        output_path: Path to write the EDL file to. Parent directories must exist.
        scene_list: List of scenes as pairs of FrameTimecodes denoting each scene's start/end.
        title: Title header written as ``TITLE:`` in the EDL.
        reel: Reel name used for each event. Typically 2-8 uppercase characters.
    """
    output_path = Path(output_path)
    lines = [f"TITLE: {title}", "FCM: NON-DROP FRAME", ""]
    for i, (start, end) in enumerate(scene_list):
        in_tc = _edl_timecode(start)
        out_tc = _edl_timecode(end)
        lines.append(f"{(i + 1):03d}  {reel} V     C        {in_tc} {out_tc} {in_tc} {out_tc}")
    logger.info("Writing scenes in EDL format to %s", output_path)
    with open(output_path, "w") as f:
        # `scenedetect` is imported lazily to avoid a circular import at module load.
        import scenedetect

        f.write(f"* CREATED WITH PYSCENEDETECT {scenedetect.__version__}\n")
        f.write("\n".join(lines))
        f.write("\n")


def _rational_seconds(value: Fraction) -> str:
    """Format a `Fraction` as an FCPXML rational time string.

    FCPXML expresses time as ``<num>/<denom>s`` (or ``<int>s`` for whole seconds). See
    https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference
    """
    if value.denominator == 1:
        return f"{value.numerator}s"
    return f"{value.numerator}/{value.denominator}s"


def _frame_timecode_seconds(tc: FrameTimecode) -> Fraction:
    """Exact seconds for `tc` as a `Fraction`, derived from PTS * time base."""
    return Fraction(tc.pts) * tc.time_base


def write_scene_list_fcpx(
    output_path: str | Path,
    scene_list: SceneList,
    video_path: str | Path,
    frame_rate: Fraction,
    frame_size: tuple[int, int],
    video_name: str | None = None,
):
    """Writes the given list of scenes to `output_path` in Final Cut Pro X XML format (FCPXML 1.9).

    The output follows Apple's FCPXML schema with rational-second time values and a custom
    ``<format>`` derived from the source video's frame rate and resolution. See
    https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference

    Arguments:
        output_path: Path to write the FCPXML file to. Parent directories must exist.
        scene_list: List of scenes as pairs of FrameTimecodes. Must not be empty.
        video_path: Path to the source video file; written into the output as a ``file://`` URI.
        frame_rate: Source frame rate as a rational `Fraction` (e.g. ``Fraction(24000, 1001)``).
        frame_size: Source resolution as a ``(width, height)`` tuple in pixels.
        video_name: Display name used for the asset, project, and event. Defaults to the stem
            of `video_path`.
    """
    assert scene_list
    output_path = Path(output_path)
    video_path = Path(video_path)
    if video_name is None:
        video_name = video_path.stem

    ASSET_ID = "r2"
    FORMAT_ID = "r1"

    width, height = frame_size
    frame_duration = _rational_seconds(Fraction(frame_rate.denominator, frame_rate.numerator))
    src_uri = video_path.absolute().as_uri()
    total_duration = _rational_seconds(
        _frame_timecode_seconds(scene_list[-1][1] - scene_list[0][0])
    )

    root = ElementTree.Element("fcpxml", version="1.9")
    resources = ElementTree.SubElement(root, "resources")
    # `name` is cosmetic: Apple publishes no authoritative FFVideoFormat* list, and editors key
    # off frameDuration/width/height. We emit a generated name for display only.
    format_name = f"FFVideoFormat{height}p{round(float(frame_rate) * 100):04d}"
    ElementTree.SubElement(
        resources,
        "format",
        id=FORMAT_ID,
        name=format_name,
        frameDuration=frame_duration,
        width=str(width),
        height=str(height),
    )
    asset = ElementTree.SubElement(
        resources,
        "asset",
        id=ASSET_ID,
        name=video_name,
        start="0s",
        duration=total_duration,
        hasVideo="1",
        format=FORMAT_ID,
    )
    ElementTree.SubElement(asset, "media-rep", kind="original-media", src=src_uri)

    library = ElementTree.SubElement(root, "library")
    event = ElementTree.SubElement(library, "event", name=video_name)
    project = ElementTree.SubElement(event, "project", name=video_name)
    sequence = ElementTree.SubElement(
        project,
        "sequence",
        format=FORMAT_ID,
        duration=total_duration,
        tcStart="0s",
        tcFormat="NDF",
    )
    spine = ElementTree.SubElement(sequence, "spine")

    for i, (start, end) in enumerate(scene_list):
        scene_start = _rational_seconds(_frame_timecode_seconds(start))
        scene_duration = _rational_seconds(_frame_timecode_seconds(end - start))
        ElementTree.SubElement(
            spine,
            "asset-clip",
            name=f"Shot {i + 1}",
            ref=ASSET_ID,
            offset=scene_start,
            start=scene_start,
            duration=scene_duration,
        )

    pretty_xml = minidom.parseString(ElementTree.tostring(root, encoding="unicode")).toprettyxml(
        indent="  "
    )
    logger.info("Writing scenes in FCPX format to %s", output_path)
    with open(output_path, "w") as f:
        f.write(pretty_xml)


def write_scene_list_fcp7(
    output_path: str | Path,
    scene_list: SceneList,
    video_path: str | Path,
    frame_rate: Fraction,
    frame_size: tuple[int, int],
    video_name: str | None = None,
    source_duration: FrameTimecode | None = None,
):
    """Writes the given list of scenes to `output_path` in Final Cut Pro 7 XML (xmeml) format.

    See the xmeml element reference at
    https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/FinalCutPro_XML/.
    ``pathurl`` is written as a valid ``file://`` URI per the xmeml spec.

    Arguments:
        output_path: Path to write the xmeml file to. Parent directories must exist.
        scene_list: List of scenes as pairs of FrameTimecodes. Must not be empty.
        video_path: Path to the source video file; written into the output as a ``file://`` URI.
        frame_rate: Source frame rate as a rational `Fraction`.
        frame_size: Source resolution as a ``(width, height)`` tuple in pixels.
        video_name: Display name used for project and sequence. Defaults to the stem of
            `video_path`.
        source_duration: Total duration of the source media. Required on ``<file>`` so NLEs
            (DaVinci Resolve, Premiere) can seek into the source — without it the clip plays
            frozen. If None, falls back to the last scene's end time.
    """
    assert scene_list
    output_path = Path(output_path)
    video_path = Path(video_path)
    if video_name is None:
        video_name = video_path.stem

    root = ElementTree.Element("xmeml", version="5")
    project = ElementTree.SubElement(root, "project")
    ElementTree.SubElement(project, "name").text = video_name
    sequence = ElementTree.SubElement(project, "sequence")
    ElementTree.SubElement(sequence, "name").text = video_name

    fps = float(frame_rate)
    ntsc = "True" if frame_rate.denominator != 1 else "False"
    duration = scene_list[-1][1] - scene_list[0][0]
    ElementTree.SubElement(sequence, "duration").text = str(round(duration.seconds * fps))

    rate = ElementTree.SubElement(sequence, "rate")
    ElementTree.SubElement(rate, "timebase").text = str(round(fps))
    ElementTree.SubElement(rate, "ntsc").text = ntsc

    timecode = ElementTree.SubElement(sequence, "timecode")
    tc_rate = ElementTree.SubElement(timecode, "rate")
    ElementTree.SubElement(tc_rate, "timebase").text = str(round(fps))
    ElementTree.SubElement(tc_rate, "ntsc").text = ntsc
    ElementTree.SubElement(timecode, "frame").text = "0"
    ElementTree.SubElement(timecode, "displayformat").text = "NDF"

    width, height = frame_size
    media = ElementTree.SubElement(sequence, "media")
    video = ElementTree.SubElement(media, "video")
    format = ElementTree.SubElement(video, "format")
    sample_chars = ElementTree.SubElement(format, "samplecharacteristics")
    ElementTree.SubElement(sample_chars, "width").text = str(width)
    ElementTree.SubElement(sample_chars, "height").text = str(height)
    track = ElementTree.SubElement(video, "track")

    path_uri = video_path.absolute().as_uri()
    source_duration_frames = str(
        round(
            (source_duration.seconds if source_duration is not None else scene_list[-1][1].seconds)
            * fps
        )
    )
    FILE_ID = "file1"

    for i, (start, end) in enumerate(scene_list):
        clip = ElementTree.SubElement(track, "clipitem")
        ElementTree.SubElement(clip, "name").text = f"Shot {i + 1}"
        ElementTree.SubElement(clip, "enabled").text = "TRUE"
        ElementTree.SubElement(clip, "duration").text = source_duration_frames
        clip_rate = ElementTree.SubElement(clip, "rate")
        ElementTree.SubElement(clip_rate, "timebase").text = str(round(fps))
        ElementTree.SubElement(clip_rate, "ntsc").text = ntsc
        # Frame numbers relative to the declared <timebase> fps, computed from PTS seconds.
        ElementTree.SubElement(clip, "start").text = str(round(start.seconds * fps))
        ElementTree.SubElement(clip, "end").text = str(round(end.seconds * fps))
        ElementTree.SubElement(clip, "in").text = str(round(start.seconds * fps))
        ElementTree.SubElement(clip, "out").text = str(round(end.seconds * fps))

        # xmeml allows a single full `<file>` declaration reused via `<file id="...">` on
        # subsequent clipitems. Emit full details on the first, then self-close on the rest.
        if i == 0:
            file_ref = ElementTree.SubElement(clip, "file", id=FILE_ID)
            ElementTree.SubElement(file_ref, "name").text = video_name
            ElementTree.SubElement(file_ref, "pathurl").text = path_uri
            ElementTree.SubElement(file_ref, "duration").text = source_duration_frames
            file_rate = ElementTree.SubElement(file_ref, "rate")
            ElementTree.SubElement(file_rate, "timebase").text = str(round(fps))
            ElementTree.SubElement(file_rate, "ntsc").text = ntsc
            media_ref = ElementTree.SubElement(file_ref, "media")
            video_ref = ElementTree.SubElement(media_ref, "video")
            clip_chars = ElementTree.SubElement(video_ref, "samplecharacteristics")
            ElementTree.SubElement(clip_chars, "width").text = str(width)
            ElementTree.SubElement(clip_chars, "height").text = str(height)
        else:
            ElementTree.SubElement(clip, "file", id=FILE_ID)

        link = ElementTree.SubElement(clip, "link")
        ElementTree.SubElement(link, "linkclipref").text = FILE_ID
        ElementTree.SubElement(link, "mediatype").text = "video"

    pretty_xml = minidom.parseString(ElementTree.tostring(root, encoding="unicode")).toprettyxml(
        indent="  "
    )
    logger.info("Writing scenes in FCP format to %s", output_path)
    with open(output_path, "w") as f:
        f.write(pretty_xml)


# TODO: We have to export framerate as a float for OTIO's current format. When OTIO supports
# fractional timecodes, we should export the framerate as a rational number instead.
# https://github.com/AcademySoftwareFoundation/OpenTimelineIO/issues/190
def write_scene_list_otio(
    output_path: str | Path,
    scene_list: SceneList,
    video_path: str | Path,
    frame_rate: Fraction,
    name: str | None = None,
    audio: bool = True,
):
    """Writes the given list of scenes to `output_path` as an OTIO Timeline.1 JSON document.

    OTIO (OpenTimelineIO) timelines can be imported by many video editors.

    Arguments:
        output_path: Path to write the OTIO file to. Parent directories must exist.
        scene_list: List of scenes as pairs of FrameTimecodes.
        video_path: Path to the source video file; written into the output as an absolute path.
        frame_rate: Source frame rate as a rational `Fraction`. Exported as a float, as the
            current OTIO format does not support rational timings.
        name: Timeline name. Defaults to the stem of `video_path`.
        audio: If True (default), include an audio track alongside the video track.
    """
    output_path = Path(output_path)
    video_path = Path(video_path)
    if name is None:
        name = video_path.stem

    video_base_name = video_path.name
    video_abs_path = str(video_path.absolute())
    fps = float(frame_rate)

    # List of track mapping to resource type.
    # TODO(https://scenedetect.com/issues/497): Allow OTIO export without an audio track.
    track_list = {"Video 1": "Video"}
    if audio:
        track_list["Audio 1"] = "Audio"

    otio = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": name,
        "global_start_time": {
            "OTIO_SCHEMA": "RationalTime.1",
            "rate": fps,
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
                                    "rate": fps,
                                    "value": round((end - start).seconds * fps, 6),
                                },
                                "start_time": {
                                    "OTIO_SCHEMA": "RationalTime.1",
                                    "rate": fps,
                                    "value": round(start.seconds * fps, 6),
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
                                            "rate": fps,
                                            "value": 1980.0,
                                        },
                                        "start_time": {
                                            "OTIO_SCHEMA": "RationalTime.1",
                                            "rate": fps,
                                            "value": 0.0,
                                        },
                                    },
                                    "available_image_bounds": None,
                                    "target_url": video_abs_path,
                                }
                            },
                            "active_media_reference_key": "DEFAULT_MEDIA",
                        }
                        for (start, end) in scene_list
                    ],
                    "kind": track_type,
                }
                for (track_name, track_type) in track_list.items()
            ],
        },
    }

    logger.info("Writing scenes in OTIO format to %s", output_path)
    with open(output_path, "w") as f:
        json.dump(otio, f, indent=4)
        f.write("\n")
