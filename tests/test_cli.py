# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#

from typing import Optional
import subprocess
import pytest

# These tests validate that the CLI itself functions correctly, mainly based on the return
# return code from the process. We do not yet check for correctness of the output, just a
# successful invocation of the command (i.e. no exceptions/errors).

# TODO: Add some basic correctness tests to validate the output (just look for the
# last expected log message or extract # of scenes). Might need to refactor the test cases
# since we need to calculate the output file names for commands that write to disk.

# TODO: Define error/exit codes explicitly. Right now these tests only verify that the
# exit code is zero or nonzero.

SCENEDETECT_CMD = 'python -m scenedetect'
VIDEO_PATH = 'tests/resources/goldeneye.mp4'
DEFAULT_BACKEND = 'opencv'
DEFAULT_STATSFILE = 'statsfile.csv'
DEFAULT_TIME = '-s 2s -d 6s'            # Seek forward a bit but limit the amount we process.
DEFAULT_DETECTOR = 'detect-content'
DEFAULT_CONFIG_FILE = 'scenedetect.cfg' # Ensure we default to a "blank" config file.
ALL_DETECTORS = ['detect-content', 'detect-threshold', 'detect-adaptive']
ALL_BACKENDS = ['opencv', 'pyav', 'moviepy']


def invoke_scenedetect(
    args: str = '',
    output_dir: Optional[str] = None,
    config_file: Optional[str] = DEFAULT_CONFIG_FILE,
    **kwargs,
):
    """Invokes the scenedetect CLI with the specified arguments and returns the exit code.
    The kwargs are passed to the args format method, for example:

        invoke_scenedetect('-i {VIDEO} {DETECTOR}', VIDEO='file.mp4', DETECTOR='detect-content')

    Providing `output_dir` and `config_file` set -o/--output and -c/--config, respectively.

    Default values are set for any arguments found in the command:
        VIDEO -> VIDEO_PATH
        DETECTOR -> DEFAULT_DETECTOR
        TIME -> DEFAULT_TIME
        STATS -> DEFAULT_STATSFILE
        BACKEND -> DEFAULT_BACKEND
        CONFIG_FILE -> DEFAULT_CONFIG_FILE
    """
    value_dict = dict(
        VIDEO=VIDEO_PATH,
        TIME=DEFAULT_TIME,
        DETECTOR=DEFAULT_DETECTOR,
        STATS=DEFAULT_STATSFILE,
        BACKEND=DEFAULT_BACKEND,
    )
    value_dict.update(**kwargs)
    command = SCENEDETECT_CMD
    if output_dir:
        command += ' -o %s' % output_dir
    if config_file:
        command += ' -c %s' % config_file
    command += ' ' + args.format(**value_dict)
    return subprocess.call(command.strip().split(' '))


def can_invoke(cmd: str, args: str = '-h'):
    """Return True if the specified command can be invoked, False otherwise.

    The command should be able to be invoked as `cmd -h` and return code 0 (or override
    `args` accordingly to achieve the same behaviour).

    Used to test if certain external programs (e.g. ffmpeg, mkvmerge) are available to
    conditionally enable/disable tests that require them.
    """
    try:
        subprocess.run(args=[cmd, *args.split(' ')], check=True, capture_output=True)
    # pylint: disable=bare-except
    except:
        return False
    return True


def test_cli_no_args():
    """Test `scenedetect` command invoked without any arguments."""
    assert invoke_scenedetect(config_file=None) == 0


@pytest.mark.parametrize('info_command', ['help', 'about', 'version'])
def test_cli_info_command(info_command):
    """Test `scenedetect` info commands (e.g. help, about)."""
    assert invoke_scenedetect(info_command) == 0


@pytest.mark.parametrize('detector_command', ALL_DETECTORS)
def test_cli_detector(detector_command: str):
    """Test each detection algorithm."""
    # Ensure all detectors work without a statsfile.
    assert invoke_scenedetect('-i {VIDEO} time {TIME} {DETECTOR}', DETECTOR=detector_command) == 0


@pytest.mark.parametrize('detector_command', ALL_DETECTORS)
def test_cli_detector_with_stats(tmp_path, detector_command: str):
    """Test each detection algorithm with a statsfile."""
    # Run with a statsfile twice to ensure the file is populated with those metrics and reloaded.
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR}',
        output_dir=tmp_path,
        DETECTOR=detector_command,
    ) == 0
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR}',
        output_dir=tmp_path,
        DETECTOR=detector_command,
    ) == 0
    # TODO: Check for existence of statsfile by trying to load it with the library,
    # and ensuring that we got some frames.


def test_cli_time():
    """Test `time` command."""
    # TODO: Add test for timecode formats.
    base_command = '-i {VIDEO} time {TIME} {DETECTOR}'

    # Test setting start/end.
    assert invoke_scenedetect(base_command, TIME='-s 2s -e 8s') == 0
    # Test setting start/duration.
    assert invoke_scenedetect(base_command, TIME='-s 2s -d 6s') == 0

    # Ensure cannot set end and duration at the same time.
    assert invoke_scenedetect(base_command, TIME='-s 2s -d 6s -e 8s') != 0
    assert invoke_scenedetect(base_command, TIME='-s 2s -e 8s -d 6s ') != 0


def test_cli_list_scenes(tmp_path):
    """Test `list-scenes` command."""
    # Regular invocation
    assert invoke_scenedetect(
        '-i {VIDEO} time {TIME} {DETECTOR} list-scenes',
        output_dir=tmp_path,
    ) == 0
    # Add statsfile
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} list-scenes',
        output_dir=tmp_path,
    ) == 0
    # Suppress output file
    assert invoke_scenedetect(
        '-i {VIDEO} time {TIME} {DETECTOR} list-scenes -n',
        output_dir=tmp_path,
    ) == 0
    # TODO: Check for output files from regular invocation.
    # TODO: Delete scene list and ensure is not recreated using -n.


@pytest.mark.skipif(condition=not can_invoke('ffmpeg'), reason="ffmpeg could not be invoked!")
def test_cli_split_video_ffmpeg(tmp_path):
    """Test `split-video` command using ffmpeg."""
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video', output_dir=tmp_path) == 0
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -c', output_dir=tmp_path) == 0
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -f abc$VIDEO_NAME-123$SCENE_NUMBER',
        output_dir=tmp_path) == 0
    # -a/--args and -c/--copy are mutually exclusive
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -c -a "-c:v libx264"',
        output_dir=tmp_path)
    # TODO: Check for existence of split video files.


@pytest.mark.skipif(condition=not can_invoke('mkvmerge'), reason="mkvmerge could not be invoked!")
def test_cli_split_video_mkvmerge(tmp_path):
    """Test `split-video` command using mkvmerge."""
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m', output_dir=tmp_path) == 0
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -c', output_dir=tmp_path) == 0
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -f "test$VIDEO_NAME"',
        output_dir=tmp_path) == 0
    # -a/--args and -m/--mkvmerge are mutually exclusive
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -a "-c:v libx264"',
        output_dir=tmp_path)
    # TODO: Check for existence of split video files.


def test_cli_save_images(tmp_path):
    """Test `save-images` command."""
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} save-images', output_dir=tmp_path) == 0
    # TODO: Check for existence of split video files.


def test_cli_export_html(tmp_path):
    """Test `export-html` command."""
    base_command = '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} {COMMAND}'
    assert invoke_scenedetect(
        base_command, COMMAND='save-images export-html', output_dir=tmp_path) == 0
    assert invoke_scenedetect(
        base_command, COMMAND='export-html --no-images', output_dir=tmp_path) == 0
    # TODO: Check for existence of HTML & image files.


@pytest.mark.parametrize('backend_type', ALL_BACKENDS)
def test_cli_backend(backend_type: str):
    """Test setting the `-b`/`--backend` argument."""
    assert invoke_scenedetect(
        '-i {VIDEO} -b {BACKEND} time {TIME} {DETECTOR}', BACKEND=backend_type) == 0


def test_cli_backend_unsupported():
    # Ensure setting an invalid backend returns an error.
    assert invoke_scenedetect(
        '-i {VIDEO} -b {BACKEND} {DETECTOR}', BACKEND='unknown_backend_type') != 0
