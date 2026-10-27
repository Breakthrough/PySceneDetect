#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""``scenedetect.video_stream`` Module

This module contains the :class:`VideoStream` class, which provides a library agnostic
interface for video input. To open a video by path, use :func:`scenedetect.open_video`:

.. code:: python

    from scenedetect import open_video
    video = open_video('video.mp4')
    while True:
        frame = video.read()
        if frame is False:
            break
    print("Read %d frames" % (video.frame_number + 1))

You can also optionally specify a framerate and a specific backend library to use. Unless specified,
OpenCV will be used as the video backend. See :mod:`scenedetect.backends` for a detailed example.

New :class:`VideoStream <scenedetect.video_stream.VideoStream>` implementations can be
tested by adding it to the test suite in `tests/test_video_stream.py`.
"""

import typing as ty
from abc import ABC, abstractmethod
from enum import Enum
from fractions import Fraction

import numpy as np

from scenedetect.common import FramePosition, FrameTimecode, Timecode, TimecodeLike


class FrameNumbering(Enum):
    RELATIVE = "relative"
    SOURCE = "source"


class SeekError(Exception):
    """Either an unrecoverable error happened while attempting to seek, or the underlying
    stream is not seekable (additional information will be provided when possible).

    The stream is guaranteed to be left in a valid state, but the position may be reset."""

    ...


class VideoOpenFailure(Exception):
    """Raised by a backend if opening a video fails."""

    def __init__(self, message: str = "Unknown backend error."):
        """
        Arguments:
            message: Additional context the backend can provide for the open failure.
        """
        super().__init__(message)


class FrameRateUnavailable(VideoOpenFailure):
    """Exception instance to provide consistent error messaging across backends when the video frame
    rate is unavailable or cannot be calculated. Subclass of VideoOpenFailure."""

    def __init__(self):
        super().__init__(
            "Unable to obtain video framerate! Specify `frame_rate` manually, or"
            " re-encode/re-mux the video and try again."
        )


##
## VideoStream Interface (Base Class)
##


class VideoStream(ABC):
    """Interface which all video backends must implement."""

    #
    # Default Implementations
    #

    def __init__(self, frame_numbering: FrameNumbering = FrameNumbering.RELATIVE):
        """
        Arguments:
            frame_numbering: The frame numbering scheme to use.
        """
        self._frame_numbering: FrameNumbering = frame_numbering
        self._position: FramePosition | None = None

    @property
    def frame_numbering(self) -> FrameNumbering:
        """Returns the frame numbering scheme used by this VideoStream."""
        return self._frame_numbering

    @property
    def position(self) -> FramePosition | None:
        """Most recently recorded frame position, or None before a frame has been recorded.

        SOURCE-mode seeks may record preroll frames without returning their images.
        """
        return self._position

    @property
    def position_ms(self) -> float:
        """Presentation time of the recorded position in milliseconds, or 0.0 if there is none.

        Restarting relative frame numbering does not reset presentation time.
        """
        return self.position.timecode.seconds * 1000.0 if self.position is not None else 0.0

    @property
    def frame_number(self) -> int:
        """Zero-based ordinal of the most recently recorded frame, or -1 if there is none.

        The ordinal's origin is determined by `frame_numbering`.
        """
        return self._position.frame_number if self._position is not None else -1

    _decode_failures: int = 0
    """Cumulative count of frames which failed to decode. Backends which can detect and skip
    corrupt frames increment this as an instance attribute."""

    @property
    def base_timecode(self) -> FrameTimecode:
        """FrameTimecode object to use as a time base."""
        return FrameTimecode(timecode=0, fps=self.frame_rate)

    @property
    def decode_failures(self) -> int:
        """Number of frames that failed to decode and were skipped (may indicate video
        corruption). Always 0 for backends which do not track decode failures."""
        return self._decode_failures

    def _record_frame(self, timecode: Timecode) -> FramePosition:
        self._position = FramePosition(timecode=timecode, frame_number=self.frame_number + 1)
        return self._position

    #
    # Backend Identification
    #

    BACKEND_NAME: ty.ClassVar[str]
    """Unique name used to identify this backend. Each subclass must set this to a unique str."""

    #
    # Abstract Properties
    #

    @property
    @abstractmethod
    def path(self) -> str:
        """Video or device path."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the video, without extension, or device."""
        ...

    @property
    @abstractmethod
    def is_seekable(self) -> bool:
        """True if seek() is allowed, False otherwise."""
        ...

    @property
    @abstractmethod
    def frame_rate(self) -> Fraction:
        """Frame rate in frames/sec as a rational Fraction (e.g. Fraction(24000, 1001))."""
        ...

    @property
    @abstractmethod
    def duration(self) -> FrameTimecode | None:
        """Duration of the stream as a FrameTimecode, or None if non terminating."""
        ...

    @property
    @abstractmethod
    def frame_size(self) -> tuple[int, int]:
        """Size of each video frame in pixels as a tuple of (width, height)."""
        ...

    @property
    @abstractmethod
    def aspect_ratio(self) -> float:
        """Pixel aspect ratio as a float (1.0 represents square pixels)."""
        ...

    #
    # Abstract Methods
    #

    @abstractmethod
    def read(self, decode: bool = True) -> np.ndarray | bool:
        """Read and decode the next frame as a np.ndarray. Returns False when video ends.

        Arguments:
            decode: Return the frame image itself. If False, a boolean indicating if the stream
                was advanced to the next frame or not. This can improve performance by reducing
                memory copying and colorspace conversions when a given frame's data is not required.

        Returns:
            If decode = True, the decoded frame (np.ndarray), or False (bool) if end of video.
            If decode = False, a bool indicating if advancing to the the next frame succeeded.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Close and re-open the VideoStream (equivalent to seeking back to beginning)."""
        ...

    @abstractmethod
    def seek(self, target: TimecodeLike) -> None:
        """Position the next read at a source frame ordinal or presentation time.

        Frame targets are zero-based source ordinals regardless of the numbering mode. For
        example, `seek(4)` followed by `read()` reads the fifth source frame. Its ordinal is 4 in
        SOURCE mode and 0 in RELATIVE mode. A successful seek restarts RELATIVE numbering at 0
        without changing source-relative presentation timestamps.

        May not be supported on all backend types or inputs (e.g. cameras).

        Arguments:
            target: Target position in video stream to seek to.
                If float, interpreted as time in seconds.
                If int, interpreted as frame number.
        Raises:
            SeekError: An error occurs while seeking, or seeking is not supported.
            ValueError: `target` is not a valid value (i.e. it is negative).
        """
        ...
