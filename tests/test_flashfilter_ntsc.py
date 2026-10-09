#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2026 PySceneDetect Contributors.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""FlashFilter NTSC regression tests (#577)

ContentDetector (and any detector that routes through FlashFilter) must emit a
cut exactly ``min_scene_len`` frames after the previous one, even at NTSC rates
(30000/1001 and 60000/1001 fps) where ``float(frame_rate)`` is not exact. The
regression was introduced in 0.7 when FlashFilter moved to time units: an
integer frame length was converted to seconds with ``length / float(frame_rate)``,
which can land one ulp above the true value, so a gap of exactly N frames failed
the ``>=`` comparison and the cut was dropped.

These tests feed FlashFilter the exact PTS positions a backend reports for an
NTSC stream (no video file needed) and assert that both MERGE and SUPPRESS modes
emit a cut every 15 frames.
"""

from fractions import Fraction

import pytest

from scenedetect.common import FrameTimecode, Timecode
from scenedetect.detector import FlashFilter

# NTSC rates whose frame duration is not exactly representable as a float.
NTSC_RATES = (
    Fraction(30000, 1001),
    Fraction(60000, 1001),
)


def _at(frame: int, fps: Fraction) -> FrameTimecode:
    """Position of `frame` as a PTS-exact backend (e.g. PyAV) reports it.

    For an NTSC rate ``num/1001`` the frame duration is ``1001/num`` seconds, so
    with ``time_base = 1/num`` each frame advances exactly ``1001`` PTS units.
    """
    return FrameTimecode(Timecode(pts=frame * 1001, time_base=Fraction(1, fps.numerator)), fps)


@pytest.mark.parametrize("fps", NTSC_RATES)
@pytest.mark.parametrize("mode", [FlashFilter.Mode.MERGE, FlashFilter.Mode.SUPPRESS])
def test_flashfilter_emits_cut_every_n_frames_at_ntsc(fps: Fraction, mode: FlashFilter.Mode):
    """A cut exactly `length` frames after the previous one is kept at NTSC rates."""
    flash_filter = FlashFilter(mode=mode, length=15)
    emitted = []
    for frame in range(300):
        emitted += flash_filter.filter(
            _at(frame, fps), above_threshold=frame > 0 and frame % 15 == 0
        )
    assert [t.frame_num for t in emitted] == list(range(15, 300, 15))


@pytest.mark.parametrize("fps", NTSC_RATES)
def test_flashfilter_keeps_exact_gap_at_ntsc(fps: Fraction):
    """The exact N-frame gap must satisfy the minimum-length check at NTSC rates."""
    gap = _at(115, fps) - _at(100, fps)
    assert gap.frame_num == 15
    # The float conversion the bug used is one ulp high, so the exact comparison
    # must not go through it.
    assert gap >= 15


def _at_microseconds(frame: int, fps: Fraction) -> FrameTimecode:
    """Position of `frame` as the OpenCV backend reports it, rounded to whole microseconds."""
    us = round(frame * 1_000_000 / fps)
    return FrameTimecode(Timecode(pts=us, time_base=Fraction(1, 1_000_000)), fps)


@pytest.mark.parametrize("fps", NTSC_RATES)
@pytest.mark.parametrize("mode", [FlashFilter.Mode.MERGE, FlashFilter.Mode.SUPPRESS])
def test_flashfilter_keeps_cuts_on_microsecond_positions(fps: Fraction, mode: FlashFilter.Mode):
    """OpenCV rounds positions to microseconds, so an N-frame gap can be 1 us short of N / fps.

    With min_scene_len=17 on 29.97 fps (the example in #577) cuts were dropped; comparing frame
    counts keeps them.
    """
    flash_filter = FlashFilter(mode=mode, length=17)
    emitted = []
    for frame in range(17 * 20):
        emitted += flash_filter.filter(
            _at_microseconds(frame, fps), above_threshold=frame > 0 and frame % 17 == 0
        )
    assert [t.frame_num for t in emitted] == list(range(17, 17 * 20, 17))
