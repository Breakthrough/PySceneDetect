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
"""

import math
import numbers
import re
import typing as ty
import warnings
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

import cv2

##
## Type Aliases
##

CropRegion = tuple[int, int, int, int]
"""Type hint for rectangle of the form X0 Y0 X1 Y1 for cropping frames. Coordinates are relative
to source frame without downscaling.
"""

CutList = list["FramePosition"]
"""Type hint for a list of cuts, where each position represents the first frame of a new shot."""

FrameRate = float | Fraction
"""Type hint for a video frame rate. ``Fraction`` is the canonical exact form and should be
preferred (e.g. ``Fraction(30000, 1001)``), while ``float`` is accepted for convenience. Floats
will be converted to rationals at runtime via :func:`framerate_to_fraction`."""

SceneList = list[tuple["FramePosition", "FramePosition"]]
"""Type hint for a list of scenes in the form (start position, end position)."""

# `Timecode` is defined later in this module; using `typing.Union` with
# string forward refs is the only form that both works at the top of the file (the PEP 604 `|`
# syntax can't accept string forward refs) and supports `TimecodeLike | None` at use sites.
TimecodeLike: ty.TypeAlias = ty.Union[int, float, str, "Timecode"]
"""Frame-or-time input accepted by :func:`parse_frame_or_time`: a frame number (`int`),
seconds (`float`), a frame/seconds/clock string (`str`), or a :class:`Timecode`."""

PositionPair = tuple["FramePosition", "FramePosition"]
"""Type hint for position pairs, typically representing the start/end of a scene."""

##
## Constants
##

MAX_FPS_DELTA: float = 1.0 / 1000000000.0
"""Maximum amount two framerates can differ by for equality testing. Currently 1 frame/nanosec."""

# `datetime.timedelta` does not expose seconds per minute/hour as constants, so we define our own.
_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 60 * _SECONDS_PER_MINUTE

# Tolerance for snapping a float value's framerate to an NTSC-derived rational (N * 1000/1001).
# e.g. 23.976 should be detected as 24000/1001, 29.97 should be detected as 30000/1001, etc.
_NTSC_DETECTION_TOLERANCE: float = 1e-3


##
## Helpers
##


def framerate_to_fraction(fps: "FrameRate | numbers.Rational") -> Fraction:
    """Convert a framerate value to an exact rational Fraction.

    Detects NTSC-derived framerates of the form ``N * 1000/1001`` (e.g. 23.976 -> 24000/1001,
    29.97 -> 30000/1001, 47.952 -> 48000/1001) for any positive integer ``N`` and returns
    their exact rational representation. Whole-number framerates are returned as
    ``Fraction(N, 1)``. Other values fall back to ``limit_denominator(10000)`` for a clean
    rational approximation. ``Fraction`` inputs are returned directly without conversion.
    :class:`numbers.Rational` (e.g. ``av.AVRational`` from PyAV) is converted using numerator and
    denominator.
    """
    if isinstance(fps, numbers.Rational) and not isinstance(fps, Fraction):
        fps = Fraction(int(fps.numerator), int(fps.denominator))
    if fps <= MAX_FPS_DELTA:
        raise ValueError("Framerate must be positive and greater than zero.")
    if isinstance(fps, Fraction):
        return fps
    if fps == int(fps):
        return Fraction(int(fps), 1)
    # Invert fps = N * 1000/1001 to recover N, then verify within tolerance.
    base = round(fps * 1001 / 1000)
    if base > 0 and abs(base * 1000 / 1001 - fps) < _NTSC_DETECTION_TOLERANCE:
        return Fraction(base * 1000, 1001)
    return Fraction(fps).limit_denominator(10000)


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

    def __post_init__(self):
        # Accept any rational (e.g. `av.AVRational` from PyAV 19+) but always store a `Fraction`
        # so downstream arithmetic (`round`, `int`, mixed-type operations) behaves consistently.
        time_base = self.time_base
        if isinstance(time_base, numbers.Rational) and not isinstance(time_base, Fraction):
            object.__setattr__(
                self, "time_base", Fraction(int(time_base.numerator), int(time_base.denominator))
            )

    @property
    def seconds(self) -> Fraction:
        return self.time_base * self.pts

    def get_timecode(self, precision: int = 3, use_rounding: bool = True) -> str:
        """Format the timestamp as HH:MM:SS[.nnn]."""
        if precision < 0:
            raise ValueError("precision must be non-negative")

        seconds = self.seconds
        scale = 10**precision
        scaled = abs(seconds) * scale
        units = round(scaled) if use_rounding else scaled.numerator // scaled.denominator

        whole_seconds, fraction = divmod(units, scale)
        hours, remainder = divmod(whole_seconds, _SECONDS_PER_HOUR)
        minutes, seconds_part = divmod(remainder, _SECONDS_PER_MINUTE)

        sign = "-" if seconds < 0 and units else ""
        suffix = f".{fraction:0{precision}d}" if precision else ""
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds_part:02d}{suffix}"


def parse_frame_or_time(value: TimecodeLike) -> int | Fraction:
    """Parse a non-negative input, preserving frames (int) or seconds (Fraction).

    Digit-only strings denote frames. Decimal strings, seconds suffixed with ``s``,
    and ``MM:SS``/``HH:MM:SS`` strings denote seconds. A Timecode uses its exact
    ``pts * time_base``; floats use their decimal string representation. No FPS
    conversion or frame rounding is performed.

    Raises:
        TypeError: Unsupported input type (including bool).
        ValueError: Negative, non-finite, or malformed input, or invalid time base.
    """
    result: int | Fraction
    if isinstance(value, bool):
        raise TypeError("Boolean values are not frame-or-time inputs.")
    if isinstance(value, int):
        result = value
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Time must be finite.")
        result = Fraction(str(value))
    elif isinstance(value, Timecode):
        if value.time_base <= 0:
            raise ValueError("Time base must be positive.")
        result = value.seconds
    elif isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"[0-9]+", text):
            return int(text)
        parts = text.split(":")
        if len(parts) not in (1, 2, 3):
            raise ValueError("Invalid timecode format.")
        hours = minutes = 0
        seconds_text = parts[-1]
        if len(parts) == 1:
            seconds_text = seconds_text.removesuffix("s")
        else:
            if not all(re.fullmatch(r"[0-9]+", part) for part in parts[:-1]):
                raise ValueError("Invalid timecode format.")
            hours = int(parts[0]) if len(parts) == 3 else 0
            minutes = int(parts[-2])
        if not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", seconds_text):
            raise ValueError("Invalid timecode seconds.")
        seconds = Fraction(seconds_text)
        if len(parts) > 1 and (minutes >= 60 or seconds >= 60):
            raise ValueError("Timecode minutes and seconds must be less than 60.")
        result = hours * 3600 + minutes * 60 + seconds
    else:
        raise TypeError(f"Unsupported frame-or-time input: {type(value)}")
    if result < 0:
        raise ValueError("Frame-or-time input must be non-negative.")
    return result


@dataclass(frozen=True)
class FramePosition:
    """Represents a frame's position, including its timecode and frame number.

    Ordering compares frame numbers within the same stream and numbering sequence.
    Equality uses both fields. String conversion formats the presentation timestamp.
    """

    timecode: Timecode
    frame_number: int

    def __sub__(self, other: "FramePosition") -> "FrameDuration":
        if not isinstance(other, FramePosition):
            raise TypeError(f"Cannot subtract {type(other)} from FramePosition")

        frames = self.frame_number - other.frame_number
        elapsed = self.timecode.seconds - other.timecode.seconds

        if frames < 0 or elapsed < 0:
            raise ValueError("Cannot subtract FramePosition objects with negative result")

        return FrameDuration(frames=frames, elapsed=elapsed)

    def get_timecode(self, precision: int = 3, use_rounding: bool = True) -> str:
        """Return the timecode as a string in HH:MM:SS[.nnn] format."""
        return self.timecode.get_timecode(precision=precision, use_rounding=use_rounding)

    @property
    def pts(self) -> int:
        """Presentation timestamp in units of time_base."""
        return self.timecode.pts

    @property
    def time_base(self) -> Fraction:
        """Timestamp unit expressed in seconds."""
        return self.timecode.time_base

    def __str__(self) -> str:
        return self.timecode.get_timecode()

    @property
    def seconds(self) -> float:
        """Return the timecode in seconds as a float. This is a convenience property for
        compatibility with legacy code that expects a float value. Use `timecode.seconds` for
        the underlying Fraction value."""
        return float(self.timecode.seconds)

    @property
    def frame_num(self) -> int:
        """Deprecated alias for frame_number"""
        warnings.warn(
            "`frame_num` is deprecated; use `frame_number` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.frame_number

    def get_frames(self) -> int:
        """Return the frame number. This is a convenience method for compatibility with legacy
        code that expects a `get_frames()` method. Use `frame_number` for the underlying value."""
        return self.frame_number

    def get_seconds(self) -> float:
        """Return the timecode in seconds as a float. This is a convenience method for
        compatibility with legacy code that expects a `get_seconds()` method. Use
        `timecode.seconds` for the underlying Fraction value."""
        return float(self.timecode.seconds)

    def __lt__(self, other: "FramePosition") -> bool:
        if not isinstance(other, FramePosition):
            return NotImplemented
        return self.frame_number < other.frame_number

    def __gt__(self, other: "FramePosition") -> bool:
        if not isinstance(other, FramePosition):
            return NotImplemented
        return self.frame_number > other.frame_number


@dataclass(frozen=True)
class FrameDuration:
    """Represents a duration of time, including its length in frames and seconds."""

    frames: int
    elapsed: Fraction
