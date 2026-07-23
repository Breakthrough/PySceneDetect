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

import av

from scenedetect.backends.pyav import MAX_CONSECUTIVE_DECODE_FAILURES, VideoStreamAv


def test_video_stream_pyav_bytesio(test_video_file: str, auto_close):
    """Test that VideoStreamAv works with a BytesIO input in addition to a path."""
    # Mode must be binary!
    with open(test_video_file, mode="rb") as video_file:
        stream = auto_close(VideoStreamAv(path_or_io=video_file, threading_mode=None))
        assert stream.is_seekable
        stream.seek(50)
        for _ in range(10):
            assert stream.read() is not False


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
