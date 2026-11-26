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

"""Tests for frame-position helpers, ordering and duration arithmetic."""

from dataclasses import FrozenInstanceError, dataclass
from fractions import Fraction

import pytest

from scenedetect.common import FrameDuration, FramePosition, Timecode


def test_frame_position_helpers_keep_frames_and_time_separate():
    position = FramePosition(Timecode(2, Fraction(1, 3)), 17)

    assert position.frame_number == position.get_frames() == 17
    assert position.pts == 2
    assert position.time_base == Fraction(1, 3)
    assert position.timecode.seconds == Fraction(2, 3)
    assert isinstance(position.timecode.seconds, Fraction)

    seconds = position.seconds
    legacy_seconds = position.get_seconds()
    assert isinstance(seconds, float)
    assert isinstance(legacy_seconds, float)
    assert seconds == legacy_seconds == pytest.approx(2 / 3)
    assert position.get_timecode() == "00:00:00.667"
    assert str(position) == "00:00:00.667"
    expected = position.timecode.get_timecode(precision=4, use_rounding=False)
    actual = position.get_timecode(precision=4, use_rounding=False)
    assert actual == expected

    with pytest.warns(DeprecationWarning, match="frame_number") as caught:
        assert position.frame_num == position.frame_number == position.get_frames() == 17
    assert len(caught) == 1
    assert caught[0].filename == __file__


def test_frame_position_ordering_uses_ordinals():
    first = FramePosition(Timecode(1000, Fraction(1, 1000)), 10)
    second = FramePosition(Timecode(1000, Fraction(1, 1000)), 11)
    third = FramePosition(Timecode(900, Fraction(1, 1000)), 12)

    assert sorted([third, second, first]) == [first, second, third]
    assert first < second < third
    assert third > second > first


def test_frame_position_equality_and_hashing_use_both_fields():
    original = FramePosition(Timecode(1000, Fraction(1, 1000)), 10)
    same = FramePosition(Timecode(1000, Fraction(1, 1000)), 10)
    different_frame = FramePosition(original.timecode, 11)
    different_time = FramePosition(Timecode(1001, Fraction(1, 1000)), 10)

    assert original == same
    assert hash(original) == hash(same)
    assert original != different_frame
    assert original != different_time
    assert {original: "saved"}[same] == "saved"
    assert len({original, same, different_frame, different_time}) == 3

    assert not original < different_time
    assert not original > different_time
    assert not different_time < original
    assert not different_time > original


def test_frame_position_equality_distinguishes_subclasses():
    @dataclass(frozen=True)
    class TaggedPosition(FramePosition):
        tag: str

    original = FramePosition(Timecode(1000, Fraction(1, 1000)), 10)
    tagged = TaggedPosition(original.timecode, original.frame_number, "tag")
    assert original != tagged
    assert tagged != original


def test_frame_position_subtraction_uses_exact_time_bases():
    start = FramePosition(Timecode(1, Fraction(1, 3)), 10)
    end = FramePosition(Timecode(7, Fraction(1, 10)), 13)

    duration = end - start
    assert duration == FrameDuration(frames=3, elapsed=Fraction(11, 30))
    assert isinstance(duration.elapsed, Fraction)


def test_frame_position_subtraction_allows_equal_timestamps():
    start = FramePosition(Timecode(500, Fraction(1, 1000)), 10)
    end = FramePosition(Timecode(1000, Fraction(1, 2000)), 12)

    duration = end - start
    assert duration == FrameDuration(frames=2, elapsed=Fraction(0))
    assert isinstance(duration.elapsed, Fraction)


def test_frame_position_subtraction_from_itself_is_zero():
    position = FramePosition(Timecode(1, Fraction(1, 3)), 10)

    duration = position - position
    assert duration == FrameDuration(frames=0, elapsed=Fraction(0))
    assert isinstance(duration.elapsed, Fraction)


@pytest.mark.parametrize(
    ("end_frame", "end_pts"),
    [(9, 2000), (11, 500)],
    ids=["negative-frames", "negative-time"],
)
def test_frame_position_subtraction_rejects_negative_results(end_frame, end_pts):
    start = FramePosition(Timecode(1000, Fraction(1, 1000)), 10)
    end = FramePosition(Timecode(end_pts, Fraction(1, 1000)), end_frame)

    with pytest.raises(ArithmeticError, match="negative"):
        _ = end - start


@pytest.mark.parametrize(
    "other",
    [1, Timecode(1, Fraction(1, 1000)), FrameDuration(1, Fraction(1, 1000))],
)
def test_frame_position_subtraction_requires_another_position(other):
    position = FramePosition(Timecode(1000, Fraction(1, 1000)), 10)

    assert position.__sub__(other) is NotImplemented
    with pytest.raises(TypeError):
        _ = position - other


@pytest.mark.parametrize(
    ("value", "attribute", "replacement"),
    [
        (FramePosition(Timecode(2, Fraction(1, 3)), 17), "frame_number", 18),
        (FrameDuration(3, Fraction(11, 30)), "elapsed", Fraction(2, 3)),
    ],
)
def test_positions_and_durations_are_immutable(value, attribute, replacement):
    with pytest.raises(FrozenInstanceError):
        setattr(value, attribute, replacement)
