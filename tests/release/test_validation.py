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
"""Output File Validation

Verifies that output files (videos, images, CSV, EDL, OTIO) are correctly generated and valid.
"""

import csv
import subprocess

import pytest

from scenedetect import (
    ContentDetector,
    SceneManager,
    open_video,
    split_video_ffmpeg,
)
from scenedetect.output import save_images, write_scene_list, write_scene_list_otio

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import opentimelineio as otio

    HAS_OTIO = True
except ImportError:
    HAS_OTIO = False


def _detect(video_path):
    video = open_video(video_path)
    sm = SceneManager()
    sm.add_detector(ContentDetector())
    sm.detect_scenes(video)
    return video, sm.get_scene_list()


@pytest.mark.release
def test_output_csv_roundtrip(test_video_file, tmp_path):
    _video, scene_list = _detect(test_video_file)
    csv_path = str(tmp_path / "scenes.csv")
    with open(csv_path, "w", newline="") as f:
        write_scene_list(f, scene_list, include_cut_list=False)

    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(scene_list)
    # write_scene_list emits 1-based start frames; reverse the offset.
    assert int(rows[0]["Start Frame"]) - 1 == scene_list[0][0].frame_num


@pytest.mark.release
def test_output_image_extensions(test_video_file, tmp_path):
    if not HAS_PIL:
        pytest.skip("Pillow not installed.")
    video, scene_list = _detect(test_video_file)
    # Limit to the first two scenes to keep the test fast.
    scene_list = scene_list[:2]

    for ext in ("jpg", "png", "webp"):
        out_dir = tmp_path / f"images_{ext}"
        out_dir.mkdir()
        save_images(
            scene_list,
            video,
            num_images=1,
            output_dir=str(out_dir),
            image_extension=ext,
            show_progress=False,
        )
        files = [p for p in out_dir.iterdir() if p.suffix == f".{ext}"]
        assert files, f"No {ext} images produced"
        for p in files:
            with Image.open(p) as img:
                img.verify()
                assert img.size[0] > 0 and img.size[1] > 0


@pytest.mark.release
def test_output_otio_rational_time_precision(test_video_file, tmp_path):
    if not HAS_OTIO:
        pytest.skip("opentimelineio not installed.")
    video, scene_list = _detect(test_video_file)
    otio_path = tmp_path / "scenes.otio"
    write_scene_list_otio(
        output_path=otio_path,
        scene_list=scene_list,
        video_path=test_video_file,
        frame_rate=video.frame_rate,
    )

    timeline = otio.adapters.read_from_file(str(otio_path))
    # One clip per scene, on each track (video + audio by default).
    video_track = timeline.tracks[0]
    assert len(list(video_track)) == len(scene_list)

    # `value` is a frame count derived from seconds * fps, serialized at 10µs
    # precision (round(..., 6)) per 914ca31. Guards the `90.00000000000001` class
    # of float-cast drift by asserting the rounded value never carries spurious
    # sub-10µs noise.
    for clip in video_track:
        for rt in (clip.source_range.start_time, clip.source_range.duration):
            assert abs(rt.value - round(rt.value, 6)) == 0, (
                f"RationalTime.value lost precision: {rt.value!r}"
            )


@pytest.mark.release
def test_output_split_video(test_video_file, tmp_path):
    _video, scene_list = _detect(test_video_file)
    # Split only the first two scenes to bound the runtime.
    scene_list = scene_list[:2]
    out_dir = tmp_path / "splits"
    out_dir.mkdir()
    output_template = str(out_dir / "scene-$SCENE_NUMBER.mp4")
    split_video_ffmpeg(test_video_file, scene_list, output_file_template=output_template)

    split_files = sorted(out_dir.glob("*.mp4"))
    assert len(split_files) == len(scene_list)

    for path in split_files:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert float(result.stdout.strip()) > 0
