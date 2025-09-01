#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""``scenedetect.common`` Module

This module contains common types and functions used throughout PySceneDetect.

This includes :class:`FrameTimecode` which is used as a way for PySceneDetect to store
frame-accurate timestamps of each cut. This is done by also specifying the video framerate with the
timecode, allowing a frame number to be converted to/from a floating-point number of seconds, or
string in the form `"HH:MM:SS[.nnn]"` where the `[.nnn]` part is optional.

A :class:`FrameTimecode` can be created by specifying a timecode (`int` for number of frames,
`float` for number of seconds, or `str` in the form "HH:MM:SS" or "HH:MM:SS.nnn") with a framerate:

.. code:: python

    frames = FrameTimecode(timecode = 29, fps = 29.97)
    seconds_float = FrameTimecode(timecode = 10.0, fps = 10.0)
    timecode_str = FrameTimecode(timecode = "00:00:10.000", fps = 10.0)


Arithmetic/comparison operations with :class:`FrameTimecode` objects is also possible, and the
other operand can also be of the above types:

.. code:: python

    x = FrameTimecode(timecode = "00:01:00.000", fps = 10.0)
    # Can add int (frames), float (seconds), or str (timecode).
    print(x + 10)
    print(x + 10.0)
    print(x + "00:10:00")
    # Same for all comparison operators.
    print((x + 10.0) == "00:01:10.000")


:class:`FrameTimecode` objects can be added and subtracted, however the current implementation
disallows negative values, and will clamp negative results to 0.

.. warning::

    Be careful when subtracting :class:`FrameTimecode` objects or adding negative
    amounts of frames/seconds. In the example below, ``c`` will be at frame 0 since
    ``b > a``, but ``d`` will be at frame 5:

    .. code:: python

        a = FrameTimecode(5, 10.0)
        b = FrameTimecode(10, 10.0)
        c = a - b   # b > a, so c == 0
        d = b - a
        assert(c == 0)
        assert(d == 5)
"""

import math
import typing as ty
import warnings
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

import cv2

_USE_PTS_IN_DEVELOPMENT = False

##
## Type Aliases
##

SceneList = ty.List[ty.Tuple["FrameTimecode", "FrameTimecode"]]
"""Type hint for a list of scenes in the form (start time, end time)."""

CutList = ty.List["FrameTimecode"]
"""Type hint for a list of cuts, where each timecode represents the first frame of a new shot."""

CropRegion = ty.Tuple[int, int, int, int]
"""Type hint for rectangle of the form X0 Y0 X1 Y1 for cropping frames. Coordinates are relative
to source frame without downscaling.
"""

TimecodePair = ty.Tuple["FrameTimecode", "FrameTimecode"]
"""Named type for pairs of timecodes, which typically represents the start/end of a scene."""

MAX_FPS_DELTA: float = 1.0 / 100000
"""Maximum amount two framerates can differ by for equality testing."""

_SECONDS_PER_MINUTE = 60.0
_SECONDS_PER_HOUR = 60.0 * _SECONDS_PER_MINUTE
_MINUTES_PER_HOUR = 60.0


class Interpolation(Enum):
    """Interpolation method used for image resizing. Based on constants defined in OpenCV."""

    NEAREST = cv2.INTER_NEAREST
    """Nearest neighbor interpolation."""
    LINEAR = cv2.INTER_LINEAR
    """Bilinear interpolation."""
    CUBIC = cv2.INTER_CUBIC
    """Bicubic interpolation."""
    AREA = cv2.INTER_AREA
    """Pixel area relation resampling. Provides moire'-free downscaling."""
    LANCZOS4 = cv2.INTER_LANCZOS4
    """Lanczos interpolation over 8x8 neighborhood."""


# TODO(@Breakthrough): How should we deal with frame numbers when we have a `Timecode`?
#
# Each backend has slight nuances we have to take into account:
#   - PyAV: Does not include a position in frames, we can probably estimate it. Need to also compare
#     with how OpenCV handles this. It also seems to fail to decode the last frame. This library
#     provides the most accurate timing information however.
#   - OpenCV: Lacks any kind of timebase, only provides position in milliseconds and as frames.
#     This is probably sufficient, since we could just use 1ms as a timebase.
#   - MoviePy: Assumes fixed framerate and doesn't include timing information. Fixing this is
#     probably not feasible, so we should make sure the docs warn users about this.
#
# In the meantime, having backends provide accurate timing information is controlled by a hard-coded
# constant `_USE_PTS_IN_DEVELOPMENT` in each backend implementation that supports it. It still does
# not work correctly however, as we have to modify detectors themselves to work with FrameTimecode
# objects instead of integer frame numbers like they do now.
#
# We might be able to avoid changing the detector interface if we just have them work directly with
# PTS and convert them back to FrameTimecodes with the same time base.
@dataclass(frozen=True)
class Timecode:
    """Timing information associated with a given frame."""

    pts: int
    """Presentation timestamp of the frame in units of `time_base`."""
    time_base: Fraction
    """The base unit in which `pts` is measured."""

    @property
    def seconds(self) -> float:
        return float(self.time_base * self.pts)


class FrameTimecode:
    """Object for frame-based timecodes, using the video framerate to compute back and
    forth between frame number and seconds/timecode.

    A timecode is valid only if it complies with one of the following three types/formats:
        1. Timecode as `str` in the form "HH:MM:SS[.nnn]" (`"01:23:45"` or `"01:23:45.678"`)
        2. Number of seconds as `float`, or `str` in form  "SSSS.nnnn" (`"45.678"`)
        3. Exact number of frames as `int`, or `str` in form NNNNN (`456` or `"456"`)
    """

    def __init__(
        self,
        timecode: ty.Union[int, float, str, Timecode, "FrameTimecode"] = None,
        fps: ty.Union[int, float, str, "FrameTimecode"] = None,
    ):
        """
        Arguments:
            timecode: A frame number (`int`), number of seconds (`float`), timecode string in
                the form `'HH:MM:SS'` or `'HH:MM:SS.nnn'`, or a `Timecode`.
            fps: The framerate or FrameTimecode to use as a time base for all arithmetic.
        Raises:
            TypeError: Thrown if either `timecode` or `fps` are unsupported types.
            ValueError: Thrown when specifying a negative timecode or framerate.
        """
        # The following two properties are what is used to keep track of time
        # in a frame-specific manner.  Note that once the framerate is set,
        # the value should never be modified (only read if required).
        # TODO(v1.0): Make these actual @properties.
        self._framerate = fps
        self._frame_num = None
        self._timecode: ty.Optional[Timecode] = None

        # Copy constructor.
        if isinstance(timecode, FrameTimecode):
            self._framerate = timecode._framerate if fps is None else fps
            self._frame_num = timecode._frame_num
            self._timecode = timecode._timecode
            return

        # Timecode.
        if isinstance(timecode, Timecode):
            self._timecode = timecode
            return

        # Ensure args are consistent with API.
        if fps is None:
            raise TypeError("Framerate (fps) is a required argument.")
        if isinstance(fps, FrameTimecode):
            fps = fps._framerate

        # Process the given framerate, if it was not already set.
        if not isinstance(fps, (int, float)):
            raise TypeError("Framerate must be of type int/float.")
        if (isinstance(fps, int) and not fps > 0) or (
            isinstance(fps, float) and not fps >= MAX_FPS_DELTA
        ):
            raise ValueError("Framerate must be positive and greater than zero.")
        self._framerate = float(fps)
        # Process the timecode value, storing it as an exact number of frames.
        if isinstance(timecode, str):
            # TODO(v0.7): This will be incorrect for VFR videos. Need to represent this format
            # differently so we can support start/end times and min_scene_len correctly.
            self._frame_num = self._parse_timecode_string(timecode)
        else:
            self._frame_num = self._parse_timecode_number(timecode)

    # TODO(v0.7): Add a PTS property as well and slowly transition over to that, since we don't
    # always know the position as a "frame number".  However, for the reverse case, we CAN state
    # the presentation time if we know the frame number (for a fixed framerate video).
    @property
    def frame_num(self) -> ty.Optional[int]:
        return self._frame_num

    @property
    def framerate(self) -> ty.Optional[int]:
        return self._framerate

    def get_frames(self) -> int:
        """[DEPRECATED] Get the current time/position in number of frames.

        Use the `frame_num` property instead.

        :meta private:
        """
        warnings.warn(
            "get_frames() is deprecated, use the `frame_num` property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.frame_num

    def get_framerate(self) -> float:
        """[DEPRECATED] Get Framerate: Returns the framerate used by the FrameTimecode object.

        Use the `framerate` property instead.

        :meta private:
        """
        warnings.warn(
            "get_framerate() is deprecated, use the `framerate` property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.framerate

    # TODO(v0.7): Figure out how to deal with VFR here.
    def equal_framerate(self, fps) -> bool:
        """Equal Framerate: Determines if the passed framerate is equal to that of this object.

        Arguments:
            fps: Framerate to compare against within the precision constant defined in this module
                (see :data:`MAX_FPS_DELTA`).
        Returns:
            bool: True if passed fps matches the FrameTimecode object's framerate, False otherwise.

        """
        # TODO(v0.7): Support this comparison in the case FPS is not set but a timecode is.
        return math.fabs(self.framerate - fps) < MAX_FPS_DELTA

    @property
    def seconds(self) -> float:
        """The frame's position in number of seconds."""
        if self._timecode:
            return self._timecode.seconds
        # Assume constant framerate if we don't have timing information.
        return float(self._frame_num) / self._framerate

    def get_seconds(self) -> float:
        """[DEPRECATED] Get the frame's position in number of seconds.

        Use the `seconds` property instead.

        If using to compare a :class:`FrameTimecode` with a frame number,
        you can do so directly against the object (e.g. ``FrameTimecode(10, 10.0) <= 1.0``).

        Returns:
            float: The current time/position in seconds.

        :meta private:
        """
        warnings.warn(
            "get_seconds() is deprecated, use the `seconds` property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.seconds

    def get_timecode(self, precision: int = 3, use_rounding: bool = True) -> str:
        """Get a formatted timecode string of the form HH:MM:SS[.nnn].

        Args:
            precision: The number of decimal places to include in the output ``[.nnn]``.
            use_rounding: Rounds the output to the desired precision. If False, the value
                will be truncated to the specified precision.

        Returns:
            str: The current time in the form ``"HH:MM:SS[.nnn]"``.
        """
        # Compute hours and minutes based off of seconds, and update seconds.
        secs = self.seconds
        hrs = int(secs / _SECONDS_PER_HOUR)
        secs -= hrs * _SECONDS_PER_HOUR
        mins = int(secs / _SECONDS_PER_MINUTE)
        secs = max(0.0, secs - (mins * _SECONDS_PER_MINUTE))
        if use_rounding:
            secs = round(secs, precision)
        secs = min(_SECONDS_PER_MINUTE, secs)
        # Guard against emitting timecodes with 60 seconds after rounding/floating point errors.
        if int(secs) == _SECONDS_PER_MINUTE:
            secs = 0.0
            mins += 1
            if mins >= _MINUTES_PER_HOUR:
                mins = 0
                hrs += 1
        # We have to extend the precision by 1 here, since `format` will round up.
        msec = format(secs, ".%df" % (precision + 1)) if precision else ""
        # Need to include decimal place in `msec_str`.
        msec_str = msec[-(2 + precision) : -1]
        secs_str = f"{int(secs):02d}{msec_str}"
        # Return hours, minutes, and seconds as a formatted timecode string.
        return "%02d:%02d:%s" % (hrs, mins, secs_str)

    def _seconds_to_frames(self, seconds: float) -> int:
        """Convert `seconds` to the nearest number of frames using the current framerate.

        *NOTE*: This will not be correct for variable framerate videos.
        """
        return round(seconds * self._framerate)

    def _parse_timecode_number(self, timecode: ty.Union[int, float]) -> int:
        """Parse a timecode number, storing it as the exact number of frames.
        Can be passed as frame number (int), seconds (float)

        Raises:
            TypeError, ValueError
        """
        # Process the timecode value, storing it as an exact number of frames.
        # Exact number of frames N
        if isinstance(timecode, int):
            if timecode < 0:
                raise ValueError("Timecode frame number must be positive and greater than zero.")
            return timecode
        # Number of seconds S
        elif isinstance(timecode, float):
            if timecode < 0.0:
                raise ValueError("Timecode value must be positive and greater than zero.")
            return self._seconds_to_frames(timecode)
        else:
            raise TypeError("Timecode format/type unrecognized.")

    def _parse_timecode_string(self, input: str) -> int:
        """Parses a string based on the three possible forms (in timecode format,
        as an integer number of frames, or floating-point seconds, ending with 's').

        Requires that the `framerate` property is set before calling this method.
        Assuming a framerate of 30.0 FPS, the strings '00:05:00.000', '00:05:00',
        '9000', '300s', and '300.0' are all possible valid values, all representing
        a period of time equal to 5 minutes, 300 seconds, or 9000 frames (at 30 FPS).

        Raises:
            ValueError: Value could not be parsed correctly.
        """
        assert self._framerate is not None
        input = input.strip()
        # Exact number of frames N
        if input.isdigit():
            timecode = int(input)
            if timecode < 0:
                raise ValueError("Timecode frame number must be positive.")
            return timecode
        # Timecode in string format 'HH:MM:SS[.nnn]' or 'MM:SS[.nnn]'
        elif input.find(":") >= 0:
            values = input.split(":")
            if len(values) not in (2, 3):
                raise ValueError("Invalid timecode (too many separators).")
            # Case of 'HH:MM:SS[.nnn]'
            if len(values) == 3:
                hrs, mins = int(values[0]), int(values[1])
                secs = float(values[2]) if "." in values[2] else int(values[2])
            # Case of 'MM:SS[.nnn]'
            elif len(values) == 2:
                hrs = 0
                mins = int(values[0])
                secs = float(values[1]) if "." in values[1] else int(values[1])
            if not (hrs >= 0 and mins >= 0 and secs >= 0 and mins < 60 and secs < 60):
                raise ValueError("Invalid timecode range (values outside allowed range).")
            secs += (hrs * 60 * 60) + (mins * 60)
            return self._seconds_to_frames(secs)
        # Try to parse the number as seconds in the format 1234.5 or 1234s
        if input.endswith("s"):
            input = input[:-1]
        if not input.replace(".", "").isdigit():
            raise ValueError("All characters in timecode seconds string must be digits.")
        as_float = float(input)
        if as_float < 0.0:
            raise ValueError("Timecode seconds value must be positive.")
        return self._seconds_to_frames(as_float)

    def _get_other_as_frames(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> int:
        """Get the frame number from `other` for arithmetic operations."""
        if isinstance(other, int):
            return other
        if isinstance(other, float):
            return self._seconds_to_frames(other)
        if isinstance(other, str):
            return self._parse_timecode_string(other)
        if isinstance(other, FrameTimecode):
            # If comparing two FrameTimecodes, they must have the same framerate for frame-based operations.
            if self._framerate and other._framerate and not self.equal_framerate(other._framerate):
                raise ValueError(
                    "FrameTimecode instances require equal framerate for frame-based arithmetic."
                )
            if other._frame_num is not None:
                return other._frame_num
            # If other has no frame_num, it must have a timecode. Convert to frames.
            return self._seconds_to_frames(other.seconds)
        raise TypeError("Unsupported type for performing arithmetic with FrameTimecode.")

    def __eq__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if other is None:
            return False
        if self._timecode:
            return self.seconds == self._get_other_as_seconds(other)
        return self.frame_num == self._get_other_as_frames(other)

    def __ne__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if other is None:
            return True
        if self._timecode:
            return self.seconds != self._get_other_as_seconds(other)
        return self.frame_num != self._get_other_as_frames(other)

    def __lt__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if self._timecode:
            return self.seconds < self._get_other_as_seconds(other)
        return self.frame_num < self._get_other_as_frames(other)

    def __le__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if self._timecode:
            return self.seconds <= self._get_other_as_seconds(other)
        return self.frame_num <= self._get_other_as_frames(other)

    def __gt__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if self._timecode:
            return self.seconds > self._get_other_as_seconds(other)
        return self.frame_num > self._get_other_as_frames(other)

    def __ge__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if self._timecode:
            return self.seconds >= self._get_other_as_seconds(other)
        return self.frame_num >= self._get_other_as_frames(other)

    def __iadd__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        if self._timecode:
            new_seconds = self.seconds + self._get_other_as_seconds(other)
            # TODO: This is incorrect for VFR, need a better way to handle this.
            # For now, we convert back to a frame number.
            self._frame_num = self._seconds_to_frames(new_seconds)
            self._timecode = None
        else:
            self._frame_num += self._get_other_as_frames(other)
        if self._frame_num < 0:  # Required to allow adding negative seconds/frames.
            self._frame_num = 0
        return self

    def __add__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        to_return = FrameTimecode(timecode=self)
        to_return += other
        return to_return

    def __isub__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        if self._timecode:
            new_seconds = self.seconds - self._get_other_as_seconds(other)
            # TODO: This is incorrect for VFR, need a better way to handle this.
            # For now, we convert back to a frame number.
            self._frame_num = self._seconds_to_frames(new_seconds)
            self._timecode = None
        else:
            self._frame_num -= self._get_other_as_frames(other)
        if self._frame_num < 0:
            self._frame_num = 0
        return self

    def __sub__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        to_return = FrameTimecode(timecode=self)
        to_return -= other
        return to_return

    # TODO(v1.0): __int__ and __float__ should be removed. Mark as deprecated, and indicate
    # need to use relevant property instead.

    def __int__(self) -> int:
        return self._frame_num

    def __float__(self) -> float:
        return self.seconds

    def __str__(self) -> str:
        return self.get_timecode()

    def __repr__(self) -> str:
        if self._timecode:
            return f"{self.get_timecode()} [pts={self._timecode.pts}, time_base={self._timecode.time_base}]"
        return "%s [frame=%d, fps=%.3f]" % (self.get_timecode(), self._frame_num, self._framerate)

    def __hash__(self) -> int:
        if self._timecode:
            return hash(self._timecode)
        return self._frame_num

    def _get_other_as_seconds(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> float:
        """Get the time in seconds from `other` for arithmetic operations."""
        if isinstance(other, int):
            return float(other) / self._framerate
        if isinstance(other, float):
            return other
        if isinstance(other, str):
            # This is not ideal, but we need a framerate to parse strings.
            # We create a temporary FrameTimecode to do this.
            return FrameTimecode(timecode=other, fps=self._framerate).seconds
        if isinstance(other, FrameTimecode):
            return other.seconds
        raise TypeError("Unsupported type for performing arithmetic with FrameTimecode.")
