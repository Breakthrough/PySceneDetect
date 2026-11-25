#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect scenedetect.backend.pyav Tests

This file includes unit tests for the scenedetect.backend.pyav module that implements the
VideoStreamAv ('pyav') backend. These tests validate behaviour specific to this backend.

For VideoStream tests that validate conformance, see test_video_stream.py.
"""

import gc
import itertools
from fractions import Fraction
from types import SimpleNamespace
from typing import cast

import av
import pytest

from scenedetect import SceneManager
from scenedetect.backends.pyav import (
    MAX_CONSECUTIVE_DECODE_FAILURES,
    MAX_SEEK_PROBE_FRAMES,
    VideoStreamAv,
    _to_fraction,
)
from scenedetect.common import FramePosition, Timecode
from scenedetect.detectors import ContentDetector
from scenedetect.video_stream import FrameNumbering, SeekError


def test_video_stream_pyav_bytesio(test_video_file: str):
    """Test that VideoStreamAv works with a BytesIO input in addition to a path."""
    # Mode must be binary!
    with open(test_video_file, mode="rb") as video_file:
        stream = VideoStreamAv(path_or_io=video_file, threading_mode=None)
        assert stream.is_seekable
        stream.seek(50)
        for _ in range(10):
            assert stream.read() is not False
        # A file-like object supplied by the caller belongs to the caller and must survive the
        # stream being finalized.
        del stream
        gc.collect()
        assert not video_file.closed


def test_video_stream_pyav_del_closes_owned_file_handle(test_video_file: str):
    """When opened from a path, the stream owns the file handle it created and must close it
    when finalized (#568). Otherwise the handle is only reclaimed by the file object's own
    finalizer, which emits a ResourceWarning under `python -X dev`."""
    stream = VideoStreamAv(test_video_file, threading_mode=None)
    handle = stream._io
    assert not handle.closed
    del stream
    gc.collect()
    assert handle.closed


def test_close_leaves_caller_file_open(test_video_file: str, auto_close):
    """`close()` must not close a file-like object supplied by the caller (#568), and must drop
    the last decoded frame and position."""
    with open(test_video_file, mode="rb") as video_file:
        stream = auto_close(VideoStreamAv(path_or_io=video_file, threading_mode=None))
        assert stream.read(decode=False) is not False
        assert stream.read(decode=False) is not False
        assert stream.frame_number == 1
        assert isinstance(stream.position, FramePosition)
        assert stream.position_ms > 0.0
        stream.close()
        assert not video_file.closed
        assert stream.frame_number == -1
        assert stream.position is None
        assert stream.position_ms == 0.0


def test_close_releases_owned_file_handle(
    test_video_file: str, monkeypatch: pytest.MonkeyPatch, auto_close
):
    """`close()` must release the file handle the stream opened from a path (#568), without
    waiting for the stream to be finalized."""
    opened = []

    # Record the handle as the backend opens it, rather than reaching into the stream.
    def recording_open(*args, **kwargs):
        handle = open(*args, **kwargs)  # noqa: SIM115
        opened.append(handle)
        return handle

    monkeypatch.setattr("scenedetect.backends.pyav.open", recording_open, raising=False)
    stream = auto_close(VideoStreamAv(test_video_file, threading_mode=None))
    assert len(opened) == 1
    assert not opened[0].closed
    stream.close()
    assert opened[0].closed


def _make_invalid_data_error() -> Exception:
    # AVERROR_INVALIDDATA ("Invalid data found when processing input").
    return av.error.InvalidDataError(  # type: ignore[attr-defined]
        1094995529, "Invalid data found when processing input"
    )


class _FaultInjectingContainer:
    """Wraps an `av.InputContainer`, replacing `decode` to inject decode errors.
    `InputContainer.decode` itself is a read-only Cython attribute, so we swap the whole
    container for this proxy instead."""

    def __init__(self, container, decode):
        self._container = container
        self._decode = decode

    def decode(self, *args, **kwargs):
        return self._decode(self._container, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._container, name)


def test_read_tolerates_corrupt_frame(test_video_file: str, auto_close):
    """A decode error partway through the stream must be skipped, not stop decoding."""
    stream = auto_close(VideoStreamAv(test_video_file))
    injected = False

    def fault_injecting_decode(container, *args, **kwargs):
        nonlocal injected
        for frame_index, frame in enumerate(container.decode(*args, **kwargs)):
            if not injected and frame_index == 5:
                injected = True
                raise _make_invalid_data_error()
            yield frame

    stream._container = _FaultInjectingContainer(stream._container, fault_injecting_decode)
    for frame in range(20):
        assert stream.read(decode=False) is not False, f"Failed on frame {frame}!"
    assert injected
    assert stream.decode_failures == 1


def test_read_gives_up_after_consecutive_failures(test_video_file: str, caplog, auto_close):
    """After too many consecutive decode failures, read() must return False, not hang."""
    stream = auto_close(VideoStreamAv(test_video_file))

    def always_failing_decode(container, *args, **kwargs):
        raise _make_invalid_data_error()
        yield  # pragma: no cover - makes this a generator function.

    stream._container = _FaultInjectingContainer(stream._container, always_failing_decode)
    assert stream.read(decode=False) is False
    assert stream.decode_failures == MAX_CONSECUTIVE_DECODE_FAILURES
    # Giving up emits an ERROR log by design; verify it then clear it so the autouse
    # `no_logs_gte_error` fixture doesn't fail the test.
    assert any("consecutive" in record.message for record in caplog.records)
    caplog.clear()


def test_rationals_are_fractions(test_video_file: str, auto_close):
    """PyAV >= 19.0 returns `av.AVRational` for time bases and frame rates. The backend must
    convert to `Fraction` so downstream arithmetic (`round`, `int`) works properly."""
    stream = auto_close(VideoStreamAv(test_video_file))
    assert stream.read(decode=False) is not False
    assert isinstance(stream.frame_rate, Fraction)
    assert stream.frame_rate == Fraction(30000, 1001)
    assert isinstance(stream.rate, Fraction)
    assert isinstance(stream.time_base, Fraction)
    assert isinstance(stream.position, FramePosition)
    assert isinstance(stream.position.timecode.time_base, Fraction)
    assert stream.position_ms == 0.0
    assert stream.frame_number == 0


class _StubRational:
    """Stands in for `av.AVRational` (PyAV 19+): only `numerator`/`denominator`, no `__int__`."""

    def __init__(self, numerator: int, denominator: int):
        self.numerator = numerator
        self.denominator = denominator


def test_to_fraction_from_stub_rational():
    result = _to_fraction(_StubRational(30000, 1001))
    assert isinstance(result, Fraction)
    assert result == Fraction(30000, 1001)
    assert _to_fraction(Fraction(1, 24000)) == Fraction(1, 24000)


class _AttrOverridingProxy:
    """Forwards attribute access to the wrapped object except for the given overrides."""

    def __init__(self, wrapped, **overrides):
        self._wrapped = wrapped
        self._overrides = overrides

    def __getattr__(self, name):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._wrapped, name)


def test_duration_fallback_from_stream_duration(
    test_video_file: str, monkeypatch: pytest.MonkeyPatch, auto_close
):
    """Stream duration ticks are converted to seconds using the stream time base."""
    stream = auto_close(VideoStreamAv(test_video_file))
    real_stream = stream._video_stream
    assert real_stream.frames == 720
    fake_stream = _AttrOverridingProxy(
        real_stream,
        frames=0,
        container=SimpleNamespace(duration=None),
        duration=123,
        time_base=Fraction(1, 100),
    )
    monkeypatch.setattr(VideoStreamAv, "_video_stream", property(lambda self: fake_stream))
    assert stream._get_duration() == Fraction(123, 100)


@pytest.mark.parametrize("unset_dar", [None, Fraction(0, 1)], ids=["none", "zero"])
def test_aspect_ratio_unset_dar(
    test_video_file: str, unset_dar, monkeypatch: pytest.MonkeyPatch, auto_close
):
    """An unset display aspect ratio (None on PyAV < 19, AVRational(0, 1) on PyAV 19+) must be
    treated as square pixels rather than producing an aspect ratio of 0."""
    stream = auto_close(VideoStreamAv(test_video_file))
    width, height = stream.frame_size
    fake_ctx = SimpleNamespace(display_aspect_ratio=unset_dar, width=width, height=height)
    monkeypatch.setattr(VideoStreamAv, "_codec_context", property(lambda self: fake_ctx))
    assert stream.aspect_ratio == 1.0


@pytest.mark.parametrize(
    "guessed_rate, expected",
    [(_StubRational(30000, 1001), Fraction(30000, 1001)), (None, None)],
    ids=["stub-rational", "none"],
)
def test_rate_normalizes_stream_rational(
    test_video_file: str, guessed_rate, expected, monkeypatch: pytest.MonkeyPatch, auto_close
):
    """`rate` must return a `Fraction` for any rational type the stream reports (PyAV 19+ returns
    `av.AVRational`), and None when the stream has no guessed rate (PyAV < 19)."""
    stream = auto_close(VideoStreamAv(test_video_file))
    fake_stream = _AttrOverridingProxy(stream._video_stream, guessed_rate=guessed_rate)
    monkeypatch.setattr(VideoStreamAv, "_video_stream", property(lambda self: fake_stream))
    assert stream.rate == expected
    assert expected is None or isinstance(stream.rate, Fraction)


@pytest.mark.parametrize("time_base", [None, Fraction(0, 1)], ids=["none", "zero"])
def test_duration_fallback_unset_time_base(
    test_video_file: str, time_base, monkeypatch: pytest.MonkeyPatch, caplog, auto_close
):
    """With no frame count, no container duration, and an unset stream time base (None on
    PyAV < 19, AVRational(0, 1) on PyAV 19+), duration is reported as None with a warning.
    Native timestamp seeking in RELATIVE mode also requires a valid stream time base."""
    stream = auto_close(VideoStreamAv(test_video_file))
    fake_stream = _AttrOverridingProxy(
        stream._video_stream,
        frames=0,
        container=SimpleNamespace(duration=None),
        time_base=time_base,
    )
    monkeypatch.setattr(VideoStreamAv, "_video_stream", property(lambda self: fake_stream))
    assert stream._get_duration() is None
    assert any("duration unavailable" in record.message for record in caplog.records)
    with pytest.raises(SeekError, match="time base"):
        stream.seek(10.0)
    assert stream.frame_number == -1
    assert stream.position is None


#
# Streams without presentation timestamps
#
# By default, PyAV enables AVFMT_FLAG_GENPTS on every input container. For containers that only
# store decode timestamps (e.g. AVI), GENPTS synthesizes PTS from decode-order packet DTS, which
# produces out-of-order frame PTS once B-frames are reordered by the decoder. Raw elementary
# streams have no timestamps at all. Both fixtures below contain the first 480 frames of
# `goldeneye.mp4` re-encoded with B-frames, so the cuts detected on `goldeneye.mp4` over that
# range serve as the reference.
#

_BFRAMES_NUM_FRAMES = 480


def _detect_cuts(path: str, num_frames: int | None = None) -> list:
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    with VideoStreamAv(path) as video:
        scene_manager.detect_scenes(video, end_time=num_frames)
    return [scene[0] for scene in scene_manager.get_scene_list()[1:]]


def test_no_pts_avi_positions_monotonic(test_no_pts_avi: str, auto_close):
    """With GENPTS disabled the AVI falls back to DTS; positions must start at 0 and increase by
    one frame per read instead of following the decoder's reordering."""
    stream = auto_close(VideoStreamAv(test_no_pts_avi))
    assert stream.read() is not False
    assert isinstance(stream.position, FramePosition)
    assert stream.position.timecode.seconds == 0.0
    assert stream.position_ms == 0.0
    assert stream.frame_number == 0
    previous = stream.position
    for i in range(1, 99):
        assert stream.read() is not False
        assert isinstance(stream.position, FramePosition)
        assert stream.position.timecode.seconds > previous.timecode.seconds
        assert stream.frame_number == i
        previous = stream.position


def test_no_pts_avi_matches_mp4(test_no_pts_avi: str, test_movie_clip: str):
    """Cuts detected on the AVI must land on the same frames as on the mp4 it was encoded from.
    Before the fix the AVI cuts were one frame late and frame numbers were permuted."""
    expected = _detect_cuts(test_movie_clip, _BFRAMES_NUM_FRAMES)
    actual = _detect_cuts(test_no_pts_avi)
    assert len(expected) > 0
    assert [cut.frame_number for cut in actual] == [cut.frame_number for cut in expected]
    for cut, oracle in zip(actual, expected, strict=True):
        # The AVI time base (1/600) cannot represent 24000/1001 exactly, so allow a few ms.
        assert cut.timecode.seconds == pytest.approx(oracle.timecode.seconds, abs=0.005)


def test_no_pts_avi_seek(test_no_pts_avi: str, auto_close):
    """Seeking must give the same positions whether or not a frame was read first, since the DTS
    offset has to be probed separately when `seek()` is the first call."""
    read_first = auto_close(VideoStreamAv(test_no_pts_avi, frame_numbering=FrameNumbering.RELATIVE))
    assert read_first.read() is not False
    target = Timecode(pts=50, time_base=1 / read_first.frame_rate)
    read_first.seek(target)
    seek_first = auto_close(VideoStreamAv(test_no_pts_avi, frame_numbering=FrameNumbering.RELATIVE))
    seek_first.seek(target)
    for stream in (read_first, seek_first):
        assert stream.frame_number == -1
        assert stream.position is None
        assert stream.position_ms == 0.0
        assert stream.read() is not False
        assert stream.frame_number == 0
        assert isinstance(stream.position, FramePosition)
        elapsed = stream.position.timecode.seconds - target.seconds
        assert 0 <= elapsed <= (1 / stream.frame_rate + stream.position.timecode.time_base)
    assert read_first.position == seek_first.position


def test_no_pts_avi_reopen(test_no_pts_avi: str, auto_close):
    """Re-opening the container (`reset()`, and the AUTO threading EOF re-open) must keep GENPTS
    disabled, otherwise positions go out of order again partway through the video."""
    stream = auto_close(VideoStreamAv(test_no_pts_avi, threading_mode="AUTO"))
    for _ in range(10):
        assert stream.read() is not False
    stream.reset()
    assert stream.frame_number == -1
    for _ in range(10):
        assert stream.read() is not False
    assert stream.frame_number == 9
    assert isinstance(stream.position, FramePosition)
    previous, frames = stream.position, stream.frame_number + 1
    assert stream._handle_eof() is True
    assert stream.frame_number == 9
    assert stream.position == previous
    while stream.read() is not False:
        frames += 1
        assert isinstance(stream.position, FramePosition)
        assert stream.position.timecode.seconds > previous.timecode.seconds
        previous = stream.position
    # Not compared to `stream.frame_count`: this AVI declares a 600 Hz stream rate, so ffmpeg (and
    # OpenCV) report its frame count in ticks.
    assert frames == _BFRAMES_NUM_FRAMES


def test_raw_stream_without_timestamps_counts_frames(
    test_raw_h264: str, test_movie_clip: str, auto_close
):
    """A raw elementary stream has neither PTS nor DTS. Positions are then derived from the number
    of decoded frames (like the OpenCV backend) instead of every frame reporting time 0. Native
    timestamp seeking in RELATIVE mode raises `SeekError`; integer seeks count frames. Seeking
    to the start re-opens the stream."""
    stream = auto_close(VideoStreamAv(test_raw_h264))
    for i in range(10):
        assert stream.read() is not False
        assert stream.frame_number == i
        assert isinstance(stream.position, FramePosition)
        assert stream.position.timecode == Timecode(i, 1 / stream.frame_rate)
    assert stream._offset is None
    stream.seek(50)
    assert stream.frame_number == -1
    assert stream.position is None
    assert stream.read() is not False
    assert stream.frame_number == 0
    assert isinstance(stream.position, FramePosition)
    assert stream.position.timecode == Timecode(50, 1 / stream.frame_rate)

    with pytest.raises(SeekError, match="without timestamps"):
        stream.seek(2.0)
    stream.seek(0)
    assert stream.frame_number == -1
    assert stream.read() is not False
    assert stream.frame_number == 0
    expected = _detect_cuts(test_movie_clip, _BFRAMES_NUM_FRAMES)
    actual = _detect_cuts(test_raw_h264)
    assert [cut.frame_number for cut in actual] == [cut.frame_number for cut in expected]


#
# Missing timestamps and monotonicity
#


def _positions(stream: VideoStreamAv, frames) -> list[int]:
    """Feed synthetic `(pts, dts)` frames (one nominal frame period per tick) through the
    timestamp policy and return the resulting positions in ticks."""
    stream._offset = None
    stream._timecode = None
    stream._frames_decoded = 0
    stream._warned_non_monotonic = False
    positions = []
    for pts, dts in frames:
        frame = SimpleNamespace(pts=pts, dts=dts, time_base=1 / stream.frame_rate)
        stream._frames_decoded += 1
        stream._update_timecode(cast(av.VideoFrame, frame))
        assert stream._timecode is not None
        positions.append(stream._timecode.pts)
    return positions


def test_missing_timestamps_policy(
    test_video_file: str, monkeypatch: pytest.MonkeyPatch, caplog, auto_close
):
    """Each frame is placed at its PTS, else its DTS, else one frame after the previous one. The
    first two cases are the examples raised in PR #592 against choosing a single source for the
    whole stream from its first frame."""
    stream = auto_close(VideoStreamAv(test_video_file))
    fake_stream = _AttrOverridingProxy(stream._video_stream, start_time=0)
    monkeypatch.setattr(VideoStreamAv, "_video_stream", property(lambda self: fake_stream))

    # Frames before the first timestamp are spaced at the nominal frame rate, and later
    # timestamps are followed (relative to that estimate) rather than being ignored.
    assert _positions(stream, ((None, None), (2, None), (5, None), (7, None))) == [0, 1, 4, 6]
    # Frames without a PTS fall back to their DTS, and frames with neither advance one frame
    # period instead of extrapolating the previous (possibly large) step.
    assert _positions(stream, ((1, 0), (4, 3), (None, None), (None, None), (7, 6))) == [
        1,
        4,
        5,
        6,
        7,
    ]
    assert _positions(stream, ((0, 0), (None, 1), (None, None), (3, 3))) == [0, 1, 2, 3]
    # DTS-only streams start at time 0 regardless of the initial reorder delay.
    assert _positions(stream, ((None, 2), (None, 3), (None, 4), (None, 5))) == [0, 1, 2, 3]
    assert not [record for record in caplog.records if "backwards" in record.message]

    # A frame with a timestamp but no time base is placed like one without a timestamp.
    stream._offset = None
    stream._timecode = None
    stream._frames_decoded = 1
    frame = SimpleNamespace(pts=None, dts=2, time_base=None)
    stream._update_timecode(frame)
    assert stream._offset is None
    assert stream._timecode == Timecode(0, 1 / stream.frame_rate)
    assert stream.position is None


def test_timestamp_behind_estimate_warns(
    test_video_file: str, monkeypatch: pytest.MonkeyPatch, caplog, auto_close
):
    """A timestamp placed before the previous *estimated* position must warn too, since the
    reported positions go backwards either way (raised in PR #592)."""
    stream = auto_close(VideoStreamAv(test_video_file))
    fake_stream = _AttrOverridingProxy(stream._video_stream, start_time=0)
    monkeypatch.setattr(VideoStreamAv, "_video_stream", property(lambda self: fake_stream))
    frames = ((1, 0), (2, 1), (None, None), (None, None), (None, None), (4, 3))
    assert _positions(stream, frames) == [1, 2, 3, 4, 5, 4]
    warnings = [record for record in caplog.records if "backwards" in record.message]
    assert len(warnings) == 1
    assert "frame 6" in warnings[0].message


def test_missing_pts_ts_follows_timestamps(
    test_missing_pts_ts: str, test_vfr_drop3_video: str, caplog, auto_close
):
    """A VFR MPEG-TS whose first frames carry no timestamps, and later frames sporadically lack
    PTS, DTS or both, must follow the timestamps that are present rather than counting frames
    (which drifts over 3 seconds behind by the last frame of this file). Frames without any
    timestamp are placed one nominal frame period after the previous frame."""
    oracle = auto_close(VideoStreamAv(test_vfr_drop3_video))
    expected = []
    while oracle.read(decode=False) is not False:
        assert isinstance(oracle.position, FramePosition)
        expected.append(oracle.position.timecode.seconds)
    stream = auto_close(VideoStreamAv(test_missing_pts_ts))
    frame_period = 1.0 / float(stream.frame_rate)
    actual, has_timestamp = [], []
    while stream.read(decode=False) is not False:
        assert isinstance(stream.position, FramePosition)
        actual.append(stream.position.timecode.seconds)
        assert stream._frame is not None
        has_timestamp.append(stream._frame.pts is not None or stream._frame.dts is not None)
    assert len(actual) == len(expected) == 160
    assert has_timestamp[:4] == [False] * 4 and not all(has_timestamp[4:])
    assert actual[0] == 0.0
    assert all(later > earlier for earlier, later in itertools.pairwise(actual))
    # The leading frames without timestamps are spaced at the nominal frame rate, so positions
    # are only expected to match the source up to a constant offset (two dropped frames here).
    anchor = has_timestamp.index(True)
    shift = float(expected[anchor] - actual[anchor])
    assert 0 <= shift <= anchor * frame_period
    for i in range(anchor, len(actual)):
        if has_timestamp[i]:
            assert float(actual[i]) + shift == pytest.approx(float(expected[i]), abs=1e-3), i
        else:
            assert float(actual[i] - actual[i - 1]) == pytest.approx(frame_period, abs=1e-3), i
    assert not [record for record in caplog.records if "backwards" in record.message]


def test_seek_probe_without_timestamps(test_raw_h264: str, auto_close):
    """Native timestamp seeking fails without timestamps: the probe gives up after
    `MAX_SEEK_PROBE_FRAMES` frames, and later seeks fail immediately without probing again or
    re-opening the stream. The stream can still be read from the start after `reset()`."""
    stream = auto_close(VideoStreamAv(test_raw_h264))
    for _ in range(3):
        assert stream.read(decode=False) is not False
    with pytest.raises(SeekError, match="without timestamps"):
        stream.seek(1.0)
    assert stream._frames_decoded == MAX_SEEK_PROBE_FRAMES
    container = stream._container
    with pytest.raises(SeekError, match="without timestamps"):
        stream.seek(1.0)
    assert stream._container is container
    assert stream._frames_decoded == MAX_SEEK_PROBE_FRAMES
    stream.reset()
    assert stream.read(decode=False) is not False
    assert stream.frame_number == 0


def test_seek_to_start_reopens_stream(test_missing_pts_ts: str, auto_close):
    """`seek(0)` must re-open the stream rather than seeking the container. The first keyframe of
    this file has no timestamps, so seeking the container to time 0 lands on the next one (frame
    61, which only has a DTS). Before the offset is known that would anchor the offset there,
    shifting every position for the life of the stream; once it is known, the next `read()` would
    return frame 61 instead of the first frame (raised in PR #592). The first timestamp is on
    frame 5, so the offset is known after 5 reads."""
    sequential = auto_close(VideoStreamAv(test_missing_pts_ts))
    expected = []
    for _ in range(10):
        assert sequential.read(decode=False) is not False
        expected.append(sequential.position)
    for first_reads in (0, 2, 5, 70):
        stream = auto_close(VideoStreamAv(test_missing_pts_ts))
        for _ in range(first_reads):
            assert stream.read(decode=False) is not False
        stream.seek(0)
        assert stream.frame_number == -1
        assert stream.position is None
        actual = []
        for _ in range(10):
            assert stream.read(decode=False) is not False
            actual.append(stream.position)
        assert actual == expected, first_reads
        assert stream._offset == sequential._offset


def test_seek_walks_past_frames_without_timestamps(
    test_video_file: str, monkeypatch: pytest.MonkeyPatch, auto_close
):
    """If the keyframe a seek lands on carries no timestamp, its position is unknown, so the
    seek must keep reading until a frame with a timestamp is found before deciding it has reached
    the target. Otherwise the next `read()` after `seek(Timecode(200, 1 / stream.frame_rate))`
    would return frame 152."""
    stream = auto_close(VideoStreamAv(test_video_file, frame_numbering=FrameNumbering.RELATIVE))
    assert stream.read(decode=False) is not False
    real_container = stream._container
    strip_next = False

    def stripping_decode(*args, **kwargs):
        nonlocal strip_next
        for frame in real_container.decode(*args, **kwargs):
            if strip_next:
                strip_next = False
                frame.pts = None
                frame.dts = None
            yield frame

    def stripping_seek(*args, **kwargs):
        nonlocal strip_next
        strip_next = True
        return real_container.seek(*args, **kwargs)

    stream._container = _AttrOverridingProxy(
        real_container, decode=stripping_decode, seek=stripping_seek
    )
    target = Timecode(pts=200, time_base=1 / stream.frame_rate)
    stream.seek(target)
    assert stream.frame_number == -1
    assert stream.position is None
    assert stream.read(decode=False) is not False
    assert stream.frame_number == 0
    assert isinstance(stream.position, FramePosition)
    assert stream.position.timecode.seconds == target.seconds


def _true_frame_number(stream: VideoStreamAv, pts: int) -> int:
    """Zero-based number of the frame with presentation timestamp `pts` in a CFR stream."""
    video_stream = stream._video_stream
    elapsed = (pts - (video_stream.start_time or 0)) * _to_fraction(video_stream.time_base)
    return round(elapsed * stream.frame_rate)


def test_seek_reads_from_start_if_probe_passes_target(
    test_video_file: str, monkeypatch: pytest.MonkeyPatch, caplog, auto_close
):
    """Frames read while looking for a timestamp after a seek cannot be given back, so if the
    first timestamp found is already past the target, the seek must read forward from the start
    instead. Otherwise `seek(Timecode(2, 1 / stream.frame_rate))` on a stream whose frames 1-4
    have no timestamps would leave the next `read()` on frame 6 (raised in PR #592)."""
    stream = auto_close(VideoStreamAv(test_video_file, frame_numbering=FrameNumbering.RELATIVE))
    true_frame = None

    def stripping_decode(container, *args, **kwargs):
        nonlocal true_frame
        for frame in container.decode(*args, **kwargs):
            true_frame = _true_frame_number(stream, frame.pts)
            if true_frame < 4:
                frame.pts = None
                frame.dts = None
            yield frame

    # Strip the same frames from containers opened by `reset()`.
    open_container = stream._open_container
    monkeypatch.setattr(
        stream,
        "_open_container",
        lambda rewind=False: _FaultInjectingContainer(open_container(rewind), stripping_decode),
    )
    stream._container = _FaultInjectingContainer(stream._container, stripping_decode)
    target = Timecode(pts=2, time_base=1 / stream.frame_rate)
    stream.seek(target)
    assert stream.frame_number == -1
    assert stream.position is None
    assert stream.read(decode=False) is not False
    assert true_frame == 2
    assert stream.frame_number == 0
    assert isinstance(stream.position, FramePosition)
    assert stream.position.timecode.seconds == target.seconds
    assert not [record for record in caplog.records if "backwards" in record.message]


def test_seek_reads_from_start_if_probe_finds_no_timestamp(test_video_file: str, auto_close):
    """If no frame carries a timestamp within `MAX_SEEK_PROBE_FRAMES` frames after a seek, where
    the demuxer landed is unknown, so the seek must read forward from the start instead. Otherwise
    the frames would be estimated forward from the target and `seek(Timecode(265, 1 / stream.frame_rate))`
    would leave the next `read()` on frame 292 (raised in PR #592)."""
    stream = auto_close(VideoStreamAv(test_video_file))
    assert stream.read(decode=False) is not False
    real_container = stream._container
    strip_remaining = 0

    def stripping_decode(*args, **kwargs):
        nonlocal strip_remaining
        for frame in real_container.decode(*args, **kwargs):
            if strip_remaining > 0:
                strip_remaining -= 1
                frame.pts = None
                frame.dts = None
            yield frame

    def stripping_seek(*args, **kwargs):
        nonlocal strip_remaining
        strip_remaining = MAX_SEEK_PROBE_FRAMES
        return real_container.seek(*args, **kwargs)

    stream._container = _AttrOverridingProxy(
        real_container, decode=stripping_decode, seek=stripping_seek
    )
    target = Timecode(pts=265, time_base=1 / stream.frame_rate)
    stream.seek(target)
    assert stream.frame_number == -1
    assert stream.position is None
    assert stream.read(decode=False) is not False
    assert stream._frame is not None and stream._frame.pts is not None
    assert _true_frame_number(stream, stream._frame.pts) == 265
    assert stream.frame_number == 0
    assert isinstance(stream.position, FramePosition)
    assert stream.position.timecode.seconds == target.seconds


def test_missing_pts_ts_seek_matches_sequential(test_missing_pts_ts: str, caplog, auto_close):
    """Seeking must land where a sequential read would. The first keyframe of this file has no
    timestamps, so the demuxer lands on the next one (frame 61) for any target before it, which
    used to leave the stream there. The file is VFR, so the expected frame is found by time:
    targets are timestamps observed during sequential decoding; the next read must return
    the selected timestamp. Targets near the start also cover the missing-timestamp prefix
    (raised in PR #592)."""
    stream = auto_close(VideoStreamAv(test_missing_pts_ts))
    sequential = []
    while stream.read(decode=False) is not False:
        assert isinstance(stream.position, FramePosition)
        sequential.append(stream.position.timecode)
    for index in (1, 2, 10, 50, 100, 150):
        target = sequential[index]
        stream.seek(target)
        assert stream.read(decode=False) is not False
        assert isinstance(stream.position, FramePosition)
        assert stream.frame_number == 0
        assert stream.position.timecode.seconds == target.seconds, index
    assert not [record for record in caplog.records if "backwards" in record.message]


def test_non_monotonic_timestamps_warn_once(
    test_video_file: str, monkeypatch: pytest.MonkeyPatch, caplog, auto_close
):
    """A timestamp going backwards is reported once per stream, and only when it actually goes
    backwards: repeated timestamps (as in VFR video) stay silent."""
    stream = auto_close(VideoStreamAv(test_video_file))
    fake_stream = _AttrOverridingProxy(stream._video_stream, start_time=0)
    monkeypatch.setattr(VideoStreamAv, "_video_stream", property(lambda self: fake_stream))
    time_base = Fraction(1, 1000)
    for pts in (0, 40, 40, 0, 80, 20):
        frame = SimpleNamespace(pts=pts, dts=None, time_base=time_base)
        stream._frames_decoded += 1
        stream._update_timecode(frame)
    warnings = [record for record in caplog.records if "backwards" in record.message]
    assert len(warnings) == 1
    assert "frame 4" in warnings[0].message
    # Positions keep following the input; the warning does not alter them.
    assert stream._timecode == Timecode(pts=20, time_base=time_base)
