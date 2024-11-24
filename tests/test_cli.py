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

import glob
import os
import subprocess
import typing as ty
from pathlib import Path

import cv2
import numpy as np
import pytest

from scenedetect.video_splitter import is_ffmpeg_available, is_mkvmerge_available

# These tests validate that the CLI itself functions correctly, mainly based on the return
# return code from the process. We do not yet check for correctness of the output, just a
# successful invocation of the command (i.e. no exceptions/errors).

# TODO: Add some basic correctness tests to validate the output (just look for the
# last expected log message or extract # of scenes). Might need to refactor the test cases
# since we need to calculate the output file names for commands that write to disk.

# TODO: Define error/exit codes explicitly. Right now these tests only verify that the
# exit code is zero or nonzero.

# TODO: These tests are very expensive since they spin up new Python interpreters.
# Move most of these test cases (e.g. argument validation) to ones that interface directly
# with the scenedetect._cli module. Click also supports unit testing directly, so we should
# probably use that instead of spinning up new subprocesses for each run of the controller.
# That will also allow splitting up the validation of argument parsing logic from the controller
# logic by creating a CLI context with the desired parameters.

# TODO: Missing tests for --min-scene-len and --drop-short-scenes.

SCENEDETECT_CMD = "python -m scenedetect"
ALL_DETECTORS = [
    "detect-content",
    "detect-threshold",
    "detect-adaptive",
    "detect-hist",
    "detect-hash",
]
ALL_BACKENDS = ["opencv", "pyav"]

DEFAULT_VIDEO_PATH = "tests/resources/goldeneye.mp4"
DEFAULT_VIDEO_NAME = Path(DEFAULT_VIDEO_PATH).stem
DEFAULT_BACKEND = "opencv"
DEFAULT_STATSFILE = "statsfile.csv"
DEFAULT_TIME = "-s 2s -d 4s"  # Seek forward a bit but limit the amount we process.
DEFAULT_DETECTOR = "detect-content"
DEFAULT_CONFIG_FILE = "scenedetect.cfg"  # Ensure we default to a "blank" config file.
DEFAULT_NUM_SCENES = 2  # Number of scenes we expect to detect given above params.
DEFAULT_FFMPEG_ARGS = (
    "-vf crop=128:128:0:0 -map 0:v:0 -c:v libx264 -preset ultrafast -qp 0 -tune zerolatency"
)
"""Only encodes a small crop of the frame and tuned for performance to speed up tests."""


def invoke_scenedetect(
    args: str = "",
    output_dir: ty.Optional[str] = None,
    config_file: ty.Optional[str] = DEFAULT_CONFIG_FILE,
    **kwargs,
):
    """Invokes the scenedetect CLI with the specified arguments and returns the exit code.
    The kwargs are passed to the args format method, for example:

        invoke_scenedetect('-i {VIDEO} {DETECTOR}', VIDEO='file.mp4', DETECTOR='detect-content')

    Providing `output_dir` and `config_file` set -o/--output and -c/--config, respectively.

    Default values are set for any arguments found in the command:
        VIDEO -> VIDEO_PATH
        VIDEO_NAME -> VIDEO_NAME
        DETECTOR -> DEFAULT_DETECTOR
        TIME -> DEFAULT_TIME
        STATS -> DEFAULT_STATSFILE
        BACKEND -> DEFAULT_BACKEND
        CONFIG_FILE -> DEFAULT_CONFIG_FILE
    """
    value_dict = dict(
        VIDEO=DEFAULT_VIDEO_PATH,
        VIDEO_NAME=DEFAULT_VIDEO_NAME,
        TIME=DEFAULT_TIME,
        DETECTOR=DEFAULT_DETECTOR,
        STATS=DEFAULT_STATSFILE,
        BACKEND=DEFAULT_BACKEND,
    )
    value_dict.update(**kwargs)
    command = SCENEDETECT_CMD
    if output_dir:
        command += " -o %s" % output_dir
    if config_file:
        command += " -c %s" % config_file
    command += " " + args.format(**value_dict)
    return subprocess.call(command.strip().split(" "))


def test_cli_no_args():
    """Test `scenedetect` command invoked without any arguments."""
    assert invoke_scenedetect(config_file=None) == 0


def test_cli_default_detector():
    """Test `scenedetect` command invoked without a detector."""
    assert invoke_scenedetect("-i {VIDEO} time {TIME}", config_file=None) == 0


@pytest.mark.parametrize("info_command", ["help", "about", "version"])
def test_cli_info_command(info_command):
    """Test `scenedetect` info commands (e.g. help, about)."""
    assert invoke_scenedetect(info_command) == 0


def test_cli_time_validate_options():
    """Validate behavior of setting parameters via the `time` command."""
    base_command = "-i {VIDEO} time {TIME} {DETECTOR}"
    # Ensure cannot set end and duration together.
    assert invoke_scenedetect(base_command, TIME="-s 2.0 -d 6.0 -e 8.0") != 0
    assert invoke_scenedetect(base_command, TIME="-s 2.0 -e 8.0 -d 6.0 ") != 0


def test_cli_time_end():
    """Validate processed frames without start time being set. End time is the end frame to stop at,
    but with duration, we stop at start + duration - 1."""
    EXPECTED = """[PySceneDetect] Scene List:
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
 |      1  |           1 | 00:00:00.000 |          10 | 00:00:00.417 |
-----------------------------------------------------------------------
"""
    TEST_CASES = [
        "time --end 10",
        "time --end 00:00:00.417",
        "time --end 0.417",
        "time --duration 10",
        "time --duration 00:00:00.417",
        "time --duration 0.417",
    ]
    for test_case in TEST_CASES:
        output = subprocess.check_output(
            SCENEDETECT_CMD.split(" ")
            + ["-i", DEFAULT_VIDEO_PATH, "-m", "0", "detect-content", "list-scenes", "-n"]
            + test_case.split(),
            text=True,
        )
        assert EXPECTED in output, test_case


def test_cli_time_start():
    """Validate processed frames with both start and end/duration set. End time is the end frame to
    stop at, but with duration, we stop at start + duration - 1."""
    EXPECTED = """[PySceneDetect] Scene List:
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
 |      1  |           4 | 00:00:00.125 |          10 | 00:00:00.417 |
-----------------------------------------------------------------------
"""
    TEST_CASES = [
        "time --start 4 --end 10",
        "time --start 4 --end 00:00:00.417",
        "time --start 4 --end 0.417",
        "time --start 4 --duration 7",
        "time --start 4 --duration 0.292",
        "time --start 4 --duration 00:00:00.292",
    ]
    for test_case in TEST_CASES:
        output = subprocess.check_output(
            SCENEDETECT_CMD.split(" ")
            + ["-i", DEFAULT_VIDEO_PATH, "-m", "0", "detect-content", "list-scenes", "-n"]
            + test_case.split(),
            text=True,
        )
        assert EXPECTED in output, test_case


def test_cli_time_scene_boundary():
    """Validate frames that are processed when crossing a scene boundary. End time is the end frame
    to stop at, but with duration, we stop at start + duration - 1."""
    # -------------------------------------------------------------------------------------
    # |   Scene   |   Frame    |       PTS        |  PTS + Duration  |     Annotation     |
    # -------------------------------------------------------------------------------------
    # |     1     |     86     |   00:00:03.545   |   00:00:03.587   |    Start Frame     |
    # |     1     |     87     |   00:00:03.587   |   00:00:03.629   |                    |
    # |     1     |     88     |   00:00:03.629   |   00:00:03.670   |                    |
    # |     1     |     89     |   00:00:03.670   |   00:00:03.712   |                    |
    # |     1     |     90     |   00:00:03.712   |   00:00:03.754   |    Scene 1 End     |
    # |     2     |     91     |   00:00:03.754   |   00:00:03.795   |   Scene 2 Start    |
    # |     2     |     92     |   00:00:03.795   |   00:00:03.837   |                    |
    # |     2     |     93     |   00:00:03.837   |   00:00:03.879   |                    |
    # |     2     |     94     |   00:00:03.879   |   00:00:03.921   |                    |
    # |     2     |     95     |   00:00:03.921   |   00:00:03.962   |                    |
    # |     2     |     96     |   00:00:03.962   |   00:00:04.004   |     End Frame      |
    # -------------------------------------------------------------------------------------
    EXPECTED = """
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
 |      1  |          86 | 00:00:03.545 |          90 | 00:00:03.754 |
 |      2  |          91 | 00:00:03.754 |          96 | 00:00:04.004 |
-----------------------------------------------------------------------
"""
    # End time is the end frame to stop at, but with duration, we stop at start + duration - 1.
    TEST_CASES = [
        "time --start 86 --end 96",
        "time --start 00:00:03.545 --end 00:00:04.004",
        "time --start 3.545 --end 4.004",
        "time --start 86 --duration 11",
        "time --start 00:00:03.545 --duration 00:00:00.459",
        "time --start 3.545 --duration 0.459",
    ]
    for test_case in TEST_CASES:
        output = subprocess.check_output(
            SCENEDETECT_CMD.split(" ")
            + ["-i", DEFAULT_VIDEO_PATH, "-m", "0", "detect-content", "list-scenes", "-n"]
            + test_case.split(),
            text=True,
        )
        assert EXPECTED in output, test_case


def test_cli_time_end_of_video():
    """Validate frame number/timecode alignment at the end of the video. The end timecode includes
    presentation time and therefore should represent the full length of the video."""
    output = subprocess.check_output(
        SCENEDETECT_CMD.split(" ")
        + ["-i", DEFAULT_VIDEO_PATH, "detect-content", "list-scenes", "-n", "time", "-s", "1872"],
        text=True,
    )
    assert (
        """
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
 |      1  |        1872 | 00:01:18.036 |        1916 | 00:01:19.913 |
 |      2  |        1917 | 00:01:19.913 |        1966 | 00:01:21.999 |
 |      3  |        1967 | 00:01:21.999 |        1980 | 00:01:22.582 |
-----------------------------------------------------------------------
"""
        in output
    )
    assert "00:01:19.913,00:01:21.999" in output


@pytest.mark.parametrize("detector_command", ALL_DETECTORS)
def test_cli_detector(detector_command: str):
    """Test each detection algorithm."""
    # Ensure all detectors work without a statsfile.
    assert invoke_scenedetect("-i {VIDEO} time {TIME} {DETECTOR}", DETECTOR=detector_command) == 0


@pytest.mark.parametrize("detector_command", ALL_DETECTORS)
def test_cli_detector_with_stats(tmp_path, detector_command: str):
    """Test each detection algorithm with a statsfile."""
    # Run with a statsfile twice to ensure the file is populated with those metrics and reloaded.
    assert (
        invoke_scenedetect(
            "-i {VIDEO} -s {STATS} time {TIME} {DETECTOR}",
            output_dir=tmp_path,
            DETECTOR=detector_command,
        )
        == 0
    )
    assert (
        invoke_scenedetect(
            "-i {VIDEO} -s {STATS} time {TIME} {DETECTOR}",
            output_dir=tmp_path,
            DETECTOR=detector_command,
        )
        == 0
    )
    # TODO: Check for existence of statsfile by trying to load it with the library,
    # and ensuring that we got some frames.


def test_cli_list_scenes(tmp_path: Path):
    """Test `list-scenes` command."""
    # Regular invocation
    assert (
        invoke_scenedetect(
            "-i {VIDEO} time {TIME} {DETECTOR} list-scenes",
            output_dir=tmp_path,
        )
        == 0
    )
    output_path = tmp_path.joinpath(f"{DEFAULT_VIDEO_NAME}-Scenes.csv")
    assert os.path.exists(output_path)
    EXPECTED_CSV_OUTPUT = """Timecode List:,00:00:03.754
Scene Number,Start Frame,Start Timecode,Start Time (seconds),End Frame,End Timecode,End Time (seconds),Length (frames),Length (timecode),Length (seconds)
1,49,00:00:02.002,2.002,90,00:00:03.754,3.754,42,00:00:01.752,1.752
2,91,00:00:03.754,3.754,144,00:00:06.006,6.006,54,00:00:02.252,2.252
"""
    assert output_path.read_text() == EXPECTED_CSV_OUTPUT


def test_cli_list_scenes_skip_cuts(tmp_path: Path):
    """Test `list-scenes` command with the -s/--skip-cuts option for RFC 4180 compliance."""
    # Regular invocation
    assert (
        invoke_scenedetect(
            "-i {VIDEO} time {TIME} {DETECTOR} list-scenes -s",
            output_dir=tmp_path,
        )
        == 0
    )
    output_path = tmp_path.joinpath(f"{DEFAULT_VIDEO_NAME}-Scenes.csv")
    assert os.path.exists(output_path)
    EXPECTED_CSV_OUTPUT = """Scene Number,Start Frame,Start Timecode,Start Time (seconds),End Frame,End Timecode,End Time (seconds),Length (frames),Length (timecode),Length (seconds)
1,49,00:00:02.002,2.002,90,00:00:03.754,3.754,42,00:00:01.752,1.752
2,91,00:00:03.754,3.754,144,00:00:06.006,6.006,54,00:00:02.252,2.252
"""
    assert output_path.read_text() == EXPECTED_CSV_OUTPUT


def test_cli_list_scenes_no_output(tmp_path: Path):
    """Test `list-scenes` command with the -n flag."""
    output_path = tmp_path.joinpath(f"{DEFAULT_VIDEO_NAME}-Scenes.csv")
    assert (
        invoke_scenedetect(
            "-i {VIDEO} time {TIME} {DETECTOR} list-scenes -n",
            output_dir=tmp_path,
        )
        == 0
    )
    assert not os.path.exists(output_path)


def test_cli_list_scenes_custom_delimiter(tmp_path: Path):
    """Test `list-scenes` command with custom delimiters set in a config file."""
    config_path = tmp_path.joinpath("config.cfg")
    config_path.write_text("""
[list-scenes]
col-separator = |
row-separator = \\t
""")
    assert (
        invoke_scenedetect(
            f"-i {{VIDEO}} -c {config_path} time {{TIME}} {{DETECTOR}} list-scenes",
            output_dir=tmp_path,
        )
        == 0
    )
    output_path = tmp_path.joinpath(f"{DEFAULT_VIDEO_NAME}-Scenes.csv")
    assert os.path.exists(output_path)
    EXPECTED_CSV_OUTPUT = """Timecode List:,00:00:03.754
Scene Number,Start Frame,Start Timecode,Start Time (seconds),End Frame,End Timecode,End Time (seconds),Length (frames),Length (timecode),Length (seconds)
1,49,00:00:02.002,2.002,90,00:00:03.754,3.754,42,00:00:01.752,1.752
2,91,00:00:03.754,3.754,144,00:00:06.006,6.006,54,00:00:02.252,2.252
"""
    EXPECTED_CSV_OUTPUT = EXPECTED_CSV_OUTPUT.replace(",", "|").replace("\n", "\t")
    assert output_path.read_text() == EXPECTED_CSV_OUTPUT


def test_cli_list_scenes_rejects_multichar_col_separator(tmp_path: Path):
    """Test `list-scenes` command with custom delimiters set in a config file."""
    config_path = tmp_path.joinpath("config.cfg")
    config_path.write_text("""
[list-scenes]
col-separator = ||
""")
    assert (
        invoke_scenedetect(
            f"-i {{VIDEO}} -c {config_path} time {{TIME}} {{DETECTOR}} list-scenes",
            output_dir=tmp_path,
        )
        != 0
    )
    output_path = tmp_path.joinpath(f"{DEFAULT_VIDEO_NAME}-Scenes.csv")
    assert not os.path.exists(output_path)


@pytest.mark.skipif(condition=not is_ffmpeg_available(), reason="ffmpeg is not available")
def test_cli_split_video_ffmpeg(tmp_path: Path):
    """Test `split-video` command using ffmpeg."""

    # Assumption: The default filename format is VIDEO_NAME-Scene-SCENE_NUMBER.
    command = f"{SCENEDETECT_CMD} -i {DEFAULT_VIDEO_PATH} -o {tmp_path} time {DEFAULT_TIME} {DEFAULT_DETECTOR} split-video -a".split(
        " "
    )
    command.append(DEFAULT_FFMPEG_ARGS)
    assert subprocess.call(command) == 0
    entries = sorted(tmp_path.glob(f"{DEFAULT_VIDEO_NAME}-Scene-*"))
    assert len(entries) == DEFAULT_NUM_SCENES, entries
    [entry.unlink() for entry in entries]

    assert (
        invoke_scenedetect(
            "-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -c", output_dir=tmp_path
        )
        == 0
    )
    entries = sorted(tmp_path.glob(f"{DEFAULT_VIDEO_NAME}-Scene-*"))
    assert len(entries) == DEFAULT_NUM_SCENES
    [entry.unlink() for entry in entries]

    command += ["-f", "abc$VIDEO_NAME-123$SCENE_NUMBER"]
    assert subprocess.call(command) == 0
    entries = sorted(tmp_path.glob(f"abc{DEFAULT_VIDEO_NAME}-123*"))
    assert len(entries) == DEFAULT_NUM_SCENES, entries
    [entry.unlink() for entry in entries]

    # -a/--args and -c/--copy are mutually exclusive, so this command should fail (return nonzero)
    assert invoke_scenedetect(
        '-i {VIDEO} {DETECTOR} split-video -c -a "-c:v libx264"',
        output_dir=tmp_path,
    )


@pytest.mark.skipif(condition=not is_mkvmerge_available(), reason="mkvmerge is not available")
def test_cli_split_video_mkvmerge(tmp_path: Path):
    """Test `split-video` command using mkvmerge."""
    assert (
        invoke_scenedetect(
            "-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m", output_dir=tmp_path
        )
        == 0
    )
    assert (
        invoke_scenedetect(
            "-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -c", output_dir=tmp_path
        )
        == 0
    )
    assert (
        invoke_scenedetect(
            '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -f "test$VIDEO_NAME"',
            output_dir=tmp_path,
        )
        == 0
    )
    # -a/--args and -m/--mkvmerge are mutually exclusive
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -a "-c:v libx264"',
        output_dir=tmp_path,
    )
    # TODO: Check for existence of split video files.


def test_cli_save_images(tmp_path: Path):
    """Test `save-images` command."""
    assert (
        invoke_scenedetect(
            "-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} save-images", output_dir=tmp_path
        )
        == 0
    )
    images = [image for image in tmp_path.glob("*.jpg")]
    # Should detect two scenes and generate 3 images per scene with above params.
    assert len(images) == 6
    # Open one of the created images and make sure it has the correct resolution.
    image = cv2.imread(images[0])
    assert image.shape == (544, 1280, 3)


def test_cli_save_images_path_handling(tmp_path: Path):
    """Test `save-images` ability to handle UTF-8 paths."""
    assert (
        invoke_scenedetect(
            "-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} save-images -f %s"
            % ("電腦檔案-$SCENE_NUMBER-$IMAGE_NUMBER"),
            output_dir=tmp_path,
        )
        == 0
    )
    images = [image for image in tmp_path.glob("電腦檔案-*.jpg")]
    # Should detect two scenes and generate 3 images per scene with above params.
    assert len(images) == 6
    # Check the created images can be read and have the correct size.
    # We can't use `cv2.imread` here since it doesn't seem to work correctly with UTF-8 paths.
    image = cv2.imdecode(np.fromfile(images[0], dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    assert image.shape == (544, 1280, 3)


# TODO(#134): This works fine with OpenCV currently, but needs to be supported for PyAV and MoviePy.
def test_cli_save_images_rotation(rotated_video_file, tmp_path: Path):
    """Test that `save-images` command rotates images correctly with the default backend."""
    assert (
        invoke_scenedetect(
            "-i {VIDEO} {DETECTOR} time {TIME} save-images",
            VIDEO=rotated_video_file,
            output_dir=tmp_path,
        )
        == 0
    )
    images = [image for image in tmp_path.glob("*.jpg")]
    # Should detect two scenes and generate 3 images per scene with above params.
    assert len(images) == 6
    image = cv2.imread(images[0])
    # Note same resolution as in test_cli_save_images but rotated 90 degrees.
    assert image.shape == (1280, 544, 3)


def test_cli_export_html(tmp_path: Path):
    """Test `export-html` command."""
    base_command = "-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} {COMMAND}"
    assert (
        invoke_scenedetect(base_command, COMMAND="save-images export-html", output_dir=tmp_path)
        == 0
    )
    assert (
        invoke_scenedetect(base_command, COMMAND="export-html --no-images", output_dir=tmp_path)
        == 0
    )
    # TODO: Check for existence of HTML & image files.


def test_cli_save_qp(tmp_path: Path):
    """Test `save-qp` command with and without a custom filename format."""
    EXPECTED_QP_CONTENTS = """
0 I -1
90 I -1
"""
    for filename in (None, "custom.txt"):
        filename_format = f"--filename {filename}" if filename else ""
        assert (
            invoke_scenedetect(
                f"-i {{VIDEO}} time -e 95 {{DETECTOR}} save-qp {filename_format}",
                output_dir=tmp_path,
            )
            == 0
        )
        output_path = tmp_path.joinpath(filename if filename else f"{DEFAULT_VIDEO_NAME}.qp")
        assert os.path.exists(output_path)
        assert output_path.read_text() == EXPECTED_QP_CONTENTS[1:]


def test_cli_save_qp_start_offset(tmp_path: Path):
    """Test `save-qp` command but using a shifted start time."""
    # The QP file should always start from frame 0, so we expect a similar result to the above, but
    # with the frame numbers shifted by the start frame. Note that on the command-line, the first
    # frame is frame 1, but the first frame in a QP file is indexed by 0.
    #
    # Since we are starting at frame 51, we must shift all cuts by 50 frames.
    EXPECTED_QP_CONTENTS = """
0 I -1
40 I -1
"""
    assert (
        invoke_scenedetect(
            "-i {VIDEO} time -s 51 -e 95 {DETECTOR} save-qp",
            output_dir=tmp_path,
        )
        == 0
    )
    output_path = tmp_path.joinpath(f"{DEFAULT_VIDEO_NAME}.qp")
    assert os.path.exists(output_path)
    assert output_path.read_text() == EXPECTED_QP_CONTENTS[1:]


def test_cli_save_qp_no_shift(tmp_path: Path):
    """Test `save-qp` command with start time shifting disabled."""
    EXPECTED_QP_CONTENTS = """
50 I -1
90 I -1
"""
    assert (
        invoke_scenedetect(
            "-i {VIDEO} time -s 51 -e 95 {DETECTOR} save-qp --disable-shift",
            output_dir=tmp_path,
        )
        == 0
    )
    output_path = tmp_path.joinpath(f"{DEFAULT_VIDEO_NAME}.qp")
    assert os.path.exists(output_path)
    assert output_path.read_text() == EXPECTED_QP_CONTENTS[1:]


@pytest.mark.parametrize("backend_type", ALL_BACKENDS)
def test_cli_backend(backend_type: str):
    """Test setting the `-b`/`--backend` argument."""
    assert (
        invoke_scenedetect("-i {VIDEO} -b {BACKEND} time {TIME} {DETECTOR}", BACKEND=backend_type)
        == 0
    )


def test_cli_backend_unsupported():
    """Ensure setting an invalid backend returns an error."""
    assert (
        invoke_scenedetect("-i {VIDEO} -b {BACKEND} {DETECTOR}", BACKEND="unknown_backend_type")
        != 0
    )


def test_cli_load_scenes():
    """Ensure we can load scenes both with and without the cut row."""
    assert invoke_scenedetect("-i {VIDEO} time {TIME} {DETECTOR} list-scenes") == 0
    assert invoke_scenedetect("-i {VIDEO} time {TIME} load-scenes -i {VIDEO_NAME}-Scenes.csv") == 0
    # Specifying a detector with load-scenes should be disallowed.
    assert invoke_scenedetect(
        "-i {VIDEO} time {TIME} {DETECTOR} load-scenes -i {VIDEO_NAME}-Scenes.csv"
    )
    # Specifying load-scenes several times should be disallowed.
    assert invoke_scenedetect(
        "-i {VIDEO} time {TIME} load-scenes -i {VIDEO_NAME}-Scenes.csv load-scenes -i {VIDEO_NAME}-Scenes.csv"
    )
    # If `-s`/`--skip-cuts` is specified, the resulting scene list should still be compatible with
    # the `load-scenes` command.
    assert invoke_scenedetect("-i {VIDEO} time {TIME} {DETECTOR} list-scenes -s") == 0
    assert invoke_scenedetect("-i {VIDEO} time {TIME} load-scenes -i {VIDEO_NAME}-Scenes.csv") == 0


def test_cli_load_scenes_with_time_frames():
    """Verify we can use `load-scenes` with the `time` command and get the desired output."""
    scenes_csv = """
Scene Number,Start Frame
1,49
2,91
3,211
"""
    with open("test_scene_list.csv", "w") as f:
        f.write(scenes_csv)
    output = subprocess.check_output(
        SCENEDETECT_CMD.split(" ")
        + [
            "-i",
            DEFAULT_VIDEO_PATH,
            "load-scenes",
            "-i",
            "test_scene_list.csv",
            "time",
            "-s",
            "2s",
            "-e",
            "10s",
            "list-scenes",
        ],
        text=True,
    )
    assert (
        """
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
 |      1  |          49 | 00:00:02.002 |          90 | 00:00:03.754 |
 |      2  |          91 | 00:00:03.754 |         210 | 00:00:08.759 |
 |      3  |         211 | 00:00:08.759 |         240 | 00:00:10.010 |
-----------------------------------------------------------------------
"""
        in output
    )
    assert "00:00:03.754,00:00:08.759" in output


def test_cli_load_scenes_round_trip():
    """Verify we can use `load-scenes` with the `time` command and get the desired output."""
    scenes_csv = """
Scene Number,Start Frame
1,49
2,91
3,211
"""
    with open("test_scene_list.csv", "w") as f:
        f.write(scenes_csv)
    ground_truth = subprocess.check_output(
        SCENEDETECT_CMD.split(" ")
        + [
            "-i",
            DEFAULT_VIDEO_PATH,
            "detect-content",
            "list-scenes",
            "-f",
            "testout.csv",
            "time",
            "-s",
            "200",
            "-e",
            "400",
        ],
        text=True,
    )
    loaded_first_pass = subprocess.check_output(
        SCENEDETECT_CMD.split(" ")
        + [
            "-i",
            DEFAULT_VIDEO_PATH,
            "load-scenes",
            "-i",
            "testout.csv",
            "time",
            "-s",
            "200",
            "-e",
            "400",
            "list-scenes",
            "-f",
            "testout2.csv",
        ],
        text=True,
    )
    SPLIT_POINT = " | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |"
    assert ground_truth.split(SPLIT_POINT)[1] == loaded_first_pass.split(SPLIT_POINT)[1]
    with open("testout.csv") as first, open("testout2.csv") as second:
        assert first.readlines() == second.readlines()
