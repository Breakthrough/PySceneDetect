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
# PySceneDetect is licensed under the BSD 2-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses the Numpy, OpenCV, click, tqdm, and pytest libraries.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" TODO.

This file contains functions to split videos with a scene list using
external tools (e.g. mkvmerge, ffmpeg).

"""

import logging
import subprocess

from scenedetect.platform import tqdm


# Need to add a "config" command to allow users to switch default split tool.


def split_video_mkvmerge(input_video_paths, scene_list, output_file_prefix):
    # type: (List[str], List[FrameTimecode, FrameTimecode], Optional[str]) -> None
    """ Calls the mkvmerge command on the input video, splitting it at the
    passed timecodes, where each scene is written in sequence from 001."""

    if not input_video_paths:
        return
    ret_val = None
    # mkvmerge automatically adds the scene numbers.
    output_file_name = output_file_prefix + '-Scene.mkv'
    try:
        ret_val = subprocess.call([
            'mkvmerge',
            '-o', output_file_name,
            '--split',
            'timecodes:%s' % ','.join(
                [start_time.get_timecode() for start_time, _ in scene_list[1:]]),
            ' +'.join(input_video_paths)])
    except OSError:
        logging.error('mkvmerge could not be found on the system.'
                      ' Please install mkvmerge to enable video output support.')
    if ret_val is not None and ret_val != 0:
        logging.error('Error splitting video (mkvmerge returned %d).', ret_val)


def split_video_ffmpeg(input_video_paths, scene_list, output_file_prefix,
                       arg_override='-c:v copy -c:a copy', output_extension='mp4',
                       show_progress=True):
    # type: (List[str], List[Tuple[FrameTimecode, FrameTimecode]], Optional[str],
    #        Optional[str]) -> None
    
    #https://trac.ffmpeg.org/wiki/Concatenate#samecodec

    # Need to generate temp. file list for ffmpeg if len(input_video_paths) > 1.

    if not input_video_paths:
        return
    if len(input_video_paths) > 1:
        logging.error('Splitting multiple videos with ffmpeg is not supported yet.')
        raise NotImplementedError()

    arg_override = arg_override.replace('\\"', '"')

    ret_val = None
    arg_override = arg_override.split(' ')
    
    try:
        progress_bar = None
        if show_progress and tqdm:
            progress_bar = tqdm(total=len(scene_list), unit='scenes')
        for i, (start_time, end_time) in enumerate(scene_list):
            call_list = ['ffmpeg']
            if i > 0:
                # Only show ffmpeg output for the first call, which will display any
                # errors if it fails. We suppress the output for the remaining calls.
                call_list += ['-v', 'error']
            call_list += [
                '-y',
                '-i',
                input_video_paths[0]] + arg_override + [
                '-ss',
                start_time.get_timecode(),
                '-t',
                (end_time - start_time).get_timecode(),
                '-sn',
                '%s-Scene-%03d.%s' % (output_file_prefix, i, output_extension)
                ]
            ret_val = subprocess.call(call_list)
            if i == 0:
                logging.info('Output from ffmpeg shown for first output, splitting remaining scenes...')
            if ret_val != 0:
                break
            progress_bar.update(1)
    except OSError:
        logging.error('ffmpeg could not be found on the system.'
                      ' Please install ffmpeg to enable video output support.')
    if ret_val is not None and ret_val != 0:
        logging.error('Error splitting video (ffmpeg returned %d).', ret_val)    

