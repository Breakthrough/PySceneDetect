#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect scenedetect.backends.concat Tests

Validates the multi-video concatenation logic in `scenedetect.backends.concat`."""

import typing as ty
from fractions import Fraction

import pytest

from scenedetect import SceneManager, ThresholdDetector, open_video
from scenedetect.backends import AVAILABLE_BACKENDS
from scenedetect.backends.concat import VideoStreamConcat
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.common import FramePosition, Timecode
from scenedetect.video_stream import FrameNumbering, VideoOpenFailure

FADES_TOTAL_FRAMES = 250
FADES_DURATION = 10.0

BACKENDS = [backend for backend in ("opencv", "pyav") if backend in AVAILABLE_BACKENDS]


class _TrackedStream(VideoStreamCv2):
    """OpenCV backend which records every stream it opens."""

    instances: ty.ClassVar[list["_TrackedStream"]] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _TrackedStream.instances.append(self)

    @property
    def is_closed(self) -> bool:
        """True once the underlying capture has been released."""
        return not self.capture.isOpened()


@pytest.fixture
def tracked_streams(monkeypatch: pytest.MonkeyPatch) -> list[_TrackedStream]:
    """Registers `_TrackedStream` as the `tracked` backend, returning the streams it opens."""
    monkeypatch.setattr(_TrackedStream, "instances", [])
    monkeypatch.setitem(AVAILABLE_BACKENDS, "tracked", _TrackedStream)
    return _TrackedStream.instances


@pytest.mark.parametrize("backend", BACKENDS)
def test_decode_single(test_fades_clip, backend, auto_close):
    """Decode a single video and validate the reported frame count and position."""
    video = auto_close(VideoStreamConcat([test_fades_clip], backend=backend))
    while video.read(decode=False) is not False:
        pass
    assert video.frame_count == FADES_TOTAL_FRAMES
    assert video.frame_number == FADES_TOTAL_FRAMES - 1
    assert video.decode_failures == 0


@pytest.mark.parametrize("backend", BACKENDS)
def test_decode_multiple(test_fades_clip, backend, auto_close):
    """Decode multiple videos and validate the reported frame count."""
    splice_amount = 3
    video = auto_close(VideoStreamConcat([test_fades_clip] * splice_amount, backend=backend))
    while video.read(decode=False) is not False:
        pass
    assert video.frame_count == FADES_TOTAL_FRAMES * splice_amount
    assert video.frame_number == FADES_TOTAL_FRAMES * splice_amount - 1
    assert video.decode_failures == 0


@pytest.mark.parametrize("backend", BACKENDS)
def test_seam_monotonicity(test_fades_clip, backend, auto_close):
    """Position must be strictly increasing across the file seam."""
    video = auto_close(VideoStreamConcat([test_fades_clip] * 2, backend=backend))
    last_seconds = -1.0
    max_delta = 0.0
    while video.read(decode=False) is not False:
        assert isinstance(video.position, FramePosition)
        seconds = video.position.timecode.seconds
        assert seconds > last_seconds, f"position went backwards: {seconds} <= {last_seconds}"
        if last_seconds >= 0:
            max_delta = max(max_delta, seconds - last_seconds)
        last_seconds = seconds
    # The seam should be continuous: no gap larger than a few frame durations.
    assert max_delta < 0.5, f"discontinuity across seam: {max_delta}s"
    assert last_seconds > 2 * FADES_DURATION - 1.0


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("frame_numbering", list(FrameNumbering))
def test_seek(test_fades_clip, backend, auto_close, frame_numbering):
    """Seeking should work on the global timeline, in either direction, across sources."""
    video = auto_close(
        VideoStreamConcat([test_fades_clip] * 2, backend=backend, frame_numbering=frame_numbering)
    )
    # Seek into the second source.
    target = FADES_DURATION + 5.0
    video.seek(target)
    assert video.read(decode=False) is not False
    assert isinstance(video.position, FramePosition)
    assert abs(video.position.timecode.seconds - target) < 0.25
    # The CFR fixture has 250 frames per 10 seconds.
    assert video.frame_number == (375 if frame_numbering is FrameNumbering.SOURCE else 0)
    # Seek backwards into the first source.
    video.seek(5.0)
    assert video.read(decode=False) is not False
    assert isinstance(video.position, FramePosition)
    assert abs(video.position.timecode.seconds - 5.0) < 0.25
    assert video.frame_number == (125 if frame_numbering is FrameNumbering.SOURCE else 0)
    # Integer targets are global source ordinals in either numbering mode.
    for target_frame in (FADES_TOTAL_FRAMES + 1, 1):
        video.seek(target_frame)
        assert video.read(decode=False) is not False
        assert isinstance(video.position, FramePosition)
        assert video.frame_number == (
            target_frame if frame_numbering is FrameNumbering.SOURCE else 0
        )
        assert video.position.timecode.seconds == Fraction(target_frame, 25)


def test_seek_backward_then_cross_seam(test_fades_clip, auto_close):
    """Crossing the seam a second time after a backward seek must not shift the timeline
    again (offset correction must be idempotent)."""
    video = auto_close(VideoStreamConcat([test_fades_clip] * 2))
    # Read across the seam once.
    video.seek(FADES_DURATION - 0.5)
    assert video.read(decode=False) is not False
    assert isinstance(video.position, FramePosition)
    while video.position.timecode.seconds < FADES_DURATION + 0.5:
        assert video.read(decode=False) is not False
    first_pass = video.position.timecode.seconds
    # Seek backward before the seam and cross it again.
    video.seek(FADES_DURATION - 0.5)
    assert video.read(decode=False) is not False
    assert isinstance(video.position, FramePosition)
    last = video.position.timecode.seconds
    while video.position.timecode.seconds < FADES_DURATION + 0.5:
        assert video.read(decode=False) is not False
        assert video.position.timecode.seconds > last
        last = video.position.timecode.seconds
    assert abs(video.position.timecode.seconds - first_pass) < 0.25


def test_seam_monotonicity_vfr(test_vfr_drop3_video, auto_close):
    """Position must also be strictly increasing across the seam between variable framerate
    inputs, whose declared duration is less exact than CFR."""
    video = auto_close(VideoStreamConcat([test_vfr_drop3_video] * 2))
    last_seconds = -1.0
    while video.read(decode=False) is not False:
        assert isinstance(video.position, FramePosition)
        seconds = video.position.timecode.seconds
        assert seconds > last_seconds, f"position went backwards: {seconds} <= {last_seconds}"
        last_seconds = seconds


def test_map_span(test_fades_clip, auto_close):
    """A span crossing the seam between two inputs must map to two local spans."""
    video = auto_close(VideoStreamConcat([test_fades_clip] * 2))
    duration = FADES_DURATION
    start = Timecode(pts=7, time_base=Fraction(1))
    end = Timecode(pts=13, time_base=Fraction(1))
    spans = video.map_span(start, end)
    assert len(spans) == 2
    assert spans[0].source_index == 0 and spans[1].source_index == 1
    assert abs(spans[0].local_start.seconds - (duration - 3.0)) < 0.01
    assert abs(spans[0].local_end.seconds - duration) < 0.01
    assert spans[1].local_start.seconds == 0.0
    assert abs(spans[1].local_end.seconds - 3.0) < 0.01
    # A span entirely within the first source maps to a single span.
    spans = video.map_span(
        Timecode(pts=1, time_base=Fraction(1)), Timecode(pts=2, time_base=Fraction(1))
    )
    assert len(spans) == 1 and spans[0].source_index == 0


def test_mismatched_resolution(test_fades_clip, test_video_file):
    """Sources with different resolutions cannot be concatenated."""
    with pytest.raises(VideoOpenFailure):
        VideoStreamConcat([test_fades_clip, test_video_file])


def test_unknown_backend_falls_back(test_fades_clip, auto_close):
    """An unknown backend name falls back to OpenCV instead of failing."""
    video = auto_close(VideoStreamConcat([test_fades_clip], backend="not_a_backend"))
    assert video.child_backend == "opencv"
    assert video.read(decode=False) is not False


def test_open_video_list(test_fades_clip, auto_close):
    """`open_video` accepts a list of paths and returns a concatenated stream."""
    video = auto_close(open_video([test_fades_clip, test_fades_clip]))
    assert isinstance(video, VideoStreamConcat)
    assert isinstance(video.duration, Fraction)
    assert video.duration == pytest.approx(2 * FADES_DURATION, abs=0.1)
    # A single-element list also returns a concatenated stream.
    video = auto_close(open_video([test_fades_clip]))
    assert isinstance(video, VideoStreamConcat)


def test_scene_manager_detect(test_fades_clip, auto_close):
    """The concatenated stream must work end-to-end with SceneManager: detecting fades over
    two spliced copies must find twice as many scenes as a single copy."""

    def detect_scenes(paths):
        scene_manager = SceneManager()
        scene_manager.add_detector(ThresholdDetector())
        video = auto_close(open_video(paths))
        scene_manager.detect_scenes(video=video)
        return scene_manager.get_scene_list()

    single = detect_scenes([test_fades_clip])
    double = detect_scenes([test_fades_clip] * 2)
    assert len(single) > 0
    assert len(double) == 2 * len(single)


@pytest.mark.skipif("pyav" not in AVAILABLE_BACKENDS, reason="PyAV backend not available")
def test_corrupt_concat(corrupt_video_file, auto_close):
    """The PyAV input path must tolerate corrupt frames and decode the full stream."""
    video = auto_close(VideoStreamConcat([corrupt_video_file], backend="pyav"))
    num_frames = 0
    while video.read(decode=False) is not False:
        num_frames += 1
    assert num_frames >= 590


def test_probed_sources_closed(test_fades_clip, tracked_streams, auto_close):
    """Only the first input stays open after probing; the others are closed once probed."""
    auto_close(VideoStreamConcat([test_fades_clip] * 3, backend="tracked"))
    assert [stream.is_closed for stream in tracked_streams] == [False, True, True]


def test_failed_open_closes_sources(test_fades_clip, test_video_file, tracked_streams):
    """Every input opened so far must be closed if the inputs can't be opened or concatenated."""
    # The second input has a different resolution.
    with pytest.raises(VideoOpenFailure):
        VideoStreamConcat([test_fades_clip, test_video_file], backend="tracked")
    # The third input doesn't exist.
    with pytest.raises(OSError):
        VideoStreamConcat([test_fades_clip, test_fades_clip, "missing.mp4"], backend="tracked")
    assert len(tracked_streams) == 4
    assert all(stream.is_closed for stream in tracked_streams)


def test_switching_sources_closes_outgoing(test_fades_clip, tracked_streams, auto_close):
    """Switching sources via `read()`, `seek()`, or `reset()` must close the outgoing source,
    so only the source currently being decoded is open."""
    video = auto_close(VideoStreamConcat([test_fades_clip] * 2, backend="tracked"))

    def assert_only_latest_open(num_opened: int):
        assert len(tracked_streams) == num_opened
        assert all(stream.is_closed for stream in tracked_streams[:-1])
        assert not tracked_streams[-1].is_closed

    # Read across the seam into the second source.
    video.seek(FADES_DURATION - 0.5)
    assert video.read(decode=False) is not False
    assert isinstance(video.position, FramePosition)
    while video.position.timecode.seconds < FADES_DURATION + 0.5:
        assert video.read(decode=False) is not False
    assert_only_latest_open(3)
    # Seek back into the first source, then forward into the second.
    video.seek(5.0)
    assert_only_latest_open(4)
    video.seek(FADES_DURATION + 5.0)
    assert_only_latest_open(5)
    video.reset()
    assert_only_latest_open(6)


def test_close(test_fades_clip, tracked_streams, auto_close):
    """`close()` closes the current source and is idempotent. Afterwards `read()`, `peek_timecode()`,
    `seek()`, and `reset()` raise `ValueError` without opening any source."""
    video = auto_close(VideoStreamConcat([test_fades_clip] * 2, backend="tracked"))
    assert video.read(decode=False) is not False
    video.close()
    video.close()
    assert all(stream.is_closed for stream in tracked_streams)
    num_opened = len(tracked_streams)
    with pytest.raises(ValueError):
        video.read()
    with pytest.raises(ValueError):
        video.peek_timecode()
    with pytest.raises(ValueError):
        video.seek(FADES_DURATION + 5.0)
    with pytest.raises(ValueError):
        video.reset()
    assert len(tracked_streams) == num_opened


@pytest.mark.parametrize("backend", BACKENDS)
def test_context_manager(test_fades_clip, backend):
    """`with open_video([...]) as video:` yields the concatenated stream and closes it."""
    with open_video([test_fades_clip] * 2, backend=backend) as video:
        assert isinstance(video, VideoStreamConcat)
        assert video.child_backend == backend
        assert video.read(decode=False) is not False
    with pytest.raises(ValueError):
        video.read()


@pytest.mark.parametrize("backend", BACKENDS)
def test_properties_after_close(test_fades_clip, backend, auto_close):
    """Properties describing the video must remain available after `close()`."""
    video = auto_close(VideoStreamConcat([test_fades_clip] * 2, backend=backend))

    def properties():
        return (
            video.path,
            video.name,
            video.frame_rate,
            video.duration,
            video.frame_count,
            video.frame_size,
            video.aspect_ratio,
            video.child_backend,
        )

    expected = properties()
    video.close()
    assert properties() == expected


@pytest.mark.parametrize("backend", BACKENDS)
def test_peek_timecode_across_seam(test_fades_clip, backend, auto_close):
    """Peeking across a source boundary preserves the position and retains the next frame."""
    video = auto_close(VideoStreamConcat([test_fades_clip] * 2, backend=backend))
    video.seek(FADES_TOTAL_FRAMES - 1)
    assert video.read(decode=False) is not False
    assert isinstance(video.position, FramePosition)
    assert video.position.timecode.seconds == Fraction(249, 25)
    previous_position = video.position

    timecode = video.peek_timecode()
    assert isinstance(timecode, Timecode)
    assert timecode.seconds == Fraction(10)
    assert video.peek_timecode() == timecode
    assert video.position == previous_position

    assert video.read(decode=False) is not False
    assert isinstance(video.position, FramePosition)
    assert video.position.timecode.seconds == timecode.seconds
    assert video.frame_number == previous_position.frame_number + 1
