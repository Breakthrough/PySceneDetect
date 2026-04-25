#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2025 Brandon Castellano <http://www.bcastell.com>.
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

##
## Type Aliases
##

SceneList = list[tuple["FrameTimecode", "FrameTimecode"]]
"""Type hint for a list of scenes in the form (start time, end time)."""

CutList = list["FrameTimecode"]
"""Type hint for a list of cuts, where each timecode represents the first frame of a new shot."""

CropRegion = tuple[int, int, int, int]
"""Type hint for rectangle of the form X0 Y0 X1 Y1 for cropping frames. Coordinates are relative
to source frame without downscaling.
"""

TimecodePair = tuple["FrameTimecode", "FrameTimecode"]
"""Named type for pairs of timecodes, which typically represents the start/end of a scene."""

MAX_FPS_DELTA: float = 1.0 / 1000000000.0
"""Maximum amount two framerates can differ by for equality testing. Currently 1 frame/nanosec."""

_SECONDS_PER_MINUTE = 60.0
_SECONDS_PER_HOUR = 60.0 * _SECONDS_PER_MINUTE
_MINUTES_PER_HOUR = 60.0

# Common framerates mapped from their float representation to exact rational values.
_COMMON_FRAMERATES: dict[Fraction, Fraction] = {
    Fraction(24000, 1001): Fraction(24000, 1001),  # 23.976...
    Fraction(30000, 1001): Fraction(30000, 1001),  # 29.97...
    Fraction(60000, 1001): Fraction(60000, 1001),  # 59.94...
    Fraction(120000, 1001): Fraction(120000, 1001),  # 119.88...
}


def framerate_to_fraction(fps: float) -> Fraction:
    """Convert a float framerate to an exact rational Fraction.

    Recognizes common NTSC framerates (23.976, 29.97, 59.94, 119.88) and maps them to their
    exact rational representation (e.g. 24000/1001). For other values, uses limit_denominator
    to find a clean rational approximation, or returns the exact integer fraction for whole
    number framerates.
    """
    if fps <= MAX_FPS_DELTA:
        raise ValueError("Framerate must be positive and greater than zero.")
    # Integer framerates are exact.
    if fps == int(fps):
        return Fraction(int(fps), 1)
    # Check against known common framerates using limit_denominator to find the closest match.
    candidate = Fraction(fps).limit_denominator(10000)
    if candidate in _COMMON_FRAMERATES:
        return _COMMON_FRAMERATES[candidate]
    return candidate


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


@dataclass(frozen=True)
class _FrameNumber:
    """Represents a time as a frame number."""

    value: int


@dataclass(frozen=True)
class _Seconds:
    """Represents a time in seconds."""

    value: float


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
        timecode: "int | float | str | Timecode | FrameTimecode",
        fps: "float | FrameTimecode | Fraction | None" = None,
    ):
        """
        Arguments:
            timecode: A frame number (`int`), number of seconds (`float`), timecode string in
                the form `'HH:MM:SS'` or `'HH:MM:SS.nnn'`, or a `Timecode`.
            fps: The framerate to use for distance between frames and to calculate frame numbers.
                For a VFR video, this may just be the average framerate.
        Raises:
            TypeError: Thrown if either `timecode` or `fps` are unsupported types.
            ValueError: Thrown when specifying a negative timecode or framerate.
        """
        self._time: _FrameNumber | _Seconds | Timecode
        """Internal time representation."""
        self._rate: Fraction | None = None
        """Rate at which time passes between frames, measured in frames/sec."""

        # Copy constructor.
        if isinstance(timecode, FrameTimecode):
            self._time = timecode._time
            self._rate = timecode._rate if fps is None else self._ensure_fractional(fps)
            return

        # Ensure args are consistent with API.
        if fps is None:
            raise TypeError("fps is a required argument.")
        self._rate = self._ensure_fractional(fps)

        # Timecode with a time base.
        if isinstance(timecode, Timecode):
            self._time = timecode
            return

        # Process the timecode value, storing it as an exact number of frames only if required.
        if isinstance(timecode, str) and timecode.isdigit():
            timecode = int(timecode)

        if isinstance(timecode, str):
            self._time = _Seconds(self._timecode_to_seconds(timecode))
        elif isinstance(timecode, float):
            if timecode < 0.0:
                raise ValueError("Timecode frame number must be positive and greater than zero.")
            self._time = _Seconds(timecode)
        else:
            # Only `int` remains: `Timecode`/`FrameTimecode` returned earlier and `str`/`float`
            # were just handled above.
            if timecode < 0:
                raise ValueError("Timecode frame number must be positive and greater than zero.")
            self._time = _FrameNumber(timecode)

    @property
    def frame_num(self) -> int:
        """The frame number. For VFR video or Timecode-backed objects, this is an approximation
        based on the average framerate. Prefer using `pts` and `time_base` for precise timing."""
        if isinstance(self._time, Timecode):
            # Calculate approximate frame number from seconds and framerate.
            if self._rate is not None:
                return round(self._time.seconds * float(self._rate))
            # No framerate available - return estimate based on time.
            return round(self._time.seconds)
        if isinstance(self._time, _Seconds):
            return self._seconds_to_frames(self._time.value)
        return self._time.value

    @property
    def framerate(self) -> float | None:
        """The framerate to use for distance between frames and to calculate frame numbers.
        For a VFR video, this may just be the average framerate. Returns None if framerate
        is unknown (e.g. when working with pure Timecode representations)."""
        if self._rate is None:
            return None
        return float(self._rate)

    @property
    def time_base(self) -> Fraction:
        """The time base in which presentation time is calculated."""
        if isinstance(self._time, Timecode):
            return self._time.time_base
        # `_FrameNumber` / `_Seconds` are only assigned after `_rate` is set.
        assert self._rate is not None
        return 1 / self._rate

    @property
    def pts(self) -> int:
        """The presentation timestamp of the frame in units of `time_base`."""
        if isinstance(self._time, Timecode):
            return self._time.pts
        return self.frame_num

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

    def get_framerate(self) -> float | None:
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

    def equal_framerate(self, fps) -> bool:
        """Equal Framerate: Determines if the passed framerate is equal to that of this object.

        Arguments:
            fps: Framerate to compare against within the precision constant defined in this module
                (see :data:`MAX_FPS_DELTA`).
        Returns:
            bool: True if passed fps matches the FrameTimecode object's framerate, False otherwise.

        """
        if self.framerate is None:
            return False
        return math.fabs(self.framerate - fps) < MAX_FPS_DELTA

    @property
    def seconds(self) -> float:
        """The frame's position in number of seconds."""
        if isinstance(self._time, Timecode):
            return self._time.seconds
        if isinstance(self._time, _Seconds):
            return self._time.value
        # `_FrameNumber` is only assigned after `_rate` is set.
        assert self._rate is not None
        return float(self._time.value / self._rate)

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

    # TODO(https://scenedetect.com/issue/168): We should remove `nearest_frame` if possible, it
    # assumes constant framerate and causes more problems than it solves. Setting it to False makes
    # test_cli_load_scenes_with_time_frames in test_cli.py fail due to differences in end time.
    # We may also just need to clamp end time to the one specified by the user, this may not be
    # happening in the code.
    def get_timecode(
        self, precision: int = 3, use_rounding: bool = True, nearest_frame: bool = True
    ) -> str:
        """Get a formatted timecode string of the form HH:MM:SS[.nnn].

        Args:
            precision: The number of decimal places to include in the output ``[.nnn]``.
            use_rounding: Rounds the output to the desired precision. If False, the value
                will be truncated to the specified precision.
            nearest_frame: Ensures that the timecode is moved to the nearest frame boundary if this
                object has a defined framerate, otherwise has no effect.

        Returns:
            str: The current time in the form ``"HH:MM:SS[.nnn]"``.
        """
        # Compute hours and minutes based off of seconds, and update seconds.
        # For PTS-backed timecodes, the PTS already represents an exact frame boundary, so we use
        # `seconds` directly. For non-PTS timecodes, `nearest_frame` snaps to the nearest frame
        # boundary using frame_num, which avoids floating point drift in CFR video display.
        if nearest_frame and self.framerate and not isinstance(self._time, Timecode):
            secs = self.frame_num / self.framerate
        else:
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
        msec = format(secs, f".{precision + 1}f") if precision else ""
        # Need to include decimal place in `msec_str`.
        msec_str = msec[-(2 + precision) : -1]
        secs_str = f"{int(secs):02d}{msec_str}"
        # Return hours, minutes, and seconds as a formatted timecode string.
        return f"{hrs:02d}:{mins:02d}:{secs_str}"

    @staticmethod
    def _ensure_fractional(fps: "float | FrameTimecode | Fraction") -> Fraction:
        """Validate and convert an `fps` argument into a positive `Fraction`."""
        if isinstance(fps, FrameTimecode):
            if fps._rate is None:
                raise TypeError("FrameTimecode passed as fps must have a known rate.")
            return fps._rate
        if isinstance(fps, float):
            if fps <= MAX_FPS_DELTA:
                raise ValueError("Framerate must be positive and greater than zero.")
            return Fraction.from_float(fps)
        if isinstance(fps, Fraction):
            if float(fps) <= MAX_FPS_DELTA:
                raise ValueError("Framerate must be positive and greater than zero.")
            return fps
        raise TypeError(
            f"Wrong type for fps: {type(fps)} - expected float, Fraction, or FrameTimecode"
        )

    def _seconds_to_frames(self, seconds: float) -> int:
        """Convert `seconds` to the nearest number of frames using the current framerate.

        *NOTE*: This will not be correct for variable framerate videos.
        """
        assert self._rate is not None
        return round(seconds * self._rate)

    def _parse_timecode_number(self, timecode: int | float) -> int:
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

    def _timecode_to_seconds(self, input: str) -> float:
        """Parses a string based on the three possible forms (in timecode format, as an integer
        number of frames, or floating-point seconds, ending with 's'). Exact frame numbers (int)
        requires the `framerate` property was set when the timecode was created. Assuming a
        framerate of 30.0 FPS, the strings '00:05:00.000', '00:05:00', '9000', '300s', and
        '300.0' are all possible valid values. These values represent periods of time equal to
        5 minutes, 300 seconds, or 9000 frames (at 30 FPS).

        Raises:
            ValueError: Value could not be parsed correctly.
        """
        assert self._rate is not None and self._rate > MAX_FPS_DELTA
        input = input.strip()
        # Exact number of frames N
        if input.isdigit():
            timecode = int(input)
            if timecode < 0:
                raise ValueError("Timecode frame number must be positive.")
            return timecode / float(self._rate)
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
            return secs
        # Try to parse the number as seconds in the format 1234.5 or 1234s
        if input.endswith("s"):
            input = input[:-1]
        if not input.replace(".", "").isdigit():
            raise ValueError("All characters in timecode seconds string must be digits.")
        as_float = float(input)
        if as_float < 0.0:
            raise ValueError("Timecode seconds value must be positive.")
        return as_float

    def _get_other_as_frames(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> int:
        """Get the frame number from `other` for arithmetic operations."""
        if isinstance(other, int):
            return other
        if isinstance(other, float):
            return self._seconds_to_frames(other)
        if isinstance(other, str):
            return self._seconds_to_frames(self._timecode_to_seconds(other))
        if isinstance(other, FrameTimecode):
            # If comparing two FrameTimecodes, they must have the same framerate for frame-based
            # operations.
            if self._rate and other._rate and not self.equal_framerate(other._rate):
                raise ValueError(
                    "FrameTimecode instances require equal framerate for frame-based arithmetic."
                )
            if isinstance(other._time, _FrameNumber):
                return other._time.value
            # If other has no frame_num, it must have a timecode. Convert to frames.
            return self._seconds_to_frames(other.seconds)
        raise TypeError("Cannot obtain frame number for this timecode.")

    def __eq__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if other is None:
            return False
        if _compare_as_fixed(other, self):
            return self.frame_num == other.frame_num
        # For integer comparison, use frame numbers to avoid floating point precision issues.
        if isinstance(other, int):
            return self.frame_num == other
        if isinstance(self._time, (Timecode, _Seconds)):
            return self.seconds == self._get_other_as_seconds(other)
        return self.frame_num == self._get_other_as_frames(other)

    def __ne__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if other is None:
            return True
        if _compare_as_fixed(other, self):
            return self.frame_num != other.frame_num
        # For integer comparison, use frame numbers to avoid floating point precision issues.
        if isinstance(other, int):
            return self.frame_num != other
        if isinstance(self._time, (Timecode, _Seconds)):
            return self.seconds != self._get_other_as_seconds(other)
        return self.frame_num != self._get_other_as_frames(other)

    def __lt__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if _compare_as_fixed(other, self):
            return self.frame_num < other.frame_num
        # For integer comparison, use frame numbers to avoid floating point precision issues.
        if isinstance(other, int):
            return self.frame_num < other
        if isinstance(self._time, (Timecode, _Seconds)):
            return self.seconds < self._get_other_as_seconds(other)
        return self.frame_num < self._get_other_as_frames(other)

    def __le__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if _compare_as_fixed(other, self):
            return self.frame_num <= other.frame_num
        # For integer comparison, use frame numbers to avoid floating point precision issues.
        if isinstance(other, int):
            return self.frame_num <= other
        if isinstance(self._time, (Timecode, _Seconds)):
            return self.seconds <= self._get_other_as_seconds(other)
        return self.frame_num <= self._get_other_as_frames(other)

    def __gt__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if _compare_as_fixed(other, self):
            return self.frame_num > other.frame_num
        # For integer comparison, use frame numbers to avoid floating point precision issues.
        if isinstance(other, int):
            return self.frame_num > other
        if isinstance(self._time, (Timecode, _Seconds)):
            return self.seconds > self._get_other_as_seconds(other)
        return self.frame_num > self._get_other_as_frames(other)

    def __ge__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> bool:
        if _compare_as_fixed(other, self):
            return self.frame_num >= other.frame_num
        # For integer comparison, use frame numbers to avoid floating point precision issues.
        if isinstance(other, int):
            return self.frame_num >= other
        if isinstance(self._time, (Timecode, _Seconds)):
            return self.seconds >= self._get_other_as_seconds(other)
        return self.frame_num >= self._get_other_as_frames(other)

    def __iadd__(self, other: "int | float | str | FrameTimecode") -> "FrameTimecode":
        # Narrow `other`'s internal time once so pyright can track it through the dispatch below.
        other_inner = other._time if isinstance(other, FrameTimecode) else None

        if isinstance(self._time, Timecode) and isinstance(other_inner, Timecode):
            if self._time.time_base == other_inner.time_base:
                self._time = Timecode(
                    pts=max(0, self._time.pts + other_inner.pts),
                    time_base=self._time.time_base,
                )
                return self
            # Different time bases: use the finer (smaller) one for better precision.
            time_base = min(self._time.time_base, other_inner.time_base)
            self_pts = round(Fraction(self._time.pts) * self._time.time_base / time_base)
            other_pts = round(Fraction(other_inner.pts) * other_inner.time_base / time_base)
            self._time = Timecode(pts=max(0, self_pts + other_pts), time_base=time_base)
            return self

        # If either input is a timecode, the output shall also be one. The input which isn't a
        # timecode is converted into seconds, after which the equivalent timecode is computed.
        if isinstance(self._time, Timecode):
            seconds = self._get_other_as_seconds(other)
            self._time = Timecode(
                pts=max(0, self._time.pts + round(seconds / self._time.time_base)),
                time_base=self._time.time_base,
            )
            if self._rate is None and isinstance(other, FrameTimecode):
                self._rate = other._rate
            return self
        if isinstance(other_inner, Timecode):
            self._time = Timecode(
                pts=max(0, other_inner.pts + round(self.seconds / other_inner.time_base)),
                time_base=other_inner.time_base,
            )
            if self._rate is None and isinstance(other, FrameTimecode):
                self._rate = other._rate
            return self

        if isinstance(self._time, _Seconds) and isinstance(other_inner, _Seconds):
            self._time = _Seconds(max(0.0, self._time.value + other_inner.value))
            return self

        if isinstance(self._time, _Seconds):
            self._time = _Seconds(max(0.0, self._time.value + self._get_other_as_seconds(other)))
            return self

        self._time = _FrameNumber(max(0, self._time.value + self._get_other_as_frames(other)))
        return self

    def __add__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        to_return = FrameTimecode(timecode=self)
        to_return += other
        return to_return

    def __isub__(self, other: "int | float | str | FrameTimecode") -> "FrameTimecode":
        # Narrow `other`'s internal time once so pyright can track it through the dispatch below.
        other_inner = other._time if isinstance(other, FrameTimecode) else None

        if isinstance(self._time, Timecode) and isinstance(other_inner, Timecode):
            if self._time.time_base == other_inner.time_base:
                self._time = Timecode(
                    pts=max(0, self._time.pts - other_inner.pts),
                    time_base=self._time.time_base,
                )
                return self
            # Different time bases: use the finer (smaller) one for better precision.
            time_base = min(self._time.time_base, other_inner.time_base)
            self_pts = round(Fraction(self._time.pts) * self._time.time_base / time_base)
            other_pts = round(Fraction(other_inner.pts) * other_inner.time_base / time_base)
            self._time = Timecode(pts=max(0, self_pts - other_pts), time_base=time_base)
            return self

        # If either input is a timecode, the output shall also be one. The input which isn't a
        # timecode is converted into seconds, after which the equivalent timecode is computed.
        if isinstance(self._time, Timecode):
            seconds = self._get_other_as_seconds(other)
            self._time = Timecode(
                pts=max(0, self._time.pts - round(seconds / self._time.time_base)),
                time_base=self._time.time_base,
            )
            if self._rate is None and isinstance(other, FrameTimecode):
                self._rate = other._rate
            return self
        if isinstance(other_inner, Timecode):
            self._time = Timecode(
                pts=max(0, other_inner.pts - round(self.seconds / other_inner.time_base)),
                time_base=other_inner.time_base,
            )
            if self._rate is None and isinstance(other, FrameTimecode):
                self._rate = other._rate
            return self

        if isinstance(self._time, _Seconds) and isinstance(other_inner, _Seconds):
            self._time = _Seconds(max(0.0, self._time.value - other_inner.value))
            return self

        if isinstance(self._time, _Seconds):
            self._time = _Seconds(max(0.0, self._time.value - self._get_other_as_seconds(other)))
            return self

        self._time = _FrameNumber(max(0, self._time.value - self._get_other_as_frames(other)))
        return self

    def __sub__(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> "FrameTimecode":
        to_return = FrameTimecode(timecode=self)
        to_return -= other
        return to_return

    # TODO(v1.0): __int__ and __float__ should be removed. Mark as deprecated, and indicate
    # need to use relevant property instead.

    def __int__(self) -> int:
        if isinstance(self._time, _FrameNumber):
            return self._time.value
        return self.frame_num

    def __float__(self) -> float:
        return self.seconds

    def __str__(self) -> str:
        return self.get_timecode()

    def __repr__(self) -> str:
        if isinstance(self._time, Timecode):
            return f"{self.get_timecode()} [pts={self._time.pts}, time_base={self._time.time_base}]"
        if isinstance(self._time, _Seconds):
            return f"{self.get_timecode()} [seconds={self._time.value}, fps={self._rate}]"
        return f"{self.get_timecode()} [frame_num={self._time.value}, fps={self._rate}]"

    def __hash__(self) -> int:
        # Use frame_num for consistent hashing regardless of internal representation.
        # This ensures that FrameTimecodes representing the same frame have the same hash,
        # enabling proper dictionary lookups in StatsManager.
        return self.frame_num

    def _get_other_as_seconds(self, other: ty.Union[int, float, str, "FrameTimecode"]) -> float:
        """Get the time in seconds from `other` for arithmetic operations."""
        if isinstance(other, int):
            # Convert frame number to seconds using framerate.
            if self._rate is None:
                raise NotImplementedError(
                    "Cannot convert frame number to seconds without framerate"
                )
            return float(other) / float(self._rate)
        if isinstance(other, float):
            return other
        if isinstance(other, str):
            return self._timecode_to_seconds(other)
        if isinstance(other, FrameTimecode):
            return other.seconds
        raise TypeError("Unsupported type for performing arithmetic with FrameTimecode.")


def _compare_as_fixed(other: ty.Any, base: FrameTimecode) -> ty.TypeGuard[FrameTimecode]:
    """Type guard: True (and narrows `other` to `FrameTimecode`) iff both timecodes have a known
    framerate, in which case frame-based comparison is exact and preferred over float seconds."""
    return base._rate is not None and isinstance(other, FrameTimecode) and other._rate is not None


TimecodeLike = int | float | str | Timecode | FrameTimecode
"""Type hint for values that can be converted to a :class:`FrameTimecode`. Accepts a frame number
(`int`), number of seconds (`float`), timecode string (`str` of the form ``HH:MM:SS[.nnn]``), a
:class:`Timecode`, or an existing :class:`FrameTimecode`.
"""
