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

See the following examples, or the :class:`FrameTimecode constructor <FrameTimecode>`.

===============================================================
Usage Examples
===============================================================

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
from dataclasses import dataclass
from fractions import Fraction

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


# TODO(@Breakthrough): Figure out interop with FrameTimecode. We can probably just store this inside
# of FrameTimecode.
# TODO(@Breakthrough): How should we deal with frame numbers? We might need to detect if a video is
# VFR or not, and if so, either omit them or always start them from 0 regardless of the start seek.
# With PyAV we can probably assume the video is VFR if the guessed rate of the stream differs
# from the average rate.
#
# Each backend has slight nuances we have to take into account:
#   - PyAV: Does not include a position in frames, we can probably estimate it. Need to also compare
#     with how OpenCV handles this. It also seems to fail to decode the last frame. This library
#     provides the most accurate timing information however.
#   - OpenCV: Lacks any kind of timebase, only provides position in milliseconds and as frames.
#     This is probably sufficient, since we could just use 1ms as a timebase.
#   - MoviePy: Assumes fixed framerate and doesn't include timing information. Fixing this is
#     probably not feasible, so we should make sure the docs warn users about this.
@dataclass
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
        timecode: ty.Union[int, float, str, "FrameTimecode"] = None,
        fps: ty.Union[int, float, str, "FrameTimecode"] = None,
    ):
        """
        Arguments:
            timecode: A frame number (int), number of seconds (float), or timecode (str in
                the form `'HH:MM:SS'` or `'HH:MM:SS.nnn'`).
            fps: The framerate or FrameTimecode to use as a time base for all arithmetic.
        Raises:
            TypeError: Thrown if either `timecode` or `fps` are unsupported types.
            ValueError: Thrown when specifying a negative timecode or framerate.
        """
        # The following two properties are what is used to keep track of time
        # in a frame-specific manner.  Note that once the framerate is set,
        # the value should never be modified (only read if required).
        # TODO(v1.0): Make these actual @properties.
        self.framerate = None
        self.frame_num = None

        # Copy constructor.  Only the timecode argument is used in this case.
        if isinstance(timecode, FrameTimecode):
            self.framerate = timecode.framerate
            self.frame_num = timecode.frame_num
            if fps is not None:
                raise TypeError("Framerate cannot be overwritten when copying a FrameTimecode.")
        else:
            # Ensure other arguments are consistent with API.
            if fps is None:
                raise TypeError("Framerate (fps) is a required argument.")
            if isinstance(fps, FrameTimecode):
                fps = fps.framerate

            # Process the given framerate, if it was not already set.
            if not isinstance(fps, (int, float)):
                raise TypeError("Framerate must be of type int/float.")
            if (isinstance(fps, int) and not fps > 0) or (
                isinstance(fps, float) and not fps >= MAX_FPS_DELTA
            ):
                raise ValueError("Framerate must be positive and greater than zero.")
            self.framerate = float(fps)

        # Process the timecode value, storing it as an exact number of frames.
        if isinstance(timecode, str):
            self.frame_num = self._parse_timecode_string(timecode)
        else:
            self.frame_num = self._parse_timecode_number(timecode)

    # TODO(v1.0): Add a `frame` property to replace the existing one and deprecate this getter.
    def get_frames(self) -> int:
        """Get the current time/position in number of frames.  This is the
        equivalent of accessing the self.frame_num property (which, along
        with the specified framerate, forms the base for all of the other
        time measurement calculations, e.g. the :meth:`get_seconds` method).

        If using to compare a :class:`FrameTimecode` with a frame number,
        you can do so directly against the object (e.g. ``FrameTimecode(10, 10.0) <= 10``).

        Returns:
            int: The current time in frames (the current frame number).
        """
        return self.frame_num

    # TODO(v1.0): Add a `framerate` property to replace the existing one and deprecate this getter.
    def get_framerate(self) -> float:
        """Get Framerate: Returns the framerate used by the FrameTimecode object.

        Returns:
            float: Framerate of the current FrameTimecode object, in frames per second.
        """
        return self.framerate

    def equal_framerate(self, fps) -> bool:
        """Equal Framerate: Determines if the passed framerate is equal to that of this object.

        Arguments:
            fps: Framerate to compare against within the precision constant defined in this module
                (see :data:`MAX_FPS_DELTA`).
        Returns:
            bool: True if passed fps matches the FrameTimecode object's framerate, False otherwise.

        """
        return math.fabs(self.framerate - fps) < MAX_FPS_DELTA

    # TODO(v1.0): Add a `seconds` property to replace this and deprecate the existing one.
    def get_seconds(self) -> float:
        """Get the frame's position in number of seconds.

        If using to compare a :class:`FrameTimecode` with a frame number,
        you can do so directly against the object (e.g. ``FrameTimecode(10, 10.0) <= 1.0``).

        Returns:
            float: The current time/position in seconds.
        """
        return float(self.frame_num) / self.framerate

    # TODO(v1.0): Add a `timecode` property to replace this and deprecate the existing one.
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
        secs = self.get_seconds()
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

    # TODO(v1.0): Add a `previous` property to replace the existing one and deprecate this getter.
    def previous_frame(self) -> "FrameTimecode":
        """Return a new FrameTimecode for the previous frame (or 0 if on frame 0)."""
        new_timecode = FrameTimecode(self)
        new_timecode.frame_num = max(0, new_timecode.frame_num - 1)
        return new_timecode

    def _seconds_to_frames(self, seconds: float) -> int:
        """Convert the passed value seconds to the nearest number of frames using
        the current FrameTimecode object's FPS (self.framerate).

        Returns:
            Integer number of frames the passed number of seconds represents using
            the current FrameTimecode's framerate property.
        """
        return round(seconds * self.framerate)

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
        # FrameTimecode
        elif isinstance(timecode, FrameTimecode):
            return timecode.frame_num
        elif timecode is None:
            raise TypeError("Timecode/frame number must be specified!")
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
        assert self.framerate is not None
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

    def __iadd__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        if isinstance(other, int):
            self.frame_num += other
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                self.frame_num += other.frame_num
            else:
                raise ValueError("FrameTimecode instances require equal framerate for addition.")
        # Check if value to add is in number of seconds.
        elif isinstance(other, float):
            self.frame_num += self._seconds_to_frames(other)
        elif isinstance(other, str):
            self.frame_num += self._parse_timecode_string(other)
        else:
            raise TypeError("Unsupported type for performing addition with FrameTimecode.")
        if self.frame_num < 0:  # Required to allow adding negative seconds/frames.
            self.frame_num = 0
        return self

    def __add__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        to_return = FrameTimecode(timecode=self)
        to_return += other
        return to_return

    def __isub__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        if isinstance(other, int):
            self.frame_num -= other
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                self.frame_num -= other.frame_num
            else:
                raise ValueError("FrameTimecode instances require equal framerate for subtraction.")
        # Check if value to add is in number of seconds.
        elif isinstance(other, float):
            self.frame_num -= self._seconds_to_frames(other)
        elif isinstance(other, str):
            self.frame_num -= self._parse_timecode_string(other)
        else:
            raise TypeError(
                "Unsupported type for performing subtraction with FrameTimecode: %s" % type(other)
            )
        if self.frame_num < 0:
            self.frame_num = 0
        return self

    def __sub__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        to_return = FrameTimecode(timecode=self)
        to_return -= other
        return to_return

    def __eq__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        if isinstance(other, int):
            return self.frame_num == other
        elif isinstance(other, float):
            return self.get_seconds() == other
        elif isinstance(other, str):
            return self.frame_num == self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num == other.frame_num
            else:
                raise TypeError(
                    "FrameTimecode objects must have the same framerate to be compared."
                )
        elif other is None:
            return False
        else:
            raise TypeError(
                "Unsupported type for performing == with FrameTimecode: %s" % type(other)
            )

    def __ne__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        return not self == other

    def __lt__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if isinstance(other, int):
            return self.frame_num < other
        elif isinstance(other, float):
            return self.get_seconds() < other
        elif isinstance(other, str):
            return self.frame_num < self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num < other.frame_num
            else:
                raise TypeError(
                    "FrameTimecode objects must have the same framerate to be compared."
                )
        else:
            raise TypeError(
                "Unsupported type for performing < with FrameTimecode: %s" % type(other)
            )

    def __le__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if isinstance(other, int):
            return self.frame_num <= other
        elif isinstance(other, float):
            return self.get_seconds() <= other
        elif isinstance(other, str):
            return self.frame_num <= self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num <= other.frame_num
            else:
                raise TypeError(
                    "FrameTimecode objects must have the same framerate to be compared."
                )
        else:
            raise TypeError(
                "Unsupported type for performing <= with FrameTimecode: %s" % type(other)
            )

    def __gt__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if isinstance(other, int):
            return self.frame_num > other
        elif isinstance(other, float):
            return self.get_seconds() > other
        elif isinstance(other, str):
            return self.frame_num > self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num > other.frame_num
            else:
                raise TypeError(
                    "FrameTimecode objects must have the same framerate to be compared."
                )
        else:
            raise TypeError(
                "Unsupported type for performing > with FrameTimecode: %s" % type(other)
            )

    def __ge__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if isinstance(other, int):
            return self.frame_num >= other
        elif isinstance(other, float):
            return self.get_seconds() >= other
        elif isinstance(other, str):
            return self.frame_num >= self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num >= other.frame_num
            else:
                raise TypeError(
                    "FrameTimecode objects must have the same framerate to be compared."
                )
        else:
            raise TypeError(
                "Unsupported type for performing >= with FrameTimecode: %s" % type(other)
            )

    # TODO(v1.0): __int__ and __float__ should be removed. Mark as deprecated, and indicate
    # need to use relevant property instead.

    def __int__(self) -> int:
        return self.frame_num

    def __float__(self) -> float:
        return self.get_seconds()

    def __str__(self) -> str:
        return self.get_timecode()

    def __repr__(self) -> str:
        return "%s [frame=%d, fps=%.3f]" % (self.get_timecode(), self.frame_num, self.framerate)

    def __hash__(self) -> int:
        return self.frame_num
