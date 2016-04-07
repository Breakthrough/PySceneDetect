#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains a simple download script helper to obtain benchmark
# videos from YouTube and save them locally as .MP4 files for analysis.
#
# Copyright (C) 2012-2016 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses pytube, written by Nick Ficano; for further details,
# see the pytube Github repo at: https://github.com/nficano/pytube
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

from pytube import YouTube


video_list = [
	("https://www.youtube.com/watch?v=fkiDpLlQ9Wg", "00-GAMESHOW"),
	("https://www.youtube.com/watch?v=vFT8HXJlvfA", "01-SPORTS"),
	("https://www.youtube.com/watch?v=bpLtXIlkyYA", "02-MOVIE")
]

yt_list = [(YouTube(x[0]), x[1]) for x in video_list]

# May require modification in the future if multiple resolutions are available.
for x in yt_list:
	x[0].set_filename(x[1])
	video = x[0].get('mp4')
	video.download('.')

