#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Solid-color interval detection using synthetic BGR frames."""

import numpy as np
import pytest

from scenedetect import FrameTimecode
from scenedetect.detector import SceneDetector
from scenedetect.detectors import SolidColorDetector


def _solid(color=(0, 0, 0)):
    return np.full((4, 4, 3), color, dtype=np.uint8)


def _detail():
    image = _solid()
    image[::2] = 255
    return image


def _intervals(detector):
    intervals = detector.get_intervals()
    assert all(isinstance(tc, FrameTimecode) for pair in intervals for tc in pair)
    return [(start.frame_num, end.frame_num) for start, end in intervals]


def _detect(frames, *, start=0, step=1, **kwargs):
    detector = SolidColorDetector(**kwargs)
    assert isinstance(detector, SceneDetector)
    timecode = FrameTimecode(start, fps=24.0)
    for index, frame in enumerate(frames):
        timecode = FrameTimecode(start + index * step, fps=24.0)
        assert detector.process_frame(timecode, frame) == []
    assert detector.post_process(timecode) == []
    return detector


@pytest.mark.parametrize(
    "solid_flags, expected",
    [
        ([], []),
        ([False] * 4, []),
        ([True] * 4, [(0, 4)]),
        ([True, True, False, False], [(0, 2)]),
        ([False, False, True, True], [(2, 4)]),
        ([False, True, True, False], [(1, 3)]),
        ([True, True, False, True, True, False, True, True], [(0, 2), (3, 5), (6, 8)]),
        ([True, False, True], []),
    ],
)
def test_interval_boundaries(solid_flags, expected):
    assert (
        _intervals(_detect([_solid() if solid else _detail() for solid in solid_flags])) == expected
    )


def test_any_color_and_color_changes_form_one_run():
    colors = [(0, 0, 0), (255, 255, 255), (0, 0, 255), (0, 255, 0), (255, 0, 0), (23, 81, 170)]
    assert _intervals(_detect([_solid(color) for color in colors], threshold=0)) == [(0, 6)]


@pytest.mark.parametrize("channel", [0, 1, 2])
def test_zero_threshold_requires_exact_uniformity_on_large_odd_size_frame(channel):
    frame = np.full((1919, 1079, 3), (21, 123, 253), dtype=np.uint8)
    assert _intervals(_detect([frame, frame], threshold=0)) == [(0, 2)]
    frame[-1, -1, channel] += 1
    assert _intervals(_detect([frame, frame], threshold=0)) == []


@pytest.mark.parametrize("length, expected", [(1, []), (2, [(0, 2)]), (3, [(0, 3)])])
@pytest.mark.parametrize("trailing", [False, True])
def test_min_frames_boundary(length, expected, trailing):
    frames = [_solid()] * length
    if not trailing:
        frames.append(_detail())
    assert _intervals(_detect(frames)) == expected


def test_minimum_one_keeps_single_frame_runs():
    assert _intervals(_detect([_solid(), _detail(), _solid()], min_frames=1)) == [(0, 1), (2, 3)]


def test_min_frames_counts_observations_instead_of_elapsed_frames():
    assert _intervals(_detect([_solid(), _solid()], step=5, min_frames=3)) == []
    assert _intervals(_detect([_solid(), _solid()], start=10, step=5)) == [(10, 16)]


@pytest.mark.parametrize("channel", [0, 1, 2])
@pytest.mark.parametrize("threshold, expected", [(0.0, []), (1.999, []), (2.0, [(0, 2)])])
def test_inclusive_threshold_uses_maximum_channel_deviation(channel, threshold, expected):
    # Half the pixels differ by four in just one channel: its population stddev is exactly two.
    frame = _solid((100, 100, 100))
    frame[::2, :, channel] = 104
    assert _intervals(_detect([frame, frame], threshold=threshold)) == expected


def test_upper_threshold_boundary():
    assert _intervals(_detect([_detail(), _detail()], threshold=127.5)) == [(0, 2)]


@pytest.mark.parametrize(
    "threshold",
    [-0.01, 127.51, 10**400, float("nan"), float("inf"), -float("inf"), None, "2", True],
)
def test_invalid_threshold_rejected(threshold):
    with pytest.raises(ValueError, match="threshold"):
        SolidColorDetector(threshold=threshold)


@pytest.mark.parametrize("minimum", [0, -1, 1.5, 2.0, True, None, "2", float("inf")])
def test_invalid_min_frames_rejected(minimum):
    with pytest.raises(ValueError, match="min_frames"):
        SolidColorDetector(min_frames=minimum)


def test_pending_interval_and_repeated_flush():
    detector = SolidColorDetector()
    for index in (10, 11):
        assert detector.process_frame(FrameTimecode(index, fps=24.0), _solid()) == []
    assert detector.get_intervals() == []
    # On an early stop, the decoder can have read ahead of the detector.
    assert detector.post_process(FrameTimecode(15, fps=24.0)) == []
    assert _intervals(detector) == [(10, 12)]
    assert detector.post_process(FrameTimecode(11, fps=24.0)) == []
    assert _intervals(detector) == [(10, 12)]


def test_intervals_are_independent_snapshots():
    detector = _detect([_solid(), _solid()])
    result = detector.get_intervals()
    start = result[0][0]
    start += 1
    result.clear()
    assert _intervals(detector) == [(0, 2)]
