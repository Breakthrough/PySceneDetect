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
"""PySceneDetect scenedetect.timecode Tests

This file includes unit tests for the scenedetect.timecode module (specifically, the
FrameTimecode object, used for representing frame-accurate timestamps and time values).

These unit tests test the FrameTimecode object with respect to object construction,
testing argument format/limits, operators (addition/subtraction), and conversion
to and from various time formats like integer frame number, float number of seconds,
or string HH:MM:SS[.nnn]. timecode format.
"""

# Third-Party Library Imports
from fractions import Fraction

import pytest

# Standard Library Imports
from scenedetect.common import MAX_FPS_DELTA, FrameTimecode, Timecode, framerate_to_fraction


def test_framerate():
    """Test FrameTimecode constructor argument "fps"."""
    # Not passing fps results in TypeError.
    with pytest.raises(TypeError):
        FrameTimecode()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        FrameTimecode(timecode=0, fps=None)
    with pytest.raises(TypeError):
        FrameTimecode(
            timecode=None,  # type: ignore[arg-type]
            fps=FrameTimecode(timecode=0, fps=None),
        )
    # Test zero FPS/negative.
    with pytest.raises(ValueError):
        FrameTimecode(timecode=0, fps=0.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=0, fps=-1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=0, fps=-100.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=0, fps=0.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=0, fps=-1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=0, fps=-1000.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=0, fps=MAX_FPS_DELTA / 2)
    # Test positive framerates.
    assert FrameTimecode(timecode=0, fps=1.0).frame_num == 0
    assert FrameTimecode(timecode=0, fps=10.0).frame_num == 0
    assert FrameTimecode(timecode=0, fps=MAX_FPS_DELTA * 2).frame_num == 0
    assert FrameTimecode(timecode=0, fps=1000.0).frame_num == 0
    assert FrameTimecode(timecode=0, fps=1000.0).frame_num == 0
    # Reject framerates too small for equality testing or potential divide by zero situations.
    with pytest.raises(ValueError):
        assert FrameTimecode(timecode=0, fps=MAX_FPS_DELTA).frame_num == 0


def test_timecode_numeric():
    """Test FrameTimecode constructor argument "timecode" with numeric arguments."""
    with pytest.raises(ValueError):
        FrameTimecode(timecode=-1, fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=-1.0, fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=-0.1, fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=-1.0 / 1000, fps=1.0)
    assert FrameTimecode(timecode=0, fps=1.0).frame_num == 0
    assert FrameTimecode(timecode=1, fps=1.0).frame_num == 1
    assert FrameTimecode(timecode=0.0, fps=1.0).frame_num == 0
    assert FrameTimecode(timecode=1.0, fps=1.0).frame_num == 1


def test_timecode_string():
    """Test FrameTimecode constructor argument "timecode" with string arguments."""
    # Invalid strings:
    with pytest.raises(ValueError):
        FrameTimecode(timecode="-1", fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode="-1.0", fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode="-0.1", fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode="1.9x", fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode="1x", fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode="1.9.9", fps=1.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode="1.0-", fps=1.0)

    # Frame number integer [int->str] ('%d', integer number as string)
    assert FrameTimecode(timecode="0", fps=1.0).frame_num == 0
    assert FrameTimecode(timecode="1", fps=1.0).frame_num == 1
    assert FrameTimecode(timecode="10", fps=1.0).frame_num == 10

    # Seconds format [float->str] ('%f', number as string)
    assert FrameTimecode(timecode="0.0", fps=1.0).frame_num == 0
    assert FrameTimecode(timecode="1.0", fps=1.0).frame_num == 1
    assert FrameTimecode(timecode="10.0", fps=1.0).frame_num == 10
    assert FrameTimecode(timecode="10.0000000000", fps=1.0).frame_num == 10
    assert FrameTimecode(timecode="10.100", fps=1.0).frame_num == 10
    assert FrameTimecode(timecode="1.100", fps=10.0).frame_num == 11

    # Seconds format [float->str] ('%fs', number as string followed by 's' for seconds)
    assert FrameTimecode(timecode="0s", fps=1.0).frame_num == 0
    assert FrameTimecode(timecode="1s", fps=1.0).frame_num == 1
    assert FrameTimecode(timecode="10s", fps=1.0).frame_num == 10
    assert FrameTimecode(timecode="10.0s", fps=1.0).frame_num == 10
    assert FrameTimecode(timecode="10.0000000000s", fps=1.0).frame_num == 10
    assert FrameTimecode(timecode="10.100s", fps=1.0).frame_num == 10
    assert FrameTimecode(timecode="1.100s", fps=10.0).frame_num == 11

    # Standard timecode format [timecode->str] ('HH:MM:SS[.nnn]', where [.nnn] is optional)
    assert FrameTimecode(timecode="00:00:01", fps=1.0).frame_num == 1
    assert FrameTimecode(timecode="00:00:01.9999", fps=1.0).frame_num == 2
    assert FrameTimecode(timecode="00:00:02.0000", fps=1.0).frame_num == 2
    assert FrameTimecode(timecode="00:00:02.0001", fps=1.0).frame_num == 2

    # MM:SS[.nnn] is also allowed
    assert FrameTimecode(timecode="00:01", fps=1.0).frame_num == 1
    assert FrameTimecode(timecode="00:01.9999", fps=1.0).frame_num == 2
    assert FrameTimecode(timecode="00:02.0000", fps=1.0).frame_num == 2
    assert FrameTimecode(timecode="00:02.0001", fps=1.0).frame_num == 2

    # Conversion edge cases
    assert FrameTimecode(timecode="00:00:01", fps=10.0).frame_num == 10
    assert FrameTimecode(timecode="00:00:00.5", fps=10.0).frame_num == 5
    assert FrameTimecode(timecode="00:00:00.100", fps=10.0).frame_num == 1
    assert FrameTimecode(timecode="00:00:00.001", fps=1000.0).frame_num == 1

    assert FrameTimecode(timecode="00:00:59.999", fps=1.0).frame_num == 60
    assert FrameTimecode(timecode="00:01:00.000", fps=1.0).frame_num == 60
    assert FrameTimecode(timecode="00:01:00.001", fps=1.0).frame_num == 60

    assert FrameTimecode(timecode="00:59:59.999", fps=1.0).frame_num == 3600
    assert FrameTimecode(timecode="01:00:00.000", fps=1.0).frame_num == 3600
    assert FrameTimecode(timecode="01:00:00.001", fps=1.0).frame_num == 3600

    # Check too many ":" characters (https://github.com/Breakthrough/PySceneDetect/issues/476)
    with pytest.raises(ValueError):
        FrameTimecode(timecode="01:01:00:00.001", fps=1.0)


def test_get_frames():
    """Test FrameTimecode get_frames() method."""
    assert FrameTimecode(timecode=1, fps=1.0).frame_num == 1
    assert FrameTimecode(timecode=1000, fps=60.0).frame_num == 1000
    assert FrameTimecode(timecode=1000000000, fps=29.97).frame_num == 1000000000

    assert FrameTimecode(timecode=1.0, fps=1.0).frame_num == int(1.0 / 1.0)
    assert FrameTimecode(timecode=1000.0, fps=60.0).frame_num == int(1000.0 * 60.0)
    assert FrameTimecode(timecode=1000000000.0, fps=29.97).frame_num == int(1000000000.0 * 29.97)

    assert FrameTimecode(timecode="00:00:02.0000", fps=1.0).frame_num == 2
    assert FrameTimecode(timecode="00:00:00.5", fps=10.0).frame_num == 5
    assert FrameTimecode(timecode="00:00:01", fps=10.0).frame_num == 10
    assert FrameTimecode(timecode="00:01:00.000", fps=1.0).frame_num == 60


def test_get_seconds():
    """Test FrameTimecode get_seconds() method."""
    assert FrameTimecode(timecode=1, fps=1.0).seconds, pytest.approx(1.0 / 1.0)
    assert FrameTimecode(timecode=1000, fps=60.0).seconds, pytest.approx(1000 / 60.0)
    assert FrameTimecode(timecode=1000000000, fps=29.97).seconds, pytest.approx(1000000000 / 29.97)

    assert FrameTimecode(timecode=1.0, fps=1.0).seconds, pytest.approx(1.0)
    assert FrameTimecode(timecode=1000.0, fps=60.0).seconds, pytest.approx(1000.0)
    assert FrameTimecode(timecode=1000000000.0, fps=29.97).seconds, pytest.approx(1000000000.0)

    assert FrameTimecode(timecode="00:00:02.0000", fps=1.0).seconds, pytest.approx(2.0)
    assert FrameTimecode(timecode="00:00:00.5", fps=10.0).seconds, pytest.approx(0.5)
    assert FrameTimecode(timecode="00:00:01", fps=10.0).seconds, pytest.approx(1.0)
    assert FrameTimecode(timecode="00:01:00.000", fps=1.0).seconds, pytest.approx(60.0)


def test_get_timecode():
    """Test FrameTimecode get_timecode() method."""
    assert FrameTimecode(timecode=1.0, fps=1.0).get_timecode() == "00:00:01.000"
    assert FrameTimecode(timecode=60.117, fps=60.0).get_timecode() == "00:01:00.117"
    assert FrameTimecode(timecode=3600.234, fps=29.97).get_timecode() == "01:00:00.234"

    assert FrameTimecode(timecode="00:00:02.0000", fps=1.0).get_timecode() == "00:00:02.000"
    assert FrameTimecode(timecode="00:00:00.5", fps=10.0).get_timecode() == "00:00:00.500"
    # If a value is provided in seconds, we store that value internally now.
    assert (
        FrameTimecode(timecode="00:00:01.501", fps=10.0).get_timecode(nearest_frame=False)
        == "00:00:01.501"
    )
    assert (
        FrameTimecode(timecode="00:00:01.501", fps=10.0).get_timecode(nearest_frame=True)
        == "00:00:01.500"
    )


def test_equality():
    """Test FrameTimecode equality (==, __eq__) operator."""
    x = FrameTimecode(timecode=1.0, fps=10.0)
    assert x == x
    assert x == FrameTimecode(timecode=1.0, fps=10.0)
    assert x == FrameTimecode(timecode=1.0, fps=10.0)
    assert x == FrameTimecode(timecode=1.0, fps=Fraction(10, 1))
    assert x != FrameTimecode(timecode=10.0, fps=10.0)
    assert x != FrameTimecode(timecode=10.0, fps=10.0)
    assert x != FrameTimecode(timecode=10.0, fps=Fraction(100, 10))
    assert x == FrameTimecode(x)
    assert x == FrameTimecode(1.0, x)
    assert x == FrameTimecode(10, x)
    assert x == "00:00:01"
    assert x == "00:00:01.0"
    assert x == "00:00:01.00"
    assert x == "00:00:01.000"
    assert x == "00:00:01.0000"
    assert x == "00:00:01.00000"
    assert x == 10
    assert x == 1.0

    with pytest.raises(ValueError):
        assert x == "0x"
    with pytest.raises(ValueError):
        assert x == "x00:00:00.000"
    with pytest.raises(TypeError):
        assert x == [0]
    with pytest.raises(TypeError):
        assert x == (0,)
    with pytest.raises(TypeError):
        assert x == [0, 1, 2, 3]
    with pytest.raises(TypeError):
        assert x == {0: 0}

    assert FrameTimecode(timecode="00:00:00.5", fps=10.0) == "00:00:00.500"
    assert FrameTimecode(timecode="00:00:01.500", fps=10.0) == "00:00:01.500"


def test_addition():
    """Test FrameTimecode addition (+/+=, __add__/__iadd__) operator."""
    x = FrameTimecode(timecode=1.0, fps=10.0)
    assert x + 1 == FrameTimecode(timecode=1.1, fps=10.0)
    assert x + 1 == FrameTimecode(1.1, x)
    assert x + 10 == "00:00:02.000", str(x + 10)
    assert x + 10 == 20
    assert x + 10 == 2.0
    assert x + 10 == "00:00:02.000"


def test_subtraction():
    """Test FrameTimecode subtraction (-/-=, __sub__) operator."""
    x = FrameTimecode(timecode=1.0, fps=10.0)
    assert (x - 1) == FrameTimecode(timecode=0.9, fps=10.0)
    assert x - 2 == FrameTimecode(0.8, x)
    assert x - 10 == FrameTimecode(0.0, x)
    # TODO(v1.0): Allow negative values. For now we clamp.
    assert x - 11 == FrameTimecode(0.0, x)
    assert x - 100 == FrameTimecode(0.0, x)
    assert x - 1.0 == FrameTimecode(0.0, x)
    assert x - 100.0 == FrameTimecode(0.0, x)
    assert x - 1 == FrameTimecode(timecode=0.9, fps=10.0)
    assert FrameTimecode("00:00:00.000", fps=20.0) == x - 10


@pytest.mark.parametrize(
    "frame_num,fps", [(1, 1.0), (61, 14.0), (29, 25.0), (126, Fraction(24000, 1001))]
)
def test_identity(frame_num, fps):
    """Test FrameTimecode values, when used in init return the same values"""
    frame_time_code = FrameTimecode(frame_num, fps=fps)
    assert FrameTimecode(frame_time_code) == frame_time_code
    assert FrameTimecode(frame_time_code.frame_num, fps=fps) == frame_time_code
    assert FrameTimecode(frame_time_code.seconds, fps=fps) == frame_time_code
    assert FrameTimecode(frame_time_code.get_timecode(), fps=fps) == frame_time_code


def test_precision():
    """Test rounding and precision, which has implications for rounding behavior."""

    fps = 1000.0

    assert FrameTimecode(110, fps).get_timecode(precision=2, use_rounding=True) == "00:00:00.11"
    assert FrameTimecode(110, fps).get_timecode(precision=2, use_rounding=False) == "00:00:00.11"
    assert FrameTimecode(110, fps).get_timecode(precision=1, use_rounding=True) == "00:00:00.1"
    assert FrameTimecode(110, fps).get_timecode(precision=1, use_rounding=False) == "00:00:00.1"
    assert FrameTimecode(110, fps).get_timecode(precision=0, use_rounding=True) == "00:00:00"
    assert FrameTimecode(110, fps).get_timecode(precision=0, use_rounding=False) == "00:00:00"

    assert FrameTimecode(990, fps).get_timecode(precision=2, use_rounding=True) == "00:00:00.99"
    assert FrameTimecode(990, fps).get_timecode(precision=2, use_rounding=False) == "00:00:00.99"
    assert FrameTimecode(990, fps).get_timecode(precision=1, use_rounding=True) == "00:00:01.0"
    assert FrameTimecode(990, fps).get_timecode(precision=1, use_rounding=False) == "00:00:00.9"
    assert FrameTimecode(990, fps).get_timecode(precision=0, use_rounding=True) == "00:00:01"
    assert FrameTimecode(990, fps).get_timecode(precision=0, use_rounding=False) == "00:00:00"


def test_rational_framerate_precision():
    """Rational framerates should round-trip frame/second conversions without drift."""
    fps = Fraction(24000, 1001)
    # Verify that frame_num round-trips through seconds without drift over many frames.
    for frame in [0, 1, 100, 1000, 10000, 100000]:
        tc = FrameTimecode(frame, fps)
        assert tc.frame_num == frame, f"Frame {frame} drifted to {tc.frame_num}"


def test_ntsc_framerate_detection():
    """Common NTSC framerates should be detected from float values."""
    assert framerate_to_fraction(23.976023976023978) == Fraction(24000, 1001)
    assert framerate_to_fraction(29.97002997002997) == Fraction(30000, 1001)
    assert framerate_to_fraction(59.94005994005994) == Fraction(60000, 1001)
    assert framerate_to_fraction(119.88011988011988) == Fraction(120000, 1001)
    assert framerate_to_fraction(24.0) == Fraction(24, 1)
    assert framerate_to_fraction(30.0) == Fraction(30, 1)
    assert framerate_to_fraction(60.0) == Fraction(60, 1)
    assert framerate_to_fraction(25.0) == Fraction(25, 1)


def test_ntsc_framerate_detection_arbitrary_base():
    """NTSC detection should work for any base rate, not a hardcoded list (e.g. 48000/1001
    for HFR cinema)."""
    assert framerate_to_fraction(47.952047952047955) == Fraction(48000, 1001)
    assert framerate_to_fraction(239.76023976023975) == Fraction(240000, 1001)


def test_ntsc_framerate_detection_low_precision():
    """Low-precision float reports (e.g. truncated to 3 decimals) should still snap to the
    NTSC rational."""
    assert framerate_to_fraction(23.976) == Fraction(24000, 1001)
    assert framerate_to_fraction(29.97) == Fraction(30000, 1001)


def test_framerate_to_fraction_non_ntsc_fallback():
    """Non-NTSC, non-integer framerates should fall back to limit_denominator and not be
    misclassified as NTSC."""
    # 24.5 is not near any N*1000/1001 within tolerance, so the limit_denominator path runs.
    assert framerate_to_fraction(24.5) == Fraction(49, 2)


def test_timecode_arithmetic_mixed_time_base():
    """Arithmetic with FrameTimecodes using different time_bases should work."""
    fps = Fraction(24000, 1001)
    # Timecode with time_base 1/24000 (from PyAV)
    tc_pyav = FrameTimecode(timecode=Timecode(pts=1001, time_base=Fraction(1, 24000)), fps=fps)
    # Timecode with time_base 1/1000000 (from OpenCV microseconds)
    tc_cv2 = FrameTimecode(timecode=Timecode(pts=41708, time_base=Fraction(1, 1000000)), fps=fps)
    # Both represent approximately 1 frame duration. Addition/subtraction shouldn't raise.
    result = tc_pyav + tc_cv2
    assert result.seconds > 0
    result = tc_pyav - tc_cv2
    assert result.seconds >= 0  # Clamped to 0 if negative


def test_timecode_frame_num_for_vfr():
    """frame_num should return approximate values for Timecode-backed objects without warning."""
    fps = Fraction(24000, 1001)
    tc = FrameTimecode(timecode=Timecode(pts=1001, time_base=Fraction(1, 24000)), fps=fps)
    # Should not raise or warn - just return the approximate frame number.
    assert tc.frame_num == 1
