# -*- coding: utf-8 -*-
#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2023 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#

import glob
import os
from typing import Optional
import subprocess
import pytest

import cv2

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
# with the scenedetect.cli module.

SCENEDETECT_CMD = 'python -m scenedetect'
VIDEO_PATH = 'tests/resources/goldeneye.mp4'
DEFAULT_BACKEND = 'opencv'
DEFAULT_STATSFILE = 'statsfile.csv'
DEFAULT_TIME = '-s 2s -d 4s'            # Seek forward a bit but limit the amount we process.
DEFAULT_DETECTOR = 'detect-content'
DEFAULT_CONFIG_FILE = 'scenedetect.cfg' # Ensure we default to a "blank" config file.
ALL_DETECTORS = ['detect-content', 'detect-threshold', 'detect-adaptive']
ALL_BACKENDS = ['opencv', 'pyav']


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
        VIDEO_NAME -> basename of VIDEO_PATH
        DETECTOR -> DEFAULT_DETECTOR
        TIME -> DEFAULT_TIME
        STATS -> DEFAULT_STATSFILE
        BACKEND -> DEFAULT_BACKEND
        CONFIG_FILE -> DEFAULT_CONFIG_FILE
    """
    value_dict = dict(
        VIDEO=VIDEO_PATH,
        VIDEO_NAME=os.path.splitext(os.path.basename(VIDEO_PATH))[0],
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


def test_cli_no_args():
    """Test `scenedetect` command invoked without any arguments."""
    assert invoke_scenedetect(config_file=None) == 0


@pytest.mark.parametrize('info_command', ['help', 'about', 'version'])
def test_cli_info_command(info_command):
    """Test `scenedetect` info commands (e.g. help, about)."""
    assert invoke_scenedetect(info_command) == 0


def test_cli_version_info():
    """Test `scenedetect` version command with the `-a`/`--show-all` flag."""
    assert invoke_scenedetect('version -a') == 0


def test_cli_frame_numbers():
    """Validate frame numbers and timecodes align as expected for the scene list.

    The end timecode must include the presentation time of the end frame itself.
    """
    output = subprocess.check_output(
        SCENEDETECT_CMD.split(' ') +
        ['-i', VIDEO_PATH, 'detect-content', 'list-scenes', '-n', 'time', '-s', '1872'],
        text=True)
    assert """
-----------------------------------------------------------------------
 | Scene # | Start Frame |  Start Time  |  End Frame  |   End Time   |
-----------------------------------------------------------------------
 |      1  |        1872 | 00:01:18.036 |        1916 | 00:01:19.913 |
 |      2  |        1917 | 00:01:19.913 |        1966 | 00:01:21.999 |
 |      3  |        1967 | 00:01:21.999 |        1980 | 00:01:22.582 |
-----------------------------------------------------------------------
""" in output
    assert "00:01:19.913,00:01:21.999" in output


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
    assert invoke_scenedetect(base_command, TIME='-s 2s -e 4s') == 0
    # Test setting start/duration.
    assert invoke_scenedetect(base_command, TIME='-s 2s -d 2s') == 0

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


@pytest.mark.skipif(condition=not is_ffmpeg_available(), reason="ffmpeg is not available")
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


@pytest.mark.skipif(condition=not is_mkvmerge_available(), reason="mkvmerge is not available")
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
    # Open one of the created images and make sure it has the correct resolution.
    # TODO: Also need to test that the right number of images was generated, and compare with
    # expected frames from the actual video.
    images = glob.glob(os.path.join(tmp_path, '*.jpg'))
    assert images
    image = cv2.imread(images[0])
    assert image.shape == (544, 1280, 3)


# TODO(#134): This works fine with OpenCV currently, but needs to be supported for PyAV and MoviePy.
def test_cli_save_images_rotation(rotated_video_file, tmp_path):
    """Test that `save-images` command rotates images correctly with the default backend."""
    assert invoke_scenedetect(
        '-i {VIDEO} {DETECTOR} time {TIME} save-images',
        VIDEO=rotated_video_file,
        output_dir=tmp_path) == 0
    images = glob.glob(os.path.join(tmp_path, '*.jpg'))
    assert images
    image = cv2.imread(images[0])
    # Note same resolution as in test_cli_save_images but rotated 90 degrees.
    assert image.shape == (1280, 544, 3)


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


def test_cli_load_scenes():
    # Ensure we can load scenes both with and without the cut row.
    assert invoke_scenedetect('-i {VIDEO} {DETECTOR} list-scenes') == 0
    assert invoke_scenedetect('-i {VIDEO} load-scenes -i {VIDEO_NAME}-Scenes.csv') == 0
    assert invoke_scenedetect('-i {VIDEO} {DETECTOR} list-scenes -s') == 0
