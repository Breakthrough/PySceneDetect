"""Unit-preserving frame-or-time input parsing."""

from fractions import Fraction

import numpy
import pytest

from scenedetect.common import FramePosition, Timecode, parse_frame_or_time
from scenedetect.detectors.threshold_detector import ThresholdDetector


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, 0),
        (15, 15),
        ("15", 15),
        (" 15 ", 15),
        (0.0, Fraction(0)),
        (15.0, Fraction(15)),
        (0.6, Fraction(3, 5)),
        ("15.0", Fraction(15)),
        ("15s", Fraction(15)),
        (" 0.6s ", Fraction(3, 5)),
        (".5", Fraction(1, 2)),
        ("1.", Fraction(1)),
        ("00:00:00.600", Fraction(3, 5)),
        ("01:02.500", Fraction(125, 2)),
        ("01:23:45.678", Fraction(5025678, 1000)),
        ("0.000000000000000001s", Fraction(1, 10**18)),
        (Timecode(1001, Fraction(1, 24000)), Fraction(1001, 24000)),
        (Timecode(1, Fraction(1)), Fraction(1)),
    ],
)
def test_parse_preserves_units(value, expected):
    result = parse_frame_or_time(value)
    assert result == expected
    assert type(result) is type(expected)


@pytest.mark.parametrize(
    "value",
    [
        -1,
        -0.5,
        float("inf"),
        float("-inf"),
        float("nan"),
        "",
        " ",
        "-1",
        "-0.5s",
        "nan",
        "inf",
        "1/2",
        "1e3",
        "1.2.3",
        "s",
        "00:60:00",
        "60:00",
        "00:00:60",
        "00:00:60.001",
        "00::01",
        "00:00:01:00",
        "00:00:01s",
        Timecode(-1, Fraction(1, 10)),
        Timecode(1, Fraction(0)),
        Timecode(1, Fraction(-1, 10)),
    ],
)
def test_parse_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_frame_or_time(value)


@pytest.mark.parametrize("value", [True, False, None, [], Fraction(1, 2)])
def test_parse_rejects_unsupported_types(value):
    with pytest.raises(TypeError):
        parse_frame_or_time(value)


def test_threshold_initializes_last_scene_cut():
    position = FramePosition(Timecode(0, Fraction(1, 25)), 0)
    detector = ThresholdDetector()
    assert detector.process_frame(position, numpy.full((2, 2, 3), 100)) == []
    assert detector.last_scene_cut == position


def test_threshold_post_process_without_frames():
    detector = ThresholdDetector(add_final_scene=True)
    position = FramePosition(Timecode(0, Fraction(1, 25)), 0)
    assert detector.post_process(position) == []
