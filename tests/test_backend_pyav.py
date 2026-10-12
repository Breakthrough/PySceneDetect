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
from fractions import Fraction
from types import SimpleNamespace

import av
import pytest

from scenedetect.backends.pyav import MAX_CONSECUTIVE_DECODE_FAILURES, VideoStreamAv, _to_fraction


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
    assert isinstance(stream.position.time_base, Fraction)
    assert stream.position_ms == 0.0
    assert stream.frame_number == 1


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
    """When neither the stream frame count nor the container duration is available, the duration
    must be derived from `stream.duration * stream.time_base` (duration is in time_base units)."""
    stream = auto_close(VideoStreamAv(test_video_file))
    real_stream = stream._video_stream
    assert real_stream.frames == 720
    fake_stream = _AttrOverridingProxy(
        real_stream,
        frames=0,
        container=SimpleNamespace(duration=None),
    )
    monkeypatch.setattr(VideoStreamAv, "_video_stream", property(lambda self: fake_stream))
    assert stream._get_duration() == 720


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
    PyAV < 19, AVRational(0, 1) on PyAV 19+), the duration must be reported as 0 with a warning."""
    stream = auto_close(VideoStreamAv(test_video_file))
    fake_stream = _AttrOverridingProxy(
        stream._video_stream,
        frames=0,
        container=SimpleNamespace(duration=None),
        time_base=time_base,
    )
    monkeypatch.setattr(VideoStreamAv, "_video_stream", property(lambda self: fake_stream))
    assert stream._get_duration() == 0
    assert any("time_base" in record.message for record in caplog.records)
