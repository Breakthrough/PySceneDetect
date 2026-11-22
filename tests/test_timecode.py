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
"""Tests for timecodes, frame-rate conversion and NTSC filter regressions."""

# Third-Party Library Imports
import math
import numbers
import random
from fractions import Fraction

import pytest

# Standard Library Imports
from scenedetect.common import (
    MAX_FPS_DELTA,
    FrameDuration,
    FramePosition,
    Timecode,
    framerate_to_fraction,
)
from scenedetect.detector import FlashFilter


def test_framerate_to_fraction_rejects_invalid_rates():
    """Reject rates at or below the minimum supported threshold."""
    # Test zero FPS/negative.
    with pytest.raises(ValueError):
        framerate_to_fraction(fps=0.0)
    with pytest.raises(ValueError):
        framerate_to_fraction(fps=-1.0)
    with pytest.raises(ValueError):
        framerate_to_fraction(fps=-100.0)
    with pytest.raises(ValueError):
        framerate_to_fraction(fps=0.0)
    with pytest.raises(ValueError):
        framerate_to_fraction(fps=-1.0)
    with pytest.raises(ValueError):
        framerate_to_fraction(fps=-1000.0)
    with pytest.raises(ValueError):
        framerate_to_fraction(fps=MAX_FPS_DELTA / 2)
    # Reject framerates too small for equality testing or potential divide by zero situations.
    with pytest.raises(ValueError):
        assert framerate_to_fraction(fps=MAX_FPS_DELTA)


def test_precision_truncation():
    """Truncating must drop the extra digits, never round up into the last digit that is kept."""
    # 1.99996667s, e.g. a frame position from a 90 kHz time base.
    tc = Timecode(pts=179997, time_base=Fraction(1, 90000))
    assert tc.get_timecode(precision=3, use_rounding=False) == "00:00:01.999"
    assert tc.get_timecode(precision=2, use_rounding=False) == "00:00:01.99"
    assert tc.get_timecode(precision=0, use_rounding=False) == "00:00:01"
    assert tc.get_timecode(precision=3, use_rounding=True) == "00:00:02.000"

    # Frame 911 is at 37.996s.
    tc = Timecode(911, Fraction(1001, 24000))
    assert tc.get_timecode(precision=1, use_rounding=False) == "00:00:37.9"
    assert tc.get_timecode(precision=1, use_rounding=True) == "00:00:38.0"

    tc = Timecode(pts=5999996, time_base=Fraction(1, 100000))
    assert tc.get_timecode(use_rounding=False) == "00:00:59.999"

    # Float error must not truncate exact values down, e.g. 504 / (24000 / 1001) == 21.021.
    tc = Timecode(pts=504, time_base=Fraction(1001, 24000))
    assert tc.get_timecode(precision=3, use_rounding=False) == "00:00:21.021"
    tc = Timecode(pts=6129, time_base=Fraction(1, 100))
    assert tc.get_timecode(precision=2, use_rounding=False) == "00:01:01.29"


def test_precision_truncation_matches_exact_arithmetic():
    """Truncation must give the exact answer at any precision, including large timestamps."""
    # Float error is larger for big values at high precision: 8192.826s at 1/1000 time base.
    tc = Timecode(pts=8192826, time_base=Fraction(1, 1000))
    assert tc.get_timecode(precision=3, use_rounding=False) == "02:16:32.826"
    assert tc.get_timecode(precision=6, use_rounding=False) == "02:16:32.826000"

    def exact(secs: Fraction, precision: int) -> str:
        units = math.floor(secs * 10**precision)
        secs, fraction = divmod(units, 10**precision)
        hrs, secs = divmod(secs, 3600)
        mins, secs = divmod(secs, 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}" + (
            f".{fraction:0{precision}d}" if precision else ""
        )

    rng = random.Random(0)
    precisions = (0, 1, 3, 6)
    for time_base in (
        Fraction(1, 1000),
        Fraction(1, 90000),
        Fraction(1, 24000),
        Fraction(1001, 30000),
    ):
        for _ in range(500):
            pts = rng.randrange(0, 400_000_000)
            tc = Timecode(pts=pts, time_base=time_base)
            for precision in precisions:
                assert tc.get_timecode(precision=precision, use_rounding=False) == exact(
                    pts * time_base, precision
                ), (pts, time_base, precision)

    # CFR fixtures use the exact frame period as their timestamp unit.
    for fps in (Fraction(24000, 1001), Fraction(30000, 1001), Fraction(25)):
        for _ in range(500):
            frame = rng.randrange(0, 10_000_000)
            tc = Timecode(pts=frame, time_base=1 / fps)
            for precision in precisions:
                assert tc.get_timecode(precision=precision, use_rounding=False) == exact(
                    Fraction(frame) / fps, precision
                ), (frame, fps, precision)


@pytest.mark.parametrize(
    "pts,time_base,expected",
    [
        (0, Fraction(1, 1000), "00:00:00.000"),
        (125, Fraction(1, 100), "00:00:01.250"),
        (45296789, Fraction(1, 1000), "12:34:56.789"),
        (1, Fraction(1001, 24000), "00:00:00.042"),
        (360000, Fraction(1), "100:00:00.000"),
    ],
)
def test_timecode_get_timecode(pts, time_base, expected):
    """Format observed timestamps directly, including rational bases and long runtimes."""
    assert Timecode(pts, time_base).get_timecode() == expected


@pytest.mark.parametrize(
    "seconds,precision,use_rounding,expected",
    [
        ("0.11", 2, True, "00:00:00.11"),
        ("0.99", 1, True, "00:00:01.0"),
        ("0.99", 1, False, "00:00:00.9"),
        ("0.99", 0, True, "00:00:01"),
        ("0.99", 0, False, "00:00:00"),
        ("1.5", 0, True, "00:00:02"),
        ("2.5", 0, True, "00:00:02"),
        ("0.0005", 3, True, "00:00:00.000"),
        ("0.0015", 3, True, "00:00:00.002"),
        ("0.0025", 3, True, "00:00:00.002"),
        ("0.9995", 3, True, "00:00:01.000"),
        ("59.9995", 3, True, "00:01:00.000"),
        ("3599.9995", 3, True, "01:00:00.000"),
        ("1/3", 6, True, "00:00:00.333333"),
        ("2/3", 6, True, "00:00:00.666667"),
        ("2/3", 6, False, "00:00:00.666666"),
        ("1.000000000000000001", 18, True, "00:00:01.000000000000000001"),
        ("1.000000000000000001", 18, False, "00:00:01.000000000000000001"),
    ],
)
def test_timecode_get_timecode_precision(seconds, precision, use_rounding, expected):
    """Round exact ties to even and carry through boundaries without float conversion."""
    value = Fraction(seconds)
    timecode = Timecode(value.numerator, Fraction(1, value.denominator))
    assert timecode.get_timecode(precision=precision, use_rounding=use_rounding) == expected


@pytest.mark.parametrize(
    "seconds,expected",
    [
        ("1.23499", "00:00:01.234"),
        ("0.99996", "00:00:00.999"),
        ("59.99996", "00:00:59.999"),
        ("3599.99996", "00:59:59.999"),
    ],
)
def test_timecode_get_timecode_truncation_regression(seconds, expected):
    """Truncation must not round an extra decimal place before discarding it."""
    value = Fraction(seconds)
    timecode = Timecode(value.numerator, Fraction(1, value.denominator))
    assert timecode.get_timecode(use_rounding=False) == expected


@pytest.mark.parametrize(
    "seconds,use_rounding,expected",
    [
        ("-1.23499", True, "-00:00:01.235"),
        ("-1.23499", False, "-00:00:01.234"),
        ("-59.9995", True, "-00:01:00.000"),
        ("-0.0001", True, "00:00:00.000"),
        ("-0.0001", False, "00:00:00.000"),
        ("-0.001", True, "-00:00:00.001"),
        ("-0.001", False, "-00:00:00.001"),
        ("-4000", True, "-01:06:40.000"),
        ("-4000", False, "-01:06:40.000"),
    ],
)
def test_timecode_get_timecode_negative_timestamps(seconds, use_rounding, expected):
    """Preserve negative timestamp signs, but do not emit negative zero."""
    value = Fraction(seconds)
    timecode = Timecode(value.numerator, Fraction(1, value.denominator))
    assert timecode.get_timecode(use_rounding=use_rounding) == expected


@pytest.mark.parametrize("precision", [-1, -3])
@pytest.mark.parametrize("use_rounding", [True, False])
def test_timecode_get_timecode_rejects_negative_precision(precision, use_rounding):
    with pytest.raises(ValueError, match="precision must be non-negative"):
        Timecode(0, Fraction(1, 1000)).get_timecode(precision=precision, use_rounding=use_rounding)


def test_ntsc_framerate_detection():
    """Common NTSC framerates should be detected from float values."""
    assert framerate_to_fraction(23.976023976023978) == Fraction(24000, 1001)
    assert framerate_to_fraction(29.97002997002997) == Fraction(30000, 1001)
    assert framerate_to_fraction(59.94005994005994) == Fraction(60000, 1001)
    assert framerate_to_fraction(119.88011988011988) == Fraction(120000, 1001)
    assert framerate_to_fraction(59.94) == Fraction(60000, 1001)
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


class _StubRational:
    """Minimal `numbers.Rational` that only exposes numerator/denominator, mirroring
    `av.AVRational` from PyAV 19+ (which has no `__int__`, `__round__`, or `__floor__`)."""

    def __init__(self, numerator: int, denominator: int):
        self.numerator = numerator
        self.denominator = denominator


numbers.Rational.register(_StubRational)


def test_framerate_to_fraction_accepts_rational():
    """Any `numbers.Rational` (not just `Fraction`) must be converted exactly. PyAV >= 19.0
    reports frame rates and time bases as the `av.AVRational` type."""
    for num, den in [(30000, 1001), (24000, 1001), (25, 1)]:
        result = framerate_to_fraction(_StubRational(num, den))  # type: ignore[arg-type]
        assert isinstance(result, Fraction)
        assert result == Fraction(num, den)
    with pytest.raises(ValueError):
        framerate_to_fraction(_StubRational(0, 1))  # type: ignore[arg-type]


def test_timecode_normalizes_rational_time_base():
    tc = Timecode(pts=1001, time_base=_StubRational(1, 30000))  # type: ignore[arg-type]
    assert isinstance(tc.time_base, Fraction)
    assert tc.time_base == Fraction(1, 30000)
    assert tc.seconds == Fraction(1001, 30000)


def test_min_scene_len_accepts_timecode_like():
    """Detector minima and FlashFilter lengths accept frame and time inputs."""
    from scenedetect.detector import FlashFilter
    from scenedetect.detectors import ContentDetector

    # FlashFilter: integer frames, seconds, strings and Timecode are valid.
    FlashFilter(mode=FlashFilter.Mode.MERGE, length=15)
    FlashFilter(mode=FlashFilter.Mode.MERGE, length=0.5)
    FlashFilter(mode=FlashFilter.Mode.MERGE, length="00:00:00.500")
    FlashFilter(
        mode=FlashFilter.Mode.MERGE,
        length=Timecode(pts=500, time_base=Fraction(1, 1000)),
    )

    # ContentDetector: same.
    ContentDetector(min_scene_len=15)
    ContentDetector(min_scene_len=0.5)
    ContentDetector(min_scene_len="00:00:00.500")
    ContentDetector(min_scene_len=Timecode(pts=500, time_base=Fraction(1, 1000)))


# FlashFilter NTSC regression tests (#577). An integer `length` (frames) was converted to seconds
# with `length / float(frame_rate)`, which can land one ulp above the true value at NTSC rates, so
# a gap of exactly N frames failed the `>=` check and the cut was dropped. These tests feed
# FlashFilter the exact positions a backend reports for an NTSC stream (no video file needed).
NTSC_RATES = (
    Fraction(30000, 1001),
    Fraction(60000, 1001),
)


def _ntsc_pts_position(frame: int, fps: Fraction) -> FramePosition:
    """Position of `frame` as a PTS-exact backend (e.g. PyAV) reports it.

    For an NTSC rate ``num/1001`` with ``time_base = 1/num`` each frame advances exactly ``1001``
    PTS units.
    """
    return FramePosition(
        timecode=Timecode(pts=frame * 1001, time_base=Fraction(1, fps.numerator)),
        frame_number=frame,
    )


def _ntsc_microsecond_position(frame: int, fps: Fraction) -> FramePosition:
    """Position of `frame` as the OpenCV backend reports it, rounded to whole microseconds."""
    us = round(frame * 1_000_000 / fps)
    return FramePosition(
        timecode=Timecode(pts=us, time_base=Fraction(1, 1_000_000)),
        frame_number=frame,
    )


@pytest.mark.parametrize("fps", NTSC_RATES)
@pytest.mark.parametrize("mode", [FlashFilter.Mode.MERGE, FlashFilter.Mode.SUPPRESS])
def test_flashfilter_emits_cut_every_n_frames_at_ntsc(fps: Fraction, mode: FlashFilter.Mode):
    """A cut exactly `length` frames after the previous one is kept at NTSC rates."""
    flash_filter = FlashFilter(mode=mode, length=15)
    emitted = []
    for frame in range(300):
        emitted += flash_filter.filter(
            _ntsc_pts_position(frame, fps), above_threshold=frame > 0 and frame % 15 == 0
        )
    assert [t.frame_number for t in emitted] == list(range(15, 300, 15))


@pytest.mark.parametrize("fps", NTSC_RATES)
def test_frame_position_subtraction_preserves_ntsc_gap(fps: Fraction):
    """Subtracting NTSC positions preserves the exact frame count and elapsed time."""
    gap = _ntsc_pts_position(115, fps) - _ntsc_pts_position(100, fps)
    assert gap == FrameDuration(frames=15, elapsed=Fraction(15) / fps)


@pytest.mark.parametrize("fps", NTSC_RATES)
@pytest.mark.parametrize("mode", [FlashFilter.Mode.MERGE, FlashFilter.Mode.SUPPRESS])
def test_flashfilter_keeps_cuts_on_microsecond_positions(fps: Fraction, mode: FlashFilter.Mode):
    """OpenCV rounds positions to microseconds, so an N-frame gap can be 1 us short of N / fps.

    With min_scene_len=17 on 29.97 fps (the example in #577) cuts were dropped.
    """
    flash_filter = FlashFilter(mode=mode, length=17)
    emitted = []
    for frame in range(17 * 20):
        emitted += flash_filter.filter(
            _ntsc_microsecond_position(frame, fps), above_threshold=frame > 0 and frame % 17 == 0
        )
    assert [t.frame_number for t in emitted] == list(range(17, 17 * 20, 17))
