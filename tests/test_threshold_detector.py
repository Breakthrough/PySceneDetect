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
"""Duration filtering for threshold-based fades."""

import csv

import cv2
import numpy as np
import pytest

from scenedetect import FrameTimecode, SceneManager, open_video
from scenedetect.detectors import ThresholdDetector
from tests.helpers import invoke_cli


def _detect_levels(levels, **kwargs):
    detector = ThresholdDetector(**kwargs)
    cuts = []
    for index, level in enumerate(levels):
        timecode = FrameTimecode(index, fps=10.0)
        cuts.extend(detector.process_frame(timecode, np.full((4, 4, 3), level, np.uint8)))
    cuts.extend(detector.post_process(timecode))
    return [cut.frame_num for cut in cuts]


@pytest.mark.parametrize("method", list(ThresholdDetector.Method))
@pytest.mark.parametrize("fade_bias, expected", [(-1.0, 22), (0.0, 25), (1.0, 28)])
def test_short_fade_does_not_affect_next_cut(method, fade_bias, expected):
    levels = [128] * 10 + [0] * 2 + [128] * 10 + [0] * 6 + [128] * 10
    if method == ThresholdDetector.Method.CEILING:
        levels = [255 - level for level in levels]
    assert _detect_levels(
        levels,
        threshold=128,
        method=method,
        min_scene_len=3,
        min_out_length=4,
        fade_bias=fade_bias,
    ) == [expected]


@pytest.mark.parametrize("out_length, expected", [(3, []), (4, [12]), (5, [12])])
@pytest.mark.parametrize("minimum", [4, 0.4, "0.4s", "00:00:00.400", FrameTimecode(4, 10.0)])
def test_min_out_length_boundary(out_length, expected, minimum):
    assert (
        _detect_levels(
            [128] * 10 + [0] * out_length + [128] * 10,
            min_scene_len=0,
            min_out_length=minimum,
        )
        == expected
    )


def test_min_scene_len_still_applies():
    levels = [128] * 10 + [0] * 4 + [128] * 3 + [0] * 4 + [128] * 10
    assert _detect_levels(levels, min_scene_len=10, min_out_length=4) == [12]
    assert _detect_levels(levels, min_scene_len=0, min_out_length=4) == [12, 19]


@pytest.mark.parametrize("out_length, expected", [(3, []), (4, [2]), (6, [3])])
def test_min_out_length_applies_to_leading_fade(out_length, expected):
    # A video that starts faded out should be measured from the *first* frame we process.
    levels = [0] * out_length + [128] * 10
    assert _detect_levels(levels, min_scene_len=0, min_out_length=4) == expected
    assert _detect_levels(levels, min_scene_len=0) == [round(out_length / 2)]


@pytest.mark.parametrize("minimum", [-1, -0.5])
def test_negative_min_out_length_rejected(minimum):
    with pytest.raises(ValueError):
        ThresholdDetector(min_out_length=minimum)


@pytest.mark.parametrize("add_final_scene", [False, True])
@pytest.mark.parametrize("out_length", [3, 4])
def test_final_fade_counts_last_frame(out_length, add_final_scene):
    assert _detect_levels(
        [128] * 10 + [0] * out_length,
        min_scene_len=0,
        min_out_length=4,
        add_final_scene=add_final_scene,
    ) == ([10] if add_final_scene and out_length == 4 else [])


def test_default_keeps_short_fades():
    levels = [128] * 10 + [0] * 2 + [128] * 10 + [0] * 3
    assert _detect_levels(levels, min_scene_len=0, add_final_scene=True) == [11, 22]
    assert _detect_levels(levels, min_scene_len=0, add_final_scene=True, min_out_length=0) == [
        11,
        22,
    ]


def _write_video(path, levels):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"MJPG"), 10, (64, 48))
    assert writer.isOpened()
    try:
        for level in levels:
            writer.write(np.full((48, 64, 3), level, np.uint8))
    finally:
        writer.release()
    return str(path)


@pytest.mark.parametrize("backend", ["opencv", "pyav"])
@pytest.mark.parametrize("final_out_length", [3, 4])
def test_min_out_length_decoded_video(tmp_path, auto_close, backend, final_out_length):
    if backend == "pyav":
        pytest.importorskip("av")
    levels = [128] * 10 + [0] * 2 + [128] * 10 + [0] * 6 + [128] * 10
    path = _write_video(tmp_path / "fades.avi", levels + [0] * final_out_length)
    video = auto_close(open_video(path, backend=backend))
    manager = SceneManager()
    manager.add_detector(
        ThresholdDetector(min_scene_len=0, min_out_length="0.4s", add_final_scene=True)
    )
    assert manager.detect_scenes(video) == len(levels) + final_out_length
    scenes = manager.get_scene_list()
    assert [start.frame_num for start, _ in scenes] == (
        [0, 25, 38] if final_out_length == 4 else [0, 25]
    )
    assert scenes[-1][1].frame_num == len(levels) + final_out_length


@pytest.mark.parametrize("minimum", ["4", "0.4s", "00:00:00.400"])
@pytest.mark.parametrize("use_config", [False, True])
def test_min_out_length_cli(tmp_path, minimum, use_config):
    levels = [128] * 10 + [0] * 2 + [128] * 10 + [0] * 6 + [128] * 10
    path = _write_video(tmp_path / "fades.avi", levels)
    args = ["-i", path, "-o", str(tmp_path), "-m", "0"]
    if use_config:
        config = tmp_path / "scenedetect.cfg"
        config.write_text(f"[detect-threshold]\nmin-out-length = {minimum}\n")
        args += ["-c", str(config), "detect-threshold"]
    else:
        args += ["detect-threshold", "--min-out-length", minimum]
    exit_code, output = invoke_cli([*args, "list-scenes", "-f", "scenes", "--skip-cuts"])
    assert exit_code == 0, output
    with (tmp_path / "scenes.csv").open(newline="") as scene_file:
        scenes = list(csv.DictReader(scene_file))
    assert [int(scene["Start Frame"]) - 1 for scene in scenes] == [0, 25]
