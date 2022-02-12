# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2021 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
""" ``scenedetect.video_stream`` Module

This module contains the :py:class:`VideoStream` class, which provides a consistent
interface to reading videos which is library agnostic.  This allows PySceneDetect to
support multiple video backends.

"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, Union

from numpy import ndarray

from scenedetect.platform import logger
from scenedetect.frame_timecode import FrameTimecode


##
## VideoManager Exceptions
##

class SeekError(Exception):
    """Either an unrecoverable error happened while attempting to seek, or the underlying
    stream is not seekable (additional information will be provided when possible)."""


class VideoOpenFailure(Exception):
    """Raised by a backend if opening a video fails."""


##
## VideoStream Constants & Helper Functions
##

# TODO: This value can and should be tuned for performance improvements as much as possible,
# until accuracy falls, on a large enough dataset. This has yet to be done, but the current
# value doesn't seem to have caused any issues at least.
DEFAULT_MIN_WIDTH: int = 260
"""The default minimum width a frame will be downscaled to when calculating a downscale factor."""


def compute_downscale_factor(frame_width: int, effective_width: int = DEFAULT_MIN_WIDTH) -> int:
    """Get the optimal default downscale factor based on a video's resolution (currently only
    the width in pixels is considered).

    The resulting effective width of the video will be between frame_width and 1.5 * frame_width
    pixels (e.g. if frame_width is 200, the range of effective widths will be between 200 and 300).

    Arguments:
        frame_width: Actual width of the video frame in pixels.
        effective_width: Desired minimum width in pixels.

    Returns:
        int: The defalt downscale factor to use to achieve at least the target effective_width.
    """
    assert not (frame_width < 1 or effective_width < 1)
    if frame_width < effective_width:
        return 1
    return frame_width // effective_width


class VideoStream(ABC):
    """ Interface which all video backends must implement. """

    @property
    def base_timecode(self) -> FrameTimecode:
        """Base FrameTimecode object to use as a time base."""
        return FrameTimecode(timecode=0, fps=self.frame_rate)

    #
    # Abstract Properties
    #

    @property
    @abstractmethod
    def path(self) -> str:
        """Video or device path."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the video, without extension, or device."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_seekable(self) -> bool:
        """True if seek() is allowed, False otherwise."""
        raise NotImplementedError

    @property
    @abstractmethod
    def frame_rate(self) -> float:
        """Frame rate in frames/sec."""
        raise NotImplementedError

    @property
    @abstractmethod
    def duration(self) -> Optional[FrameTimecode]:
        """Duration of the stream as a FrameTimecode, or None if non terminating."""
        raise NotImplementedError

    @property
    @abstractmethod
    def frame_size(self) -> Tuple[int, int]:
        """Size of each video frame in pixels as a tuple of (width, height)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def aspect_ratio(self) -> float:
        """Display/pixel aspect ratio as a float (1.0 represents square pixels)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def position(self) -> FrameTimecode:
        """Current position within stream as FrameTimecode.

        This can be interpreted as presentation time stamp, thus frame 1 corresponds
        to the presentation time 0.  Returns 0 even if `frame_number` is 1."""
        raise NotImplementedError

    @property
    @abstractmethod
    def position_ms(self) -> float:
        """Current position within stream as a float of the presentation time in
        milliseconds. The first frame has a PTS of 0."""
        raise NotImplementedError

    @property
    @abstractmethod
    def frame_number(self) -> int:
        """Current position within stream as the frame number.

        Will return 0 until the first frame is `read`."""
        raise NotImplementedError

    #
    # Abstract Methods
    #

    @abstractmethod
    def read(self, decode: bool = True, advance: bool = True) -> Union[Optional[ndarray], bool]:
        """ Return next frame (or current if advance = False), or None if end of video.

        If decode = False, None will be returned, but will be slightly faster.  Instead a
        boolean indicating if the next frame was advanced or not is returned.

        If decode and advance are both False, equivalent to a no-op, and the return value should
        be discarded/ignored.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """ Close and re-open the VideoStream (equivalent to seeking back to beginning). """
        raise NotImplementedError

    @abstractmethod
    def seek(self, target: Union[FrameTimecode, float, int]) -> None:
        """Seek to the given timecode, frame, or time in seconds. The next frame returned from
        read() will be target + 1.
        with advance=True (the default).

        Frame 0 has a (presentation) timecode of 0.

        May not be supported on all backends/types of videos (e.g. cameras).

        Internally, PySceneDetect maps the first frame to 0 to simplify timecode handling.
        Note that most external libraries denote the first frame as 1, so correction for this is
        sometimes required.

        Arguments:
            target: Target position in video stream to seek to. Interpreted based on type.
              If FrameTimecode, backend can seek using any representation (preferably native when
              VFR support is added).
              If float, interpreted as time in seconds.
              If int, interpreted as frame number.
        Raises:
            SeekError: An unrecoverable error occurs while seeking, or seeking is not
              supported (either by the backend entirely, or if the input is a stream).
            ValueError: `target` is not a valid value (i.e. it is negative).
        """
        raise NotImplementedError
