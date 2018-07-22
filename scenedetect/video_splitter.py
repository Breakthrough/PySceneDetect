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


def split_video_mkvmerge(input_video_paths, scene_list, output_directory=None):
    # type: (List[str], List[FrameTimecode, FrameTimecode], Optional[str]) -> None
    """ Calls the mkvmerge command on the input video, splitting it at the
    passed timecodes, where each scene is written in sequence from 001."""
    
    #print('[PySceneDetect] Splitting video into clips...')
    #ret_val = None
    #try:
    #    ret_val = subprocess.call(
    #        ['mkvmerge',
    #         '-o', output_path,
    #         '--split', 'timecodes:%s' % timecode_list_str,
    #         input_path])
    #except OSError:
    #    print('[PySceneDetect] Error: mkvmerge could not be found on the system.'
    #          ' Please install mkvmerge to enable video output support.')
    #if ret_val is not None:
    #    if ret_val != 0:
    #        print('[PySceneDetect] Error splitting video '
    #              '(mkvmerge returned %d).' % ret_val)
    #    else:
    #        print('[PySceneDetect] Finished writing scenes to output.')

