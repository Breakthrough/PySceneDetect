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
    with open_video('video.mp4') as video:
        while True:
            frame = video.read()
            if frame is False:
                break
        print("Read %d frames" % (video.frame_number + 1))

Leaving the ``with`` block closes the video, releasing resources such as file handles and decoders.
A stream can also be closed explicitly by calling :meth:`VideoStream.close`.

You can also optionally specify a framerate and a specific backend library to use. Unless specified,
OpenCV will be used as the video backend. See :mod:`scenedetect.backends` for a detailed example.

New :class:`VideoStream <scenedetect.video_stream.VideoStream>` implementations can be
tested by adding it to the test suite in `tests/test_video_stream.py`.
"""

import typing as ty
from abc import ABC, abstractmethod
from enum import Enum
from fractions import Fraction
from types import TracebackType

import numpy as np

from scenedetect.common import FramePosition, Timecode, TimecodeLike


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

_VideoStreamT = ty.TypeVar("_VideoStreamT", bound="VideoStream")


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

    @property
    def final_frame_duration(self) -> Fraction | None:
        """Backend-reported duration of the final frame in seconds, or None if unavailable.

        Query after reading or peeking reaches EOF, before seeking, resetting, or closing.
        """
        return None

    def get_end_position(self) -> FramePosition | None:
        """Return the exclusive EOF position, or None if no frame has been recorded.

        Call after reading or peeking reaches EOF. Prefer native frame duration,
        then reported source duration, then an estimate from frame_rate.
        """
        position = self.position
        if position is None:
            return None

        last_seconds = position.timecode.seconds
        frame_duration = self.final_frame_duration

        if frame_duration is not None and frame_duration > 0:
            end_seconds = last_seconds + frame_duration
        else:
            reported_end = self.duration
            if reported_end is not None and reported_end > last_seconds:
                end_seconds = reported_end
            else:
                end_seconds = last_seconds + 1 / self.frame_rate

        return FramePosition(
            timecode=Timecode(
                pts=end_seconds.numerator,
                time_base=Fraction(1, end_seconds.denominator),
            ),
            frame_number=position.frame_number + 1,
        )

    _decode_failures: int = 0
    """Cumulative count of frames which failed to decode. Backends which can detect and skip
    corrupt frames increment this as an instance attribute."""

    _closed: bool = False
    """True once the stream has been closed. Backends which implement `close()` set this as an
    instance attribute, and call `_check_open()` from methods which require an open stream."""

    @property
    def decode_failures(self) -> int:
        """Number of frames that failed to decode and were skipped (may indicate video
        corruption). Always 0 for backends which do not track decode failures."""
        return self._decode_failures

    def close(self) -> None:  # noqa: B027 - Not abstract, so existing subclasses remain valid.
        """Close the stream, releasing any resources it holds (e.g. file handles, decoders).

        Calling `close()` more than once has no effect. Backends which hold resources override
        this method: once they are closed, `read()`, `seek()`, and `reset()` raise `ValueError`,
        and the stream is never re-opened. Properties describing the video itself (`path`, `name`,
        `frame_rate`, `duration`, `frame_size`, and `aspect_ratio`) remain available, but all
        others (e.g. `position`) are undefined, and may return arbitrary values or raise.

        A stream can also be used as a context manager, which closes it on exit:

        .. code:: python

            with open_video("video.mp4") as video:
                scene_manager.detect_scenes(video=video)

        The default implementation does nothing, so streams which hold no resources of their own
        (e.g. a :class:`VideoCaptureAdapter <scenedetect.backends.opencv.VideoCaptureAdapter>`,
        whose capture belongs to the caller) remain usable after closing.
        """

    def __enter__(self: _VideoStreamT) -> _VideoStreamT:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _check_open(self) -> None:
        """Raise `ValueError` if the stream has been closed."""
        if self._closed:
            raise ValueError("I/O operation on closed video stream.")

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
    def duration(self) -> Fraction | None:
        """Reported source duration in seconds, or None if unavailable.

        This is metadata and may be inaccurate. Estimates may be revised during decoding.
        """
        ...

    @property
    @abstractmethod
    def frame_count(self) -> int | None:
        """Reported total source frame count, or None if unavailable.

        This is metadata and may be inaccurate. Seeking and frame numbering does not change it.
        """
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
        Raises:
            ValueError: The stream is closed.
        """
        ...

    @abstractmethod
    def peek_timecode(self) -> Timecode | None:
        """Return the presentation time of the next frame without advancing the stream.

        Returns:
            Timecode of the next frame, or None if end of video.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Close and re-open the VideoStream (equivalent to seeking back to beginning).

        Raises:
            ValueError: The stream is closed.
        """
        ...

    @abstractmethod
    def seek(self, target: TimecodeLike) -> None:
        """Position the next read at a source frame ordinal or presentation time.

        Frame targets are zero-based source ordinals regardless of the numbering mode. For
        example, `seek(4)` followed by `read()` reads the fifth source frame. Its ordinal is 4 in
        SOURCE mode and 0 in RELATIVE mode. A successful seek restarts RELATIVE numbering at 0
        without changing source-relative presentation timestamps.

        May not be supported on all backend types or inputs (e.g. cameras). If `SeekError` is
        raised, the stream position is undefined. `reset()` can be called to restore the stream.

        Arguments:
            target: Target position in video stream to seek to.
                If float, interpreted as time in seconds.
                If int, interpreted as frame number.
        Raises:
            SeekError: An error occurs while seeking, or seeking is not supported.
            ValueError: `target` is not a valid value (i.e. it is negative), or the stream is
                closed.
        """
        ...
