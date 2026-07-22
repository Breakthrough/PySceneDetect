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
"""Tests for scenedetect._fan_out.FanOutVideoStream."""

from __future__ import annotations

import threading

import numpy as np
import pytest

from scenedetect import ContentDetector, SceneManager, detect, open_video
from scenedetect._fan_out import FanOutVideoStream
from scenedetect.video_stream import SeekError


def _read_all(stream) -> list[np.ndarray]:
    frames = []
    while True:
        frame = stream.read()
        if frame is False:
            break
        frames.append(frame)
    return frames


def test_fan_out_n1_matches_single_consumer(test_video_file):
    """A single consumer behind the wrapper sees the same frames as a bare source."""
    baseline = _read_all(open_video(test_video_file))

    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=1)
    fan.start()
    try:
        fanout = _read_all(fan.stream(0))
    finally:
        fan.close()

    assert len(fanout) == len(baseline)
    for a, b in zip(fanout, baseline, strict=True):
        assert np.array_equal(a, b)


def test_fan_out_frame_equality_across_consumers(test_video_file):
    """All N consumers see identical frames in identical order."""
    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=4, prefetch=4)
    fan.start()
    results: list[list[np.ndarray]] = [[] for _ in range(4)]

    def worker(i: int) -> None:
        results[i] = _read_all(fan.stream(i))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        fan.close()

    counts = {len(r) for r in results}
    assert len(counts) == 1, f"Consumers saw different frame counts: {counts}"
    n_frames = counts.pop()
    assert n_frames > 0
    # Compare frame-by-frame across all consumers.
    for k in range(n_frames):
        ref = results[0][k]
        for i in range(1, 4):
            assert np.array_equal(results[i][k], ref), f"frame {k} differs in consumer {i}"


def test_fan_out_per_consumer_position(test_video_file):
    """Each consumer's frame_number/position advances based on its own reads."""
    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=2, prefetch=4)
    fan.start()
    try:
        s0 = fan.stream(0)
        s1 = fan.stream(1)
        assert s0.frame_number == 0
        assert s1.frame_number == 0
        # Read 5 frames on s0 (s1 must also keep up because of back-pressure, but its
        # frame_number is independent of how many we've consumed there).
        for _ in range(5):
            assert isinstance(s0.read(), np.ndarray)
        assert s0.frame_number == 5
        assert s1.frame_number == 0  # never read; counter is per-consumer
        # Now drain s1; it should still see frame 1 first.
        for _ in range(5):
            assert isinstance(s1.read(), np.ndarray)
        assert s1.frame_number == 5
    finally:
        fan.close()


def test_fan_out_seek_and_reset_raise(test_video_file):
    """Consumers are forward-only."""
    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=1)
    fan.start()
    try:
        s = fan.stream(0)
        with pytest.raises(SeekError):
            s.seek(0)
        with pytest.raises(SeekError):
            s.reset()
    finally:
        fan.close()


def test_fan_out_eof_returns_false_on_subsequent_reads(test_video_file):
    """After end-of-stream, read() keeps returning False (matches VideoStream protocol)."""
    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=1)
    fan.start()
    try:
        s = fan.stream(0)
        # Drain.
        while s.read() is not False:
            pass
        # Subsequent reads must continue to return False, not block.
        assert s.read() is False
        assert s.read() is False
    finally:
        fan.close()


def test_fan_out_metadata_forwarded(test_video_file):
    """Consumer's frame_rate / frame_size / duration / path match the source."""
    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=2)
    fan.start()
    try:
        for i in range(2):
            s = fan.stream(i)
            assert s.frame_rate == source.frame_rate
            assert s.frame_size == source.frame_size
            assert s.duration == source.duration
            assert s.path == source.path
            assert s.name == source.name
            assert s.is_seekable is False
    finally:
        fan.close()


def test_fan_out_cut_list_matches_direct_detect(test_video_file):
    """Cut list from SceneManager+FanOut(n=1) matches the production detect() helper.

    Catches any subtle protocol-conformance bug in the consumer side that would
    affect detector output.
    """
    baseline_scenes = detect(test_video_file, ContentDetector())
    baseline_cuts = [scene[1].frame_num for scene in baseline_scenes]

    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=1)
    fan.start()
    try:
        sm = SceneManager()
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video=fan.stream(0))
        cuts = [scene[1].frame_num for scene in sm.get_scene_list()]
    finally:
        fan.close()

    assert cuts == baseline_cuts


def test_fan_out_parallel_detection_matches_baseline(test_video_file):
    """Two detectors run in parallel from one decode produce the same cut lists as
    two independent detect() calls."""
    cd_default = ContentDetector()
    cd_loose = ContentDetector(threshold=15.0)
    baseline_default = detect(test_video_file, ContentDetector())
    baseline_loose = detect(test_video_file, ContentDetector(threshold=15.0))
    # Use fresh detector instances inside the fan-out (cd_default/cd_loose above were used).
    del cd_default, cd_loose

    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=2, prefetch=4)
    fan.start()
    results: list[list[int]] = [[], []]

    def worker(i: int, det) -> None:
        sm = SceneManager()
        sm.add_detector(det)
        sm.detect_scenes(video=fan.stream(i))
        results[i] = [scene[1].frame_num for scene in sm.get_scene_list()]

    detectors = [ContentDetector(), ContentDetector(threshold=15.0)]
    threads = [threading.Thread(target=worker, args=(i, detectors[i])) for i in range(2)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        fan.close()

    assert results[0] == [scene[1].frame_num for scene in baseline_default]
    assert results[1] == [scene[1].frame_num for scene in baseline_loose]


def test_fan_out_prefetch_zero_rendezvous(test_video_file):
    """prefetch=0 still produces correct frames (uses maxsize=1 internally)."""
    source = open_video(test_video_file)
    fan = FanOutVideoStream(source, n=2, prefetch=0)
    fan.start()
    results: list[int] = [0, 0]

    def worker(i: int) -> None:
        s = fan.stream(i)
        while s.read() is not False:
            results[i] += 1

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        fan.close()

    assert results[0] == results[1] > 0
