# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses the Numpy, OpenCV, click, tqdm, and pytest libraries.
# See the included LICENSE files or one of the above URLs for more information.
#
# This software may also invoke mkvmerge or FFmpeg, if available.
#
# FFmpeg is a trademark of Fabrice Bellard.
# mkvmerge is Copyright (C) 2005-2016, Matroska.
#
# Certain distributions of PySceneDetect may include the above software;
# see the included LICENSE-FFMPEG and LICENSE-MKVMERGE files. If using a
# source distribution, these programs can be obtained from following URLs
# (note that mkvmerge is a part of the MKVToolNix package):
#
#     FFmpeg:   [ https://ffmpeg.org/download.html ]
#     mkvmerge: [ https://mkvtoolnix.download/downloads.html ]
#
# Also note that Linux users can likely obtain them from their package
# manager (e.g. `sudo apt-get install ffmpeg`).
#
# Once installed, ensure the program can be accessed system-wide by calling
# the `mkvmerge` or `ffmpeg` command from a terminal/command prompt.
# PySceneDetect will automatically use whichever program is available on
# the computer, depending on the specified command-line options.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect `scenedetect.video_splitter` Module

The scenedetect.video_splitter module contains functions to split videos
with a scene list using external tools (e.g. `mkvmerge`, `ffmpeg`), as well
as functions to check if the tools are available.

These functions are mainly intended for use by the PySceneDetect command
line interface (the `scenedetect` command).

Certain distributions of PySceneDetect may include the above software. If
using a source distribution, these programs can be obtained from following
URLs (note that mkvmerge is a part of the MKVToolNix package):

    FFmpeg:   [ https://ffmpeg.org/download.html ]

    mkvmerge: [ https://mkvtoolnix.download/downloads.html ]

Also note that Linux users can likely obtain them from their package
manager (e.g. `sudo apt-get install ffmpeg`).

Once installed, ensure the program can be accessed system-wide by calling
the `mkvmerge` or `ffmpeg` command from a terminal/command prompt.
PySceneDetect will automatically use whichever program is available on
the computer, depending on the specified command-line options.
"""

# Standard Library Imports
import logging
import subprocess
import math
import time
from string import Template

# Third-Party Library Imports
from scenedetect.platform import tqdm


##
## Command Availability Checking Functions
##

def is_mkvmerge_available():
    # type: () -> bool
    """ Is mkvmerge Available: Gracefully checks if mkvmerge command is available.

    Returns:
        (bool) True if the mkvmerge command is available, False otherwise.
    """
    ret_val = None
    try:
        ret_val = subprocess.call(['mkvmerge', '--quiet'])
    except OSError:
        return False
    if ret_val is not None and ret_val != 2:
        return False
    return True


def is_ffmpeg_available():
    # type: () -> bool
    """ Is ffmpeg Available: Gracefully checks if ffmpeg command is available.

    Returns:
        (bool) True if the ffmpeg command is available, False otherwise.
    """
    ret_val = None
    try:
        ret_val = subprocess.call(['ffmpeg', '-v', 'quiet'])
    except OSError:
        return False
    if ret_val is not None and ret_val != 1:
        return False
    return True


##
## Split Video Functions
##

def split_video_mkvmerge(input_video_paths, scene_list, output_file_prefix,
                         video_name, suppress_output=False):
    # type: (List[str], List[FrameTimecode, FrameTimecode], Optional[str],
    #        Optional[bool]) -> None
    """ Calls the mkvmerge command on the input video(s), splitting it at the
    passed timecodes, where each scene is written in sequence from 001. """

    if not input_video_paths:
        return
    ret_val = None
    # mkvmerge automatically appends '-$SCENE_NUMBER'.
    output_file_name = output_file_prefix.replace('-${SCENE_NUMBER}', '')
    output_file_name = output_file_prefix.replace('-$SCENE_NUMBER', '')
    output_file_template = Template(output_file_name)
    output_file_name = output_file_template.safe_substitute(
        VIDEO_NAME=video_name,
        SCENE_NUMBER='')

    try:
        call_list = ['mkvmerge']
        if suppress_output:
            call_list.append('--quiet')
        call_list += [
            '-o', output_file_name,
            '--split',
            #'timecodes:%s' % ','.join(
            #    [start_time.get_timecode() for start_time, _ in scene_list[1:]]),
            'parts:%s' % ','.join(
                ['%s-%s' % (start_time.get_timecode(), end_time.get_timecode())
                 for start_time, end_time in scene_list]),
            ' +'.join(input_video_paths)]
        total_frames = scene_list[-1][1].get_frames() - scene_list[0][0].get_frames()
        processing_start_time = time.time()
        ret_val = subprocess.call(call_list)
        if not suppress_output:
            print('')
            logging.info('Average processing speed %.2f frames/sec.',
                         float(total_frames) / (time.time() - processing_start_time))
    except OSError:
        logging.error('mkvmerge could not be found on the system.'
                      ' Please install mkvmerge to enable video output support.')
        raise
    if ret_val is not None and ret_val != 0:
        logging.error('Error splitting video (mkvmerge returned %d).', ret_val)


def split_video_ffmpeg(input_video_paths, scene_list, output_file_template, video_name,
                       arg_override='-c:v libx264 -preset fast -crf 21 -c:a copy',
                       hide_progress=False, suppress_output=False):
    # type: (List[str], List[Tuple[FrameTimecode, FrameTimecode]], Optional[str],
    #        Optional[str], Optional[bool]) -> None
    """ Calls the ffmpeg command on the input video(s), generating a new video for
    each scene based on the start/end timecodes. """

    if not input_video_paths:
        return

    if len(input_video_paths) > 1:
        # TODO: Add support for splitting multiple/appended input videos.
        # https://trac.ffmpeg.org/wiki/Concatenate#samecodec
        # Requires generating a temporary file list for ffmpeg.
        logging.error(
            'Sorry, splitting multiple appended/concatenated input videos with'
            ' ffmpeg is not supported yet. This feature will be added to a future'
            ' version of PySceneDetect. In the meantime, you can try using the'
            ' -c / --copy option with the split-video to use mkvmerge, which'
            ' generates less accurate output, but supports multiple input videos.')
        raise NotImplementedError()

    arg_override = arg_override.replace('\\"', '"')

    ret_val = None
    arg_override = arg_override.split(' ')
    filename_template = Template(output_file_template)
    scene_num_format = '%0'
    scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + 'd'

    try:
        progress_bar = None
        total_frames = scene_list[-1][1].get_frames() - scene_list[0][0].get_frames()
        if tqdm and not hide_progress:
            progress_bar = tqdm(total=total_frames, unit='frame', miniters=1)
        processing_start_time = time.time()
        for i, (start_time, end_time) in enumerate(scene_list):
            duration = (end_time - start_time)
            # Fix FFmpeg start timecode frame shift.
            start_time -= 1
            call_list = ['ffmpeg']
            if suppress_output:
                call_list += ['-v', 'quiet']
            elif i > 0:
                # Only show ffmpeg output for the first call, which will display any
                # errors if it fails, and then break the loop. We only show error messages
                # for the remaining calls.
                call_list += ['-v', 'error']
            call_list += [
                '-y',
                '-ss',
                start_time.get_timecode(),
                '-i',
                input_video_paths[0]]
            call_list += arg_override
            call_list += [
                '-strict',
                '-2',
                '-t',
                duration.get_timecode(),
                '-sn',
                filename_template.safe_substitute(
                    VIDEO_NAME=video_name,
                    SCENE_NUMBER=scene_num_format % (i + 1))
                ]
            ret_val = subprocess.call(call_list)
            if not suppress_output and i == 0 and len(scene_list) > 1:
                logging.info(
                    'Output from ffmpeg for Scene 1 shown above, splitting remaining scenes...')
            if ret_val != 0:
                break
            if progress_bar:
                progress_bar.update(duration.get_frames())
        if progress_bar:
            print('')
            logging.info('Average processing speed %.2f frames/sec.',
                         float(total_frames) / (time.time() - processing_start_time))
    except OSError:
        logging.error('ffmpeg could not be found on the system.'
                      ' Please install ffmpeg to enable video output support.')
    if ret_val is not None and ret_val != 0:
        logging.error('Error splitting video (ffmpeg returned %d).', ret_val)

