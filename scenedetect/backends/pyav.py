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
""":py:class:`VideoStreamAv` provides an adapter for the PyAV av.InputContainer object.

Uses string identifier ``'pyav'``.
"""

from typing import Tuple, Union

import av
from numpy import ndarray

from scenedetect.frame_timecode import FrameTimecode
from scenedetect.platform import get_file_name
from scenedetect.video_stream import VideoStream, VideoOpenFailure

#pylint: disable=c-extension-no-member
class VideoStreamAv(VideoStream):
    """PyAV `av.InputContainer` backend."""


    # TODO(#257): Allow creating a VideoStreamAv using a BytesIO object in addition to a path.
    def __init__(self, path: str):
        """Open a video by path.

        Arguments:
            path: Path to the video.

        Raises:
            IOError: file could not be found or access was denied
            VideoOpenFailure: video could not be opened (may be corrupted).
        """
        # TODO(v0.6): Investigate why setting the video stream threading mode to 'AUTO' / 'FRAME'
        # causes decoding to stop early, e.g. adding the following:
        #
        #     self._container.streams.video[0].thread_type = 'AUTO'  # Go faster!
        #
        # As a workaround, we can re-open the video without threading, and continue decoding from
        # where the multithreaded version left off. That could be as simple as re-initializing
        # self._container and retrying the read() call.
        #
        # The 'FRAME' threading method provides a significant speed boost (~400 FPS vs
        # 240 FPS without), so this seems like a worth-while tradeoff. The OpenCV backend
        # gets around 350 FPS for comparison.

        # TODO(#258): See if setting self._container.discard_corrupt = True affects anything.
        super().__init__()

        self._path = path
        self._frame = None
        try:
            self._container = av.open(path)
        except av.error.FileNotFoundError as ex:
            raise IOError from ex
        except Exception as ex:
            raise VideoOpenFailure() from ex

    #
    # Backend-Specific Methods/Properties
    #

    @property
    def _video_stream(self):
        """PyAV `av.video.stream.VideoStream` being used."""
        return self._container.streams.video[0]

    @property
    def _codec_context(self):
        """PyAV `av.codec.context.CodecContext` associated with the `video_stream`."""
        return self._video_stream.codec_context

    #
    # VideoStream Methods/Properties
    #

    BACKEND_NAME = 'pyav'
    """Unique name used to identify this backend."""

    @property
    def path(self) -> str:
        """Video path."""
        return self._path

    @property
    def name(self) -> str:
        """Name of the video, without extension."""
        return get_file_name(self.path, include_extension=False)

    @property
    def is_seekable(self) -> bool:
        """True if seek() is allowed, False otherwise."""
        return self._container.format.seek_to_pts

    @property
    def frame_size(self) -> Tuple[int, int]:
        """Size of each video frame in pixels as a tuple of (width, height)."""
        return (self._codec_context.coded_width, self._codec_context.coded_height)

    @property
    def duration(self) -> FrameTimecode:
        """Duration of the video as a FrameTimecode."""
        # TODO: Some ffmpeg wrappers have provisions for when the stream does not report a number
        # of frames (i.e. frames == 0).  In this case, we need to get the length of the video
        # and convert it into frames from it's time base (e.g. CvCapture_FFMPEG::get_total_frames()
        # and CvCapture_FFMPEG::get_duration_sec() from OpenCV).
        return self.base_timecode + self._video_stream.frames

    @property
    def frame_rate(self) -> float:
        """Frame rate in frames/sec."""
        return self._codec_context.framerate.numerator / self._codec_context.framerate.denominator

    @property
    def position(self) -> FrameTimecode:
        """Current position within stream as FrameTimecode.

        This can be interpreted as presentation time stamp, thus frame 1 corresponds
        to the presentation time 0.  Returns 0 even if `frame_number` is 1."""
        if self._frame is None:
            return self.base_timecode
        return FrameTimecode(round(self._frame.time * self.frame_rate), self.frame_rate)

    @property
    def position_ms(self) -> float:
        """Current position within stream as a float of the presentation time in
        milliseconds. The first frame has a PTS of 0."""
        if self._frame is None:
            return 0.0
        return self._frame.time * 1000.0

    @property
    def frame_number(self) -> int:
        """Current position within stream as the frame number.

        Will return 0 until the first frame is `read`."""
        if self._frame:
            return self.position.frame_num + 1
        return 0

    @property
    def aspect_ratio(self) -> float:
        """Display/pixel aspect ratio as a float (1.0 represents square pixels)."""
        return (self._codec_context.display_aspect_ratio.numerator /
                self._codec_context.display_aspect_ratio.denominator)

    def seek(self, target: Union[FrameTimecode, float, int]) -> None:
        """Seek to the given timecode. If given as a frame number, represents the current seek
        pointer (e.g. if seeking to 0, the next frame decoded will be the first frame of the video).

        For 1-based indices (first frame is frame #1), the target frame number needs to be converted
        to 0-based by subtracting one. For example, if we want to seek to the first frame, we call
        seek(0) followed by read(). If we want to seek to the 5th frame, we call seek(4) followed
        by read(), at which point frame_number will be 5.

        May not be supported on all input codecs (see `is_seekable`).

        Arguments:
            target: Target position in video stream to seek to.
                If float, interpreted as time in seconds.
                If int, interpreted as frame number.
        Raises:
            ValueError: `target` is not a valid value (i.e. it is negative).
        """
        if target < 0:
            raise ValueError("Target cannot be negative!")
        beginning = (target == 0)
        target = (self.base_timecode + target)
        if target >= 1:
            target = target - 1
        target_pts = self._video_stream.start_time + int(
            (self.base_timecode + target).get_seconds() / self._video_stream.time_base)
        self._frame = None
        self._container.seek(target_pts)
        if not beginning:
            self.read(decode=False, advance=True)
        while self.position < target:
            self.read(decode=False, advance=True)

    def reset(self):
        """ Close and re-open the VideoStream (should be equivalent to calling `seek(0)`). """
        self._container.close()
        self._frame = None
        try:
            self._container = av.open(self._path)
        except Exception as ex:
            raise VideoOpenFailure() from ex

    def read(self, decode: bool = True, advance: bool = True) -> Union[ndarray, bool]:
        """ Return next frame (or current if advance = False), or False if end of video.

        Arguments:
            decode: Decode and return the frame.
            advance: Seek to the next frame. If False, will remain on the current frame.

        Returns:
            If decode = True, returns either the decoded frame, or False if end of video.
            If decode = False, a boolean indicating if the next frame was advanced to or not is
            returned.
        """
        has_advanced = False
        if advance:
            try:
                last_frame = self._frame
                self._frame = next(self._container.decode(video=0))
            except av.error.EOFError:
                self._frame = last_frame
                return False
            except StopIteration:
                return False
            has_advanced = True
        if decode:
            return self._frame.to_ndarray(format='bgr24')
        return has_advanced
