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
import logging
import typing as ty

from scenedetect._thirdparty.simpletable import (
    HTMLPage,
    SimpleTable,
    SimpleTableCell,
    SimpleTableImage,
    SimpleTableRow,
)
from scenedetect.common import (
    CutList,
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
    cut_list: ty.Optional[CutList] = None,
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
            ["Timecode List:"] + cut_list
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
                "%d" % (i + 1),
                "%d" % (start.get_frames() + 1),
                start.get_timecode(),
                "%.3f" % start.get_seconds(),
                "%d" % end.get_frames(),
                end.get_timecode(),
                "%.3f" % end.get_seconds(),
                "%d" % duration.get_frames(),
                duration.get_timecode(),
                "%.3f" % duration.get_seconds(),
            ]
        )


def write_scene_list_html(
    output_html_filename: str,
    scene_list: SceneList,
    cut_list: ty.Optional[CutList] = None,
    css: str = None,
    css_class: str = "mytable",
    image_filenames: ty.Optional[ty.Dict[int, ty.List[str]]] = None,
    image_width: ty.Optional[int] = None,
    image_height: ty.Optional[int] = None,
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
                "%d" % (i + 1),
                "%d" % (start.get_frames() + 1),
                start.get_timecode(),
                "%.3f" % start.get_seconds(),
                "%d" % end.get_frames(),
                end.get_timecode(),
                "%.3f" % end.get_seconds(),
                "%d" % duration.get_frames(),
                duration.get_timecode(),
                "%.3f" % duration.get_seconds(),
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
