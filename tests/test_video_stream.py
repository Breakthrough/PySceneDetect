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
"""PySceneDetect scenedetect.video_stream Tests

This file includes unit tests for the scenedetect.video_stream module, as well as the video
backends implemented in scenedetect.backends.  These tests enforce a consistent interface across
all supported backends, and verify that they are functionally equivalent where possible.
"""

import math
import os.path
import typing as ty
from dataclasses import dataclass
from fractions import Fraction

import numpy
import pytest

from scenedetect import open_video
from scenedetect.backends import VideoStreamAv, VideoStreamMoviePy
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.common import FramePosition, Timecode
from scenedetect.video_stream import FrameNumbering, SeekError, VideoStream

# Accuracy a framerate is checked to for testing purposes.
FRAMERATE_TOLERANCE = 0.001

# Accuracy a time in milliseconds is checked to for testing purposes.
TIME_TOLERANCE_MS = 0.1

# Accuracy a pixel aspect ratio is checked to for testing purposes.
PIXEL_ASPECT_RATIO_TOLERANCE = 0.001

# Filter for warnings we ignore from VideoStreamMoviePy (warnings come from FFMPEG_VideoReader).
# The warning occurs when reading the last frame, which VideoStreamMoviePy handles gracefully.
MOVIEPY_WARNING_FILTER = "ignore:.*Using the last valid frame instead.:UserWarning"


def get_moviepy_major_version() -> int:
    import importlib.metadata

    return int(importlib.metadata.version("moviepy").split(".")[0])


def calculate_frame_delta(frame_a, frame_b, roi=None) -> float:
    if roi:
        raise RuntimeError("TODO")
    assert frame_a.shape == frame_b.shape
    num_pixels = frame_a.shape[0] * frame_a.shape[1]
    return numpy.sum(numpy.abs(frame_b - frame_a)) / num_pixels


# TODO: Reduce code duplication here and in `conftest.py`
def get_absolute_path(relative_path: str) -> str:
    """Returns the absolute path to a (relative) path of a file that
    should exist within the tests/ directory.

    Throws FileNotFoundError if the file could not be found.
    """
    abs_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(
            f"""
Test video file ({relative_path}) must be present to run test case. This file can be obtained by running the following commands from the root of the repository:

git fetch --depth=1 https://github.com/Breakthrough/PySceneDetect.git refs/heads/resources:refs/remotes/origin/resources
git checkout refs/remotes/origin/resources -- tests/resources/
git reset
"""
        )
    return abs_path


@dataclass
class VideoParameters:
    """Properties for each input a VideoStream is tested against."""

    path: str
    height: int
    width: int
    frame_rate: float
    total_frames: int
    aspect_ratio: float
    duration: float


# TODO: Save two "golden" frames from each video on a shot boundary, and use that to validate
# that seeking works correctly for all backends (as well as that no frames are dropped).
def get_test_video_params() -> list[VideoParameters]:
    """Fixture for parameters of all videos."""
    return [
        VideoParameters(
            path=get_absolute_path("resources/testvideo.mp4"),
            width=1280,
            height=720,
            frame_rate=29.97,
            total_frames=720,
            aspect_ratio=1.0,
            duration=24.024,
        ),
        VideoParameters(
            path=get_absolute_path("resources/goldeneye.mp4"),
            width=1280,
            height=544,
            frame_rate=23.976,
            total_frames=1980,
            aspect_ratio=1.0,
            duration=82.5825,
        ),
        VideoParameters(
            path=get_absolute_path("resources/issue-195-aspect-ratio.mp4"),
            width=704,
            height=576,
            frame_rate=25.0,
            total_frames=628,
            aspect_ratio=1.4545454545,
            duration=25.12,
        ),
    ]


_VS_TYPES: list = [vs for vs in (VideoStreamCv2, VideoStreamAv) if vs is not None]
if VideoStreamMoviePy is not None:
    _VS_TYPES.append(
        pytest.param(
            VideoStreamMoviePy,
            marks=pytest.mark.flaky(reruns=3, reruns_delay=2, only_rerun=["OSError"]),
        )
    )

pytestmark = [
    pytest.mark.parametrize("vs_type", _VS_TYPES),
    pytest.mark.filterwarnings(MOVIEPY_WARNING_FILTER),
]


@pytest.mark.parametrize("test_video", get_test_video_params())
class TestVideoStream:
    """Fixture for tests which run against different input videos."""

    def test_properties(
        self, vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
    ):
        """Validate video properties: frame size, frame rate, duration, aspect ratio, etc."""
        stream = auto_close(vs_type(test_video.path))
        assert stream.frame_size == (test_video.width, test_video.height)
        assert stream.frame_rate == pytest.approx(test_video.frame_rate, FRAMERATE_TOLERANCE)
        assert isinstance(stream.duration, Fraction)
        assert stream.duration == pytest.approx(test_video.duration, abs=0.01)
        if vs_type is VideoStreamMoviePy:
            assert stream.frame_count is None
        else:
            assert stream.frame_count == test_video.total_frames
        file_name = os.path.basename(test_video.path)
        last_dot_pos = file_name.rfind(".")
        assert stream.name == file_name[:last_dot_pos]
        assert stream.aspect_ratio == pytest.approx(
            test_video.aspect_ratio, PIXEL_ASPECT_RATIO_TOLERANCE
        )

    def test_read(
        self, vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
    ):
        """Validate basic `read` functionality."""
        stream = auto_close(vs_type(test_video.path))
        frame = stream.read()
        assert isinstance(frame, numpy.ndarray)
        # For now hard-code 3 channels/pixel for each test video
        assert frame.shape == (test_video.height, test_video.width, 3)
        assert stream.frame_number == 0

    def test_read_no_decode(
        self, vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
    ):
        """Validate invoking `read` with `decode` set to False."""
        stream = auto_close(vs_type(test_video.path))
        assert stream.read(decode=False) is True
        assert stream.frame_number == 0

    def test_time_invariants(
        self, vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
    ):
        """Validate the `frame_number`, `position`, and `position_ms` properties."""
        stream = auto_close(vs_type(test_video.path))
        # No frame has been recorded yet.
        assert stream.frame_number == -1
        assert stream.position is None
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        # Read the first frame (frame number 0).
        assert stream.read() is not False
        assert stream.frame_number == 0
        # The `position`/`position_ms` properties represent the presentation time, so they
        # should still be zero for the first frame.
        assert isinstance(stream.position, FramePosition)
        assert stream.position.frame_number == 0
        assert stream.position.timecode.seconds == 0
        assert stream.position_ms == pytest.approx(0.0, abs=TIME_TOLERANCE_MS)
        # These fixtures are CFR, so their expected timestamps follow their frame rates.
        for i in range(1, 10):
            assert stream.read() is not False
            assert stream.frame_number == i
            assert isinstance(stream.position, FramePosition)
            assert stream.position.frame_number == i
            assert stream.position.timecode.seconds == pytest.approx(
                float(i / stream.frame_rate), abs=TIME_TOLERANCE_MS / 1000
            )
            assert stream.position_ms == pytest.approx(
                1000.0 * i / float(stream.frame_rate), abs=TIME_TOLERANCE_MS
            )

    def test_reset(
        self, vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
    ):
        """Test `reset()` functions as expected."""
        stream = auto_close(vs_type(test_video.path))
        # Decode some frames, then reset the VideoStream and validate the time invariants.
        for _ in range(10):
            stream.read()
        assert stream.frame_number == 9
        assert stream.peek_timecode() is not None
        stream.reset()
        assert stream.frame_number == -1
        assert stream.position is None
        assert stream.position_ms == pytest.approx(0, abs=TIME_TOLERANCE_MS)
        assert stream.read() is not False
        assert stream.frame_number == 0
        assert isinstance(stream.position, FramePosition)
        assert stream.position.timecode.seconds == 0

    @pytest.mark.parametrize("frame_numbering", list(FrameNumbering))
    def test_seek(
        self,
        vs_type: ty.Callable[..., VideoStream],
        test_video: VideoParameters,
        auto_close,
        frame_numbering: FrameNumbering,
    ):
        """Validate `seek()` functionality with different offset types."""
        stream = auto_close(vs_type(test_video.path, frame_numbering=frame_numbering))
        assert stream.frame_numbering is frame_numbering

        # Seek to a given frame number (int).
        stream.seek(200)
        if frame_numbering is FrameNumbering.SOURCE:
            assert stream.frame_number == 199
            assert isinstance(stream.position, FramePosition)
            assert stream.position_ms == pytest.approx(
                float(1000 * 199.0 / float(stream.frame_rate)), abs=TIME_TOLERANCE_MS
            )
        else:
            assert stream.frame_number == -1
            assert stream.position is None
            assert stream.position_ms == 0.0
        stream.read()
        assert stream.frame_number == (200 if frame_numbering is FrameNumbering.SOURCE else 0)
        assert isinstance(stream.position, FramePosition)
        assert stream.position.timecode.seconds == pytest.approx(
            float(200 / stream.frame_rate), abs=TIME_TOLERANCE_MS / 1000
        )
        assert stream.position_ms == pytest.approx(
            1000.0 * (200.0 / float(stream.frame_rate)), abs=TIME_TOLERANCE_MS
        )

        # These CFR fixtures select the first frame at or after 2 seconds.
        target_frame = math.ceil(2 * stream.frame_rate)
        for target in (2.0, Timecode(pts=2, time_base=Fraction(1))):
            stream.seek(target)

            if frame_numbering is FrameNumbering.SOURCE:
                assert stream.frame_number == target_frame - 1
                assert isinstance(stream.position, FramePosition)
                assert stream.position.timecode.seconds == pytest.approx(
                    float((target_frame - 1) / stream.frame_rate),
                    abs=TIME_TOLERANCE_MS / 1000,
                )
            else:
                assert stream.frame_number == -1
                assert stream.position is None
                assert stream.position_ms == 0.0

            assert stream.read() is not False
            assert stream.frame_number == (
                target_frame if frame_numbering is FrameNumbering.SOURCE else 0
            )
            assert isinstance(stream.position, FramePosition)
            assert stream.position.timecode.seconds == pytest.approx(
                float(target_frame / stream.frame_rate),
                abs=TIME_TOLERANCE_MS / 1000,
            )
            assert stream.position_ms == pytest.approx(
                float(1000 * target_frame / stream.frame_rate),
                abs=TIME_TOLERANCE_MS,
            )

    @pytest.mark.parametrize("frame_numbering", list(FrameNumbering))
    def test_seek_start(
        self,
        vs_type: ty.Callable[..., VideoStream],
        test_video: VideoParameters,
        auto_close,
        frame_numbering: FrameNumbering,
    ):
        """Validate behaviour of `seek()` at the start of a video."""
        stream = auto_close(vs_type(test_video.path, frame_numbering=frame_numbering))
        # Here we check similar invariants to test_time_invariants, but using seek().
        assert stream.frame_number == -1
        assert stream.position is None
        assert stream.position_ms == 0.0
        # Seeking to frame 0 (or time 0) is equivalent to seeking "before" the first frame.
        stream.seek(0)
        assert stream.frame_number == -1
        assert stream.position is None
        assert stream.position_ms == 0.0
        # Ensure invariants hold for the first few frames.
        for i in range(10):
            assert stream.read() is not False
            assert isinstance(stream.position, FramePosition)
            assert stream.frame_number == i
            assert stream.position.timecode.seconds == pytest.approx(
                i / float(stream.frame_rate), abs=TIME_TOLERANCE_MS / 1000
            )
            assert stream.position_ms == pytest.approx(
                1000.0 * i / float(stream.frame_rate), abs=TIME_TOLERANCE_MS
            )
        stream.seek(0)
        assert stream.frame_number == -1
        assert stream.position is None
        assert stream.position_ms == 0.0

        # Seek to the second source frame (ordinal 1).
        stream.seek(1)
        # SOURCE has recorded frame 0; RELATIVE has no recorded position yet.
        if frame_numbering is FrameNumbering.SOURCE:
            assert isinstance(stream.position, FramePosition)
            assert stream.frame_number == 0
            assert stream.position.timecode.seconds == 0
        else:
            assert stream.frame_number == -1
            assert stream.position is None
        assert stream.read() is not False
        assert isinstance(stream.position, FramePosition)
        assert stream.frame_number == (1 if stream.frame_numbering is FrameNumbering.SOURCE else 0)
        assert stream.position.timecode.seconds == pytest.approx(
            float(1 / stream.frame_rate), abs=TIME_TOLERANCE_MS / 1000
        )

    def test_read_eof(
        self, vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
    ):
        """Ensure calling `read()` handles the end of the video correctly."""
        stream = auto_close(vs_type(test_video.path, frame_numbering=FrameNumbering.SOURCE))
        # Seek to the final expected source frame.
        stream.seek(test_video.total_frames - 1)
        while stream.read() is not False:
            pass
        # TODO: On some videos, the PyAV backend seems to drop a frame. See where this occurs.
        if vs_type == VideoStreamAv:
            assert stream.frame_number in (test_video.total_frames - 1, test_video.total_frames - 2)
        else:
            assert stream.frame_number == test_video.total_frames - 1

        last_position = stream.position
        assert stream.peek_timecode() is None
        assert stream.read() is False
        assert stream.position == last_position

    def test_seek_past_eof(
        self, vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
    ):
        """Validate calling `seek()` to offset past end of video."""
        stream = auto_close(vs_type(test_video.path, frame_numbering=FrameNumbering.SOURCE))
        # Seek to a large seek offset past the end of the video. Some backends only support 32-bit
        # frame numbers so that's our max offset. Certain backends disallow seek offsets past EOF,
        # in which case they should raise a SeekError (and the test is considered a pass).
        try:
            stream.seek(2**32)
        except SeekError:
            return
        # For those backends that do allow seek offsets past EOF, they should act as though we
        # seeked to the end of the video (i.e. shouldn't be able to decode any more frames).
        assert stream.read() is False
        # TODO: On some videos, the PyAV backend seems to drop a frame. See where this occurs.
        if vs_type == VideoStreamAv:
            assert stream.frame_number in (test_video.total_frames - 1, test_video.total_frames - 2)
        else:
            assert stream.frame_number == test_video.total_frames - 1

    def test_seek_invalid(
        self, vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
    ):
        """Test `seek()` throws correct exception when specifying in invalid seek value."""
        stream = auto_close(vs_type(test_video.path))

        with pytest.raises(ValueError):
            stream.seek(-1)

        with pytest.raises(ValueError):
            stream.seek(-0.1)


#
# Tests which run against a specific inputs.
#


def test_invalid_path(vs_type: ty.Callable[..., VideoStream]):
    """Ensure correct exception is thrown if the path does not exist."""
    with pytest.raises(OSError):
        _ = vs_type("this_path_should_not_exist.mp4")


def test_framerate_legacy_alias(vs_type: ty.Callable[..., VideoStream], auto_close):
    """`framerate=` is the deprecated alias for `frame_rate=` (issue #548). All backends
    must accept both forms and produce the same `frame_rate`."""
    path = get_absolute_path("resources/goldeneye.mp4")
    with pytest.warns(DeprecationWarning, match="frame_rate"):
        legacy = auto_close(vs_type(path, framerate=30.0))
    canonical = auto_close(vs_type(path, frame_rate=30.0))
    assert legacy.frame_rate == canonical.frame_rate
    # When both are provided, `frame_rate` wins (legacy is ignored).
    with pytest.warns(DeprecationWarning, match="frame_rate"):
        both = auto_close(vs_type(path, frame_rate=30.0, framerate=24.0))
    assert both.frame_rate == canonical.frame_rate


def test_corrupt_video(vs_type: ty.Callable[..., VideoStream], corrupt_video_file: str, auto_close):
    """Test that backend handles video with corrupt frame gracefully with defaults."""
    if vs_type == VideoStreamMoviePy and get_moviepy_major_version() >= 2:
        # Due to changes in MoviePy 2.0 (#461), loading this file causes an exception to be thrown.
        # See https://github.com/Zulko/moviepy/pull/2253 for a PR that attempts to more gracefully
        # handle this case, however even once that is fixed, we will be unable to run this test
        # on certain versions of MoviePy.
        pytest.skip(reason="https://github.com/Zulko/moviepy/pull/2253")

    stream = auto_close(vs_type(corrupt_video_file))

    # The fixture has 596 frames, one of which is corrupt. Depending on the FFmpeg build, the bad
    # frame is either skipped (incrementing `decode_failures`) or concealed and decoded anyway.
    # Either way the backend must decode the rest of the stream without raising.
    frames_read = 0
    while stream.read(decode=False) is not False:
        frames_read += 1
    assert frames_read >= 590, f"Only decoded {frames_read} frames!"
    assert isinstance(stream.decode_failures, int)
    assert stream.decode_failures >= 0


def test_decode_failures_clean_video(vs_type: ty.Callable[..., VideoStream], auto_close):
    """`decode_failures` must exist on every backend and stay 0 on a clean video."""
    stream = auto_close(vs_type(get_absolute_path("resources/testvideo.mp4")))
    assert stream.decode_failures == 0
    for _ in range(10):
        assert stream.read() is not False
    assert stream.decode_failures == 0


def test_delayed_start_normalized(
    vs_type: ty.Callable[..., VideoStream], delayed_start_video: str, auto_close
):
    """Files with a nonzero stream start time must report the first frame at t=0 on every
    backend (the fixture has a start time of 1.075s)."""
    stream = auto_close(vs_type(delayed_start_video))
    assert stream.read(decode=False) is not False
    assert stream.position is not None
    assert 0 <= stream.position.timecode.seconds < Fraction(1, 10)
    assert stream.frame_number == 0


#
# Tests for closing streams.
#


def _video_properties(stream: VideoStream) -> tuple:
    """Properties describing the video itself, which must remain available after `close()`."""
    return (
        stream.path,
        stream.name,
        stream.frame_rate,
        stream.duration,
        stream.frame_size,
        stream.aspect_ratio,
        stream.frame_count,
    )


def test_close_is_idempotent(vs_type: ty.Callable[..., VideoStream], auto_close):
    """Calling `close()` more than once must have no effect."""
    stream = auto_close(vs_type(get_absolute_path("resources/testvideo.mp4")))
    assert stream.read() is not False
    stream.close()
    stream.close()
    with pytest.raises(ValueError):
        stream.read()


def test_use_after_close(vs_type: ty.Callable[..., VideoStream], auto_close):
    """`read()`, `peek_timecode()`, `seek()`, and `reset()` must raise after closing."""
    stream = auto_close(vs_type(get_absolute_path("resources/testvideo.mp4")))
    stream.close()
    with pytest.raises(ValueError):
        stream.read()
    with pytest.raises(ValueError):
        stream.read(decode=False)
    with pytest.raises(ValueError):
        stream.peek_timecode()
    with pytest.raises(ValueError):
        stream.seek(10)
    with pytest.raises(ValueError):
        stream.reset()


@pytest.mark.parametrize("test_video", get_test_video_params())
def test_properties_after_close(
    vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
):
    """Properties describing the video must remain available, and unchanged, after `close()`."""
    stream = auto_close(vs_type(test_video.path))
    expected = _video_properties(stream)
    stream.close()
    assert _video_properties(stream) == expected


def test_context_manager(vs_type: type[VideoStream]):
    """`with open_video(path) as video:` must yield the stream and close it on exit."""
    path = get_absolute_path("resources/testvideo.mp4")
    with open_video(path, backend=vs_type.BACKEND_NAME) as video:
        assert isinstance(video, vs_type)
        assert video.read() is not False
    with pytest.raises(ValueError):
        video.read()


def test_context_manager_closes_on_error(vs_type: ty.Callable[..., VideoStream], auto_close):
    """The stream must be closed if the `with` block raises, without suppressing the error."""
    stream = auto_close(vs_type(get_absolute_path("resources/testvideo.mp4")))
    with pytest.raises(RuntimeError, match="raised in with block"), stream:
        raise RuntimeError("raised in with block")
    with pytest.raises(ValueError):
        stream.read()


@pytest.mark.parametrize("test_video", get_test_video_params())
def test_peek_timecode(
    vs_type: ty.Callable[..., VideoStream], test_video: VideoParameters, auto_close
):
    """Peeking retains the next frame without changing the recorded position."""
    stream = auto_close(vs_type(test_video.path))

    for frame_number in range(3):
        previous_position = stream.position
        timecode = stream.peek_timecode()

        assert isinstance(timecode, Timecode)
        assert stream.peek_timecode() == timecode
        assert stream.position == previous_position
        assert stream.frame_number == frame_number - 1

        assert stream.read(decode=False) is True
        assert stream.frame_number == frame_number
        assert stream.position is not None
        assert stream.position.timecode == timecode
