# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the above pages for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import subprocess

import pytest

# These tests validate that the CLI itself functions correctly, mainly based on the return
# return code from the process. We do not yet check for correctness of the output, just a
# successful invocation of the command (i.e. no exceptions/errors).

# TODO(v1.0): Test should clean up working directory (create a temp one).

SCENEDETECT_CMD = 'python -m scenedetect'
VIDEO_PATH = 'tests/goldeneye/goldeneye.mp4'
DEFAULT_STATSFILE = 'statsfile.csv'
DEFAULT_TIME = '-s 2s -d 6s'    # Seek forward a bit but limit the amount we process.
DEFAULT_DETECTOR = 'detect-content'
ALL_DETECTORS = ['detect-content', 'detect-threshold', 'detect-adaptive']


def invoke_scenedetect(args: str = '', **kwargs):
    """Invokes the scenedetect CLI with the specified arguments and returns the exit code.
    The kwargs are passed to the args format method, for example:
        invoke_scenedetect('-i {VIDEO} {DETECTOR}', video='file.mp4', detector='detect-content')

    Also sets the following template arguments to default values if present in args:
        VIDEO -> VIDEO_PATH
        DETECTOR -> DEFAULT_DETECTOR
        TIME -> DEFAULT_TIME
        STATS -> DEFAULT_STATSFILE
    """
    value_dict = dict(
        VIDEO=VIDEO_PATH, TIME=DEFAULT_TIME, DETECTOR=DEFAULT_DETECTOR, STATS=DEFAULT_STATSFILE)
    value_dict.update(**kwargs)
    command = '{COMMAND} {ARGS}'.format(COMMAND=SCENEDETECT_CMD, ARGS=args.format(**value_dict))
    return subprocess.call(command.strip().split(' '))


def can_invoke(cmd: str):
    try:
        subprocess.call(cmd)
    # pylint: disable=bare-except
    except:
        return False
    return True


def test_cli_no_args():
    """Test `scenedetect` command invoked without any arguments."""
    assert invoke_scenedetect() == 0


@pytest.mark.parametrize('info_command', ['help', 'about', 'version'])
def test_cli_info_commands(info_command):
    """Test `scenedetect` info commands (e.g. help, about)."""
    assert invoke_scenedetect(info_command) == 0


@pytest.mark.parametrize('detector_command', ALL_DETECTORS)
def test_cli_detectors(detector_command: str):
    """Test each detection algorithm."""
    # Ensure all detectors work with and without a statsfile.
    assert invoke_scenedetect('-i {VIDEO} time {TIME} {DETECTOR}', DETECTOR=detector_command) == 0
    # Run with a statsfile twice to ensure the file is populated with those metrics and reloaded.
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR}', DETECTOR=detector_command) == 0
    assert invoke_scenedetect(
        '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR}', DETECTOR=detector_command) == 0


def test_cli_time():
    # TODO: Add test for timecode formats.
    base_command = '-i {VIDEO} time {TIME} {DETECTOR}'

    # Test setting start, end, and duration.
    assert invoke_scenedetect(base_command, TIME='-s 2s -e 8s') == 0    # start/end
    assert invoke_scenedetect(base_command, TIME='-s 2s -d 6s') == 0    # start/duration

    # Ensure cannot set end and duration at the same time.
    assert invoke_scenedetect(base_command, TIME='-s 2s -d 6s -e 8s') != 0
    assert invoke_scenedetect(base_command, TIME='-s 2s -e 8s -d 6s ') != 0


def test_cli_list_scenes():
    # Regular invocation (TODO: Check for output file!)
    assert invoke_scenedetect('-i {VIDEO} time {TIME} {DETECTOR} list-scenes') == 0
    # Add statsfile
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} list-scenes') == 0
    # Suppress output file
    assert invoke_scenedetect('-i {VIDEO} time {TIME} {DETECTOR} list-scenes -n') == 0


@pytest.mark.skipif(condition=not can_invoke('ffmpeg'), reason="ffmpeg could not be invoked!")
def test_cli_split_video_ffmpeg():
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video') == 0
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -c') == 0
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -c -a "-c:v libx264"')
    # TODO(v0.6): Check for existence of split video files, remove after.


@pytest.mark.skipif(condition=not can_invoke('mkvmerge'), reason="mkvmerge could not be invoked!")
def test_cli_split_video_mkvmerge():
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m') == 0
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -c') == 0
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -f "test$VIDEO_NAME"')
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} split-video -m -a "-c:v libx264"')
    # TODO(v0.6): Check for existence of split video files, remove after.


def test_cli_save_images():
    assert invoke_scenedetect('-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} save-images') == 0
    # TODO(v0.6): Check for existence of split video files, remove after.


def test_cli_export_html():
    base_command = '-i {VIDEO} -s {STATS} time {TIME} {DETECTOR} {COMMAND}'
    assert invoke_scenedetect(base_command, COMMAND='save-images export-html') == 0
    assert invoke_scenedetect(base_command, COMMAND='export-html --no-images') == 0
    # TODO: Check for existence of HTML & image files, remove after.
