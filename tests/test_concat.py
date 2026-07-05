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

import pytest

from scenedetect import SceneManager, ThresholdDetector, open_video
from scenedetect.backends import AVAILABLE_BACKENDS
from scenedetect.backends.concat import VideoStreamConcat
from scenedetect.video_stream import VideoOpenFailure

FADES_TOTAL_FRAMES = 250
FADES_DURATION = 10.0

BACKENDS = [backend for backend in ("opencv", "pyav") if backend in AVAILABLE_BACKENDS]


@pytest.mark.parametrize("backend", BACKENDS)
def test_decode_single(test_fades_clip, backend):
    """Decode a single video and validate the reported frame count and position."""
    video = VideoStreamConcat([test_fades_clip], backend=backend)
    while video.read(decode=False) is not False:
        pass
    assert video.frame_number == FADES_TOTAL_FRAMES
    assert video.decode_failures == 0


@pytest.mark.parametrize("backend", BACKENDS)
def test_decode_multiple(test_fades_clip, backend):
    """Decode multiple videos and validate the reported frame count."""
    splice_amount = 3
    video = VideoStreamConcat([test_fades_clip] * splice_amount, backend=backend)
    while video.read(decode=False) is not False:
        pass
    assert video.frame_number == FADES_TOTAL_FRAMES * splice_amount
    assert video.decode_failures == 0


@pytest.mark.parametrize("backend", BACKENDS)
def test_seam_monotonicity(test_fades_clip, backend):
    """Position must be strictly increasing across the file seam."""
    video = VideoStreamConcat([test_fades_clip] * 2, backend=backend)
    last_seconds = -1.0
    max_delta = 0.0
    while video.read(decode=False) is not False:
        seconds = video.position.seconds
        assert seconds > last_seconds, f"position went backwards: {seconds} <= {last_seconds}"
        if last_seconds >= 0:
            max_delta = max(max_delta, seconds - last_seconds)
        last_seconds = seconds
    # The seam should be continuous: no gap larger than a few frame durations.
    assert max_delta < 0.5, f"discontinuity across seam: {max_delta}s"
    assert last_seconds > 2 * FADES_DURATION - 1.0


@pytest.mark.parametrize("backend", BACKENDS)
def test_seek(test_fades_clip, backend):
    """Seeking should work on the global timeline, in either direction, across sources."""
    video = VideoStreamConcat([test_fades_clip] * 2, backend=backend)
    # Seek into the second source.
    target = FADES_DURATION + 5.0
    video.seek(target)
    assert video.read(decode=False) is not False
    assert abs(video.position.seconds - target) < 0.25
    # Seek backwards into the first source.
    video.seek(5.0)
    assert video.read(decode=False) is not False
    assert abs(video.position.seconds - 5.0) < 0.25


def test_seek_backward_then_cross_seam(test_fades_clip):
    """Crossing the seam a second time after a backward seek must not shift the timeline
    again (offset correction must be idempotent)."""
    video = VideoStreamConcat([test_fades_clip] * 2)
    # Read across the seam once.
    video.seek(FADES_DURATION - 0.5)
    while video.position.seconds < FADES_DURATION + 0.5:
        assert video.read(decode=False) is not False
    first_pass = video.position.seconds
    # Seek backward before the seam and cross it again.
    video.seek(FADES_DURATION - 0.5)
    last = video.position.seconds
    while video.position.seconds < FADES_DURATION + 0.5:
        assert video.read(decode=False) is not False
        assert video.position.seconds > last
        last = video.position.seconds
    assert abs(video.position.seconds - first_pass) < 0.25


def test_seam_monotonicity_vfr(test_vfr_drop3_video):
    """Position must also be strictly increasing across the seam between variable framerate
    inputs, whose declared duration is less exact than CFR."""
    video = VideoStreamConcat([test_vfr_drop3_video] * 2)
    last_seconds = -1.0
    while video.read(decode=False) is not False:
        seconds = video.position.seconds
        assert seconds > last_seconds, f"position went backwards: {seconds} <= {last_seconds}"
        last_seconds = seconds


def test_map_span(test_fades_clip):
    """A span crossing the seam between two inputs must map to two local spans."""
    video = VideoStreamConcat([test_fades_clip] * 2)
    duration = FADES_DURATION
    start = video.base_timecode + (duration - 3.0)
    end = video.base_timecode + (duration + 3.0)
    spans = video.map_span(start, end)
    assert len(spans) == 2
    assert spans[0].source_index == 0 and spans[1].source_index == 1
    assert abs(spans[0].local_start.seconds - (duration - 3.0)) < 0.01
    assert abs(spans[0].local_end.seconds - duration) < 0.01
    assert spans[1].local_start.seconds == 0.0
    assert abs(spans[1].local_end.seconds - 3.0) < 0.01
    # A span entirely within the first source maps to a single span.
    spans = video.map_span(video.base_timecode + 1.0, video.base_timecode + 2.0)
    assert len(spans) == 1 and spans[0].source_index == 0


def test_mismatched_resolution(test_fades_clip, test_video_file):
    """Sources with different resolutions cannot be concatenated."""
    with pytest.raises(VideoOpenFailure):
        VideoStreamConcat([test_fades_clip, test_video_file])


def test_unknown_backend_falls_back(test_fades_clip):
    """An unknown backend name falls back to OpenCV instead of failing."""
    video = VideoStreamConcat([test_fades_clip], backend="not_a_backend")
    assert video.child_backend == "opencv"
    assert video.read(decode=False) is not False


def test_open_video_list(test_fades_clip):
    """`open_video` accepts a list of paths and returns a concatenated stream."""
    video = open_video([test_fades_clip, test_fades_clip])
    assert isinstance(video, VideoStreamConcat)
    assert video.duration.seconds == pytest.approx(2 * FADES_DURATION, abs=0.1)
    # A single-element list also returns a concatenated stream.
    video = open_video([test_fades_clip])
    assert isinstance(video, VideoStreamConcat)


def test_scene_manager_detect(test_fades_clip):
    """The concatenated stream must work end-to-end with SceneManager: detecting fades over
    two spliced copies must find twice as many scenes as a single copy."""

    def detect_scenes(paths):
        scene_manager = SceneManager()
        scene_manager.add_detector(ThresholdDetector())
        video = open_video(paths)
        scene_manager.detect_scenes(video=video)
        return scene_manager.get_scene_list()

    single = detect_scenes([test_fades_clip])
    double = detect_scenes([test_fades_clip] * 2)
    assert len(single) > 0
    assert len(double) == 2 * len(single)


@pytest.mark.skipif("pyav" not in AVAILABLE_BACKENDS, reason="PyAV backend not available")
def test_corrupt_concat(corrupt_video_file):
    """The PyAV input path must tolerate corrupt frames and decode the full stream."""
    video = VideoStreamConcat([corrupt_video_file], backend="pyav")
    num_frames = 0
    while video.read(decode=False) is not False:
        num_frames += 1
    assert num_frames >= 590
