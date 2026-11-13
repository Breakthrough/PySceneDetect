#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Tests for scenedetect.output module."""

import json
import logging
import os
import typing as ty
from fractions import Fraction
from io import StringIO
from pathlib import Path
from xml.etree import ElementTree

import pytest

from scenedetect import (
    ContentDetector,
    FrameTimecode,
    SceneManager,
    VideoStreamCv2,
    open_video,
    save_images,
)
from scenedetect.output import (
    SceneMetadata,
    VideoMetadata,
    _escape_ffmetadata,
    _open_output_file,
    is_ffmpeg_available,
    split_video_ffmpeg,
    write_scene_list,
    write_scene_list_edl,
    write_scene_list_fcp7,
    write_scene_list_fcpx,
    write_scene_list_ffmetadata,
    write_scene_list_otio,
)

FFMPEG_ARGS = (
    "-vf crop=128:128:0:0 -map 0:v:0 -c:v libx264 -preset ultrafast -qp 0 -tune zerolatency"
)
"""Only encodes a small crop of the frame and tuned for performance to speed up tests."""


@pytest.mark.skipif(condition=not is_ffmpeg_available(), reason="ffmpeg is not available")
def test_split_video_ffmpeg_default(tmp_path, test_movie_clip, caplog):
    caplog.set_level(logging.INFO, logger="pyscenedetect")
    video = open_video(test_movie_clip)
    # Extract three hard-coded scenes for testing, each 30 frames.
    scenes = [
        (video.base_timecode + 30, video.base_timecode + 60),
        (video.base_timecode + 60, video.base_timecode + 90),
        (video.base_timecode + 90, video.base_timecode + 120),
    ]
    assert (
        split_video_ffmpeg(test_movie_clip, scenes, output_dir=tmp_path, arg_override=FFMPEG_ARGS)
        == 0
    )
    # The default filename format should be VIDEO_NAME-Scene-SCENE_NUMBER.mp4.
    video_name = Path(test_movie_clip).stem
    entries = sorted(tmp_path.glob(f"{video_name}-Scene-*"))
    assert len(entries) == len(scenes)
    # The log should show the output folder, not the filename template.
    assert f"Output folder:\n  {tmp_path}" in caplog.text


@pytest.mark.skipif(condition=not is_ffmpeg_available(), reason="ffmpeg is not available")
def test_split_video_ffmpeg_formatter(tmp_path, test_movie_clip):
    video = open_video(test_movie_clip)
    # Extract three hard-coded scenes for testing, each 30 frames.
    scenes = [
        (video.base_timecode + 30, video.base_timecode + 60),
        (video.base_timecode + 60, video.base_timecode + 90),
        (video.base_timecode + 90, video.base_timecode + 120),
    ]

    # Custom filename formatter:
    def name_formatter(video: VideoMetadata, scene: SceneMetadata):
        return "abc" + video.name + "-123-" + str(scene.index) + ".mp4"

    assert (
        split_video_ffmpeg(
            test_movie_clip,
            scenes,
            output_dir=tmp_path,
            arg_override=FFMPEG_ARGS,
            formatter=name_formatter,
        )
        == 0
    )
    video_name = Path(test_movie_clip).stem
    entries = sorted(tmp_path.glob(f"abc{video_name}-123-*"))
    assert len(entries) == len(scenes)


# TODO: Add tests for `split_video_mkvmerge`.


def test_save_images(test_video_file, tmp_path: Path):
    """Test scenedetect.scene_manager.save_images function."""
    video = VideoStreamCv2(test_video_file)
    sm = SceneManager()
    sm.add_detector(ContentDetector())

    image_name_glob = "scenedetect.tempfile.*.jpg"
    image_name_template = (
        "scenedetect.tempfile.$SCENE_NUMBER.$IMAGE_NUMBER.$FRAME_NUMBER.$TIMESTAMP_MS.$TIMECODE"
    )

    video_fps = video.frame_rate
    scene_list = [
        (FrameTimecode(start, video_fps), FrameTimecode(end, video_fps))
        for start, end in [(0, 100), (200, 300), (300, 400)]
    ]

    image_filenames = save_images(
        scene_list=scene_list,
        output_dir=tmp_path,
        video=video,
        num_images=3,
        image_extension="jpg",
        image_name_template=image_name_template,
        threading=False,
    )

    # Ensure images got created, and the proper number got created.
    total_images = 0
    for scene_number in image_filenames:
        for path in image_filenames[scene_number]:
            assert tmp_path.joinpath(path).exists(), f"expected {path} to exist"
            total_images += 1

    assert total_images == len([path for path in tmp_path.glob(image_name_glob)])


def test_save_images_singlethreaded(test_video_file, tmp_path: Path):
    """Test scenedetect.scene_manager.save_images function."""
    video = VideoStreamCv2(test_video_file)
    sm = SceneManager()
    sm.add_detector(ContentDetector())

    image_name_glob = "scenedetect.tempfile.*.jpg"
    image_name_template = (
        "scenedetect.tempfile.$SCENE_NUMBER.$IMAGE_NUMBER.$FRAME_NUMBER.$TIMESTAMP_MS.$TIMECODE"
    )

    video_fps = video.frame_rate
    scene_list = [
        (FrameTimecode(start, video_fps), FrameTimecode(end, video_fps))
        for start, end in [(0, 100), (200, 300), (300, 400)]
    ]

    image_filenames = save_images(
        scene_list=scene_list,
        output_dir=tmp_path,
        video=video,
        num_images=3,
        image_extension="jpg",
        image_name_template=image_name_template,
        threading=True,
    )

    # Ensure images got created, and the proper number got created.
    total_images = 0
    for scene_number in image_filenames:
        for path in image_filenames[scene_number]:
            assert tmp_path.joinpath(path).exists(), f"expected {path} to exist"
            total_images += 1

    assert total_images == len([path for path in tmp_path.glob(image_name_glob)])


@pytest.mark.parametrize("frame_margin", [1, 0.1, "0.1s", "00:00:00.100"])
def test_save_images_frame_margin_accepts_time_values(
    test_video_file, tmp_path: Path, frame_margin
):
    """save_images() should accept frame counts (int), seconds (float), and timecode strings."""
    video = VideoStreamCv2(test_video_file)
    video_fps = video.frame_rate
    scene_list = [
        (FrameTimecode(start, video_fps), FrameTimecode(end, video_fps))
        for start, end in [(0, 100), (200, 300)]
    ]
    image_filenames = save_images(
        scene_list=scene_list,
        output_dir=tmp_path,
        video=video,
        num_images=3,
        image_extension="jpg",
        image_name_template="scenedetect.tempfile.$SCENE_NUMBER.$IMAGE_NUMBER",
        frame_margin=frame_margin,
    )
    for paths in image_filenames.values():
        for path in paths:
            assert tmp_path.joinpath(path).exists()


def test_save_images_rejects_negative_margin(test_video_file, tmp_path: Path):
    video = VideoStreamCv2(test_video_file)
    scene_list = [(FrameTimecode(0, video.frame_rate), FrameTimecode(10, video.frame_rate))]
    with pytest.raises(ValueError):
        save_images(scene_list=scene_list, output_dir=tmp_path, video=video, frame_margin=-1)


# TODO: Test other functionality against zero width scenes.
def test_save_images_zero_width_scene(test_video_file, tmp_path: Path):
    """Test scenedetect.scene_manager.save_images guards against zero width scenes."""
    video = VideoStreamCv2(test_video_file)
    image_name_glob = "scenedetect.tempfile.*.jpg"
    image_name_template = "scenedetect.tempfile.$SCENE_NUMBER.$IMAGE_NUMBER"

    video_fps = video.frame_rate
    scene_list = [
        (FrameTimecode(start, video_fps), FrameTimecode(end, video_fps))
        for start, end in [(0, 0), (1, 1), (2, 3)]
    ]
    NUM_IMAGES = 10
    image_filenames = save_images(
        scene_list=scene_list,
        output_dir=tmp_path,
        video=video,
        num_images=10,
        image_extension="jpg",
        image_name_template=image_name_template,
    )
    assert len(image_filenames) == 3
    assert all(len(image_filenames[scene]) == NUM_IMAGES for scene in image_filenames)
    total_images = 0
    for scene_number in image_filenames:
        for path in image_filenames[scene_number]:
            assert tmp_path.joinpath(path).exists(), f"expected {path} to exist"
            total_images += 1

    assert total_images == len([path for path in tmp_path.glob(image_name_glob)])


@pytest.mark.parametrize("threading", [True, False])
@pytest.mark.parametrize(
    "interval,min_images,max_images,expected",
    [
        # Scenes are 100, 10, and 60 frames long: floor(length / 25) + 1 images each.
        (25, 1, None, [5, 1, 3]),
        ("25", 1, None, [5, 1, 3]),
        (25, 2, 4, [4, 2, 3]),
        # 1 second is 29.97 frames.
        ("1s", 1, None, [4, 1, 3]),
        (1.0, 1, None, [4, 1, 3]),
    ],
)
def test_save_images_interval(
    test_video_file, tmp_path: Path, threading, interval, min_images, max_images, expected
):
    """With `interval`, the number of images saved for each scene depends on its length."""
    video = VideoStreamCv2(test_video_file)
    video_fps = video.frame_rate
    scene_list = [
        (FrameTimecode(start, video_fps), FrameTimecode(end, video_fps))
        for start, end in [(0, 100), (200, 210), (300, 360)]
    ]
    image_filenames = save_images(
        scene_list=scene_list,
        output_dir=tmp_path,
        video=video,
        interval=interval,
        min_images=min_images,
        max_images=max_images,
        image_name_template="scenedetect.tempfile.$SCENE_NUMBER.$IMAGE_NUMBER",
        threading=threading,
    )
    assert [len(image_filenames[scene]) for scene in sorted(image_filenames)] == expected
    for paths in image_filenames.values():
        for path in paths:
            assert tmp_path.joinpath(path).exists(), f"expected {path} to exist"
    assert sum(expected) == len(list(tmp_path.glob("scenedetect.tempfile.*.jpg")))


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"num_images": 3, "interval": 25}, "num_images and interval cannot both be set"),
        ({"interval": 0}, "interval must be greater than 0"),
        ({"interval": "0s"}, "interval must be greater than 0"),
        ({"interval": 25, "min_images": 0}, "min_images must be greater than 0"),
        (
            {"interval": 25, "min_images": 3, "max_images": 2},
            "max_images must be greater than or equal to min_images",
        ),
        (
            {"num_images": 3, "max_images": 2},
            "min_images and max_images can only be used with interval",
        ),
        ({"min_images": 2}, "min_images and max_images can only be used with interval"),
    ],
)
def test_save_images_interval_rejects_invalid_arguments(
    test_video_file, tmp_path: Path, kwargs, error
):
    video = VideoStreamCv2(test_video_file)
    scene_list = [(FrameTimecode(0, video.frame_rate), FrameTimecode(10, video.frame_rate))]
    with pytest.raises(ValueError, match=error):
        save_images(scene_list=scene_list, output_dir=tmp_path, video=video, **kwargs)


#
# Scene-list export API (EDL / FCPXML / FCP7 xmeml / OTIO)
#
# These tests construct small synthetic scene lists so they do not require video
# decoding and stay fast. They assert the structural invariants each format must
# hold (e.g. rational time strings for FCPXML, `file://` URIs for xmeml, OTIO
# Clip.2 count matching scene count).

_FPS_NTSC = Fraction(24000, 1001)
_FPS_CFR = Fraction(30, 1)


def _fake_scenes(fps: Fraction, frames):
    return [(FrameTimecode(start, fps=fps), FrameTimecode(end, fps=fps)) for start, end in frames]


_OUTPUT_TARGET_KINDS = ("file_handle", "str", "path", "bytes")


def _make_output_target(
    tmp_path: Path, target_kind: str, filename: str
) -> tuple[ty.Any, ty.Callable[[], str]]:
    """Create one supported output target and a function that reads its text."""
    output_path = tmp_path / filename
    if target_kind == "file_handle":
        output_file = StringIO(newline="")
        return output_file, output_file.getvalue
    if target_kind == "str":
        output_target = str(output_path)
    elif target_kind == "bytes":
        output_target = os.fsencode(output_path)
    else:
        assert target_kind == "path"
        output_target = output_path
    return output_target, lambda: output_path.read_bytes().decode("utf-8")


def test_open_output_file_does_not_create_file_on_error(tmp_path: Path):
    """Verify that the decorator does not create a destination when output generation fails."""

    @_open_output_file("TEST")
    def failing_writer(output_file: ty.Any):
        output_file.write("partial output")
        raise RuntimeError("generation failed")

    output_path = tmp_path / "output.txt"
    with pytest.raises(RuntimeError, match="generation failed"):
        failing_writer(output_path)
    assert not output_path.exists()


def test_open_output_file_preserves_existing_file_on_error(tmp_path: Path):
    """The decorator does not clobber an existing destination when output generation fails."""

    @_open_output_file("TEST")
    def failing_writer(output_file: ty.Any):
        output_file.write("partial output")
        raise RuntimeError("generation failed")

    output_path = tmp_path / "output.txt"
    output_path.write_text("existing contents", encoding="utf-8")
    with pytest.raises(RuntimeError, match="generation failed"):
        failing_writer(output_path)
    assert output_path.read_text(encoding="utf-8") == "existing contents"


def test_open_output_file_missing_target_raises_type_error():
    """Omitting the output target raises the usual missing-argument TypeError, not KeyError."""
    with pytest.raises(TypeError, match="output_csv_file"):
        write_scene_list(scene_list=[])  # type: ignore[call-arg]


@pytest.mark.parametrize("target_kind", _OUTPUT_TARGET_KINDS)
def test_write_scene_list_output_target(tmp_path: Path, target_kind: str):
    """CSV output accepts a file handle, string, Path, or bytes path."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 60)])
    output_target, read_output = _make_output_target(tmp_path, target_kind, "scenes.csv")
    write_scene_list(output_target, scenes, include_cut_list=False)
    text = read_output()
    assert "Scene Number" in text
    assert "00:00:00.000" in text
    assert "\r\n" not in text


def test_write_scene_list_rejects_invalid_output_target():
    """The shared output decorator rejects objects that are neither paths nor writable files."""
    scenes = [(FrameTimecode(0, 24.0), FrameTimecode(24, 24.0))]
    with pytest.raises(TypeError, match="output_csv_file"):
        write_scene_list(ty.cast(ty.Any, object()), scenes)


def test_write_scene_list_cut_list_row_without_cut_list():
    """The cut list row is labelled whether the cut list is passed in or derived from the scenes."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 60), (60, 90)])
    derived, explicit = StringIO(), StringIO()
    write_scene_list(derived, scenes)
    write_scene_list(explicit, scenes, cut_list=[scenes[1][0], scenes[2][0]])
    assert derived.getvalue().splitlines()[0] == "Timecode List:,00:00:01.000,00:00:02.000"
    assert derived.getvalue() == explicit.getvalue()


def test_write_scene_list_edl(tmp_path: Path):
    """EDL output has title header, FCM line, and one event per scene in CMX 3600 format."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 60)])
    output_path = tmp_path / "scenes.edl"
    write_scene_list_edl(output_path, scenes, title="my-clip", reel="AX")

    content = output_path.read_text()
    assert "TITLE: my-clip" in content
    assert "FCM: NON-DROP FRAME" in content
    assert "001  AX V     C        00:00:00:00 00:00:01:00 00:00:00:00 00:00:01:00" in content
    assert "002  AX V     C        00:00:01:00 00:00:02:00 00:00:01:00 00:00:02:00" in content


@pytest.mark.parametrize("target_kind", _OUTPUT_TARGET_KINDS)
def test_write_scene_list_edl_output_target(tmp_path: Path, target_kind: str):
    """EDL output accepts a file handle, string, Path, or bytes path."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    output_target, read_output = _make_output_target(tmp_path, target_kind, "scenes.edl")
    write_scene_list_edl(output_target, scenes, title="Tést")
    text = read_output()
    assert "TITLE: Tést" in text
    assert "\r\n" not in text


def test_write_scene_list_edl_with_start_timecode_smpte(tmp_path: Path):
    """`start_timecode` shifts every event by the supplied SMPTE offset (source + record)."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 60)])
    output_path = tmp_path / "scenes.edl"
    write_scene_list_edl(output_path, scenes, start_timecode="01:00:00:00")

    content = output_path.read_text()
    assert "001  AX V     C        01:00:00:00 01:00:01:00 01:00:00:00 01:00:01:00" in content
    assert "002  AX V     C        01:00:01:00 01:00:02:00 01:00:01:00 01:00:02:00" in content


def test_write_scene_list_edl_with_start_timecode_digits(tmp_path: Path):
    """8-digit form (numpad-friendly) yields the same output as the colon-separated form."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 60)])
    smpte_path = tmp_path / "smpte.edl"
    digits_path = tmp_path / "digits.edl"
    write_scene_list_edl(smpte_path, scenes, start_timecode="01:00:00:00")
    write_scene_list_edl(digits_path, scenes, start_timecode="01000000")

    assert smpte_path.read_text() == digits_path.read_text()


def test_write_scene_list_edl_with_start_timecode_subsecond(tmp_path: Path):
    """A sub-second frame offset (FF component) is added to every event."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    output_path = tmp_path / "scenes.edl"
    write_scene_list_edl(output_path, scenes, start_timecode="00:00:00:15")

    content = output_path.read_text()
    assert "001  AX V     C        00:00:00:15 00:00:01:15 00:00:00:15 00:00:01:15" in content


def test_write_scene_list_edl_default_no_offset(tmp_path: Path):
    """Omitting `start_timecode` (or passing ``None``/empty) preserves the existing baseline."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 60)])
    baseline = tmp_path / "baseline.edl"
    explicit_none = tmp_path / "none.edl"
    explicit_empty = tmp_path / "empty.edl"
    write_scene_list_edl(baseline, scenes)
    write_scene_list_edl(explicit_none, scenes, start_timecode=None)
    write_scene_list_edl(explicit_empty, scenes, start_timecode="   ")

    assert baseline.read_text() == explicit_none.read_text() == explicit_empty.read_text()


@pytest.mark.parametrize(
    "bad_value",
    [
        "bogus",
        "00:00:00",  # 3 segments, not 4
        "00:00:00:00:00",  # 5 segments
        "1234567",  # 7 digits
        "123456789",  # 9 digits
        "ab:cd:ef:gh",  # non-numeric
    ],
)
def test_write_scene_list_edl_with_start_timecode_invalid_format(tmp_path: Path, bad_value: str):
    """Malformed start timecodes raise ValueError before writing."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    output_path = tmp_path / "scenes.edl"
    output_path.write_text("existing output", encoding="utf-8")
    with pytest.raises(ValueError):
        write_scene_list_edl(output_path, scenes, start_timecode=bad_value)
    assert output_path.read_text(encoding="utf-8") == "existing output"


@pytest.mark.parametrize(
    "bad_value",
    [
        "00:60:00:00",  # MM=60
        "00:00:60:00",  # SS=60
        "00:00:00:99",  # FF beyond ceil(30 fps)
    ],
)
def test_write_scene_list_edl_with_start_timecode_out_of_range(tmp_path: Path, bad_value: str):
    """Out-of-range SMPTE components raise ValueError."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    with pytest.raises(ValueError):
        write_scene_list_edl(tmp_path / "scenes.edl", scenes, start_timecode=bad_value)


@pytest.mark.parametrize(
    "fps,frames,expected",
    [
        # 23.976: a hard cut every 7200 frames is exactly every 5 minutes of NDF timecode (#593).
        (Fraction(24000, 1001), [(0, 7200), (7200, 14400)], ["00:05:00:00", "00:10:00:00"]),
        (Fraction(30000, 1001), [(0, 108000)], ["01:00:00:00"]),
        (Fraction(60000, 1001), [(0, 216000)], ["01:00:00:00"]),
        # Whole-number rates count the same way; frame 90000 at 25 fps is exactly one hour.
        (Fraction(25, 1), [(0, 90000)], ["01:00:00:00"]),
    ],
)
def test_write_scene_list_edl_counts_frames_at_nominal_rate(
    tmp_path: Path, fps: Fraction, frames, expected
):
    """Non-drop-frame timecodes count 24/30/60 frames per timecode second at NTSC rates rather
    than following wall-clock seconds, which drifts about 3.6 s/hour (#593)."""
    output_path = tmp_path / "scenes.edl"
    write_scene_list_edl(output_path, _fake_scenes(fps, frames))
    events = [line for line in output_path.read_text().splitlines() if " AX V " in line]
    assert [line.split()[5] for line in events] == expected


def test_write_scene_list_edl_start_timecode_ntsc_round_trips(tmp_path: Path):
    """A start timecode is read as non-drop-frame too, so `01:00:00:00` at 29.97 fps is written
    back as `01:00:00:00` (previously `00:59:59:29`) (#593)."""
    scenes = _fake_scenes(Fraction(30000, 1001), [(0, 30)])
    output_path = tmp_path / "scenes.edl"
    write_scene_list_edl(output_path, scenes, start_timecode="01:00:00:00")
    assert "001  AX V     C        01:00:00:00 01:00:01:00 01:00:00:00 01:00:01:00" in (
        output_path.read_text()
    )


def test_write_scene_list_edl_start_timecode_ff_bound_uses_nominal_rate():
    """At 29.97 fps the FF field runs 00-29, matching the 30 frames per NDF timecode second."""
    scenes = _fake_scenes(Fraction(30000, 1001), [(0, 30)])
    write_scene_list_edl(StringIO(), scenes, start_timecode="00:00:00:29")
    with pytest.raises(ValueError, match="FF<30"):
        write_scene_list_edl(StringIO(), scenes, start_timecode="00:00:00:30")


def test_write_scene_list_edl_non_standard_rate_uses_wall_clock(tmp_path: Path):
    """Rates with no nominal frame count (here 12.5 fps) keep the wall-clock approximation."""
    scenes = _fake_scenes(Fraction(25, 2), [(0, 12), (12, 13), (13, 25)])
    output_path = tmp_path / "scenes.edl"
    write_scene_list_edl(output_path, scenes, start_timecode="00:00:01:00")
    content = output_path.read_text()
    # The start timecode of one second is 12.5 frames, rounded to 12, shifting every event.
    assert "001  AX V     C        00:00:00:12 00:00:01:11 00:00:00:12 00:00:01:11" in content
    assert "002  AX V     C        00:00:01:11 00:00:02:00 00:00:01:11 00:00:02:00" in content
    assert "003  AX V     C        00:00:02:00 00:00:02:12 00:00:02:00 00:00:02:12" in content


def test_write_scene_list_ffmetadata(tmp_path: Path):
    """FFmetadata output has the header and one chapter block per scene, in milliseconds."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 90)])
    output_path = tmp_path / "chapters.txt"
    write_scene_list_ffmetadata(output_path, scenes)

    assert output_path.read_text() == (
        ";FFMETADATA1\n"
        "[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=1000\ntitle=Scene 1\n"
        "[CHAPTER]\nTIMEBASE=1/1000\nSTART=1000\nEND=3000\ntitle=Scene 2\n"
    )


def test_write_scene_list_ffmetadata_empty_scene_list(tmp_path: Path):
    """An empty scene list still writes a valid FFmetadata header with no chapters."""
    output_path = tmp_path / "chapters.txt"
    write_scene_list_ffmetadata(output_path, [])
    assert output_path.read_text() == ";FFMETADATA1\n"


@pytest.mark.parametrize("target_kind", _OUTPUT_TARGET_KINDS)
def test_write_scene_list_ffmetadata_output_target(tmp_path: Path, target_kind: str):
    """FFmetadata output accepts a file handle, string, Path, or bytes path."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    output_target, read_output = _make_output_target(tmp_path, target_kind, "chapters.txt")
    write_scene_list_ffmetadata(output_target, scenes, title_format_template="Tést $SCENE_NUMBER")
    text = read_output()
    assert text.startswith(";FFMETADATA1\n")
    assert "title=Tést 1" in text
    assert "\r\n" not in text


@pytest.mark.parametrize(
    "fps,end_frame,expected_end_ms",
    [
        (Fraction(24, 1), 7200, 300000),
        (Fraction(25, 1), 7200, 288000),
        (Fraction(30, 1), 7200, 240000),
        (Fraction(24000, 1001), 7200, 300300),
        (Fraction(30000, 1001), 7200, 240240),
        (Fraction(60000, 1001), 7200, 120120),
    ],
)
def test_write_scene_list_ffmetadata_frame_rates(
    tmp_path: Path, fps: Fraction, end_frame: int, expected_end_ms: int
):
    """Chapter times match the exact frame time at both whole and fractional frame rates."""
    scenes = _fake_scenes(fps, [(0, end_frame)])
    output_path = tmp_path / "chapters.txt"
    write_scene_list_ffmetadata(output_path, scenes)
    assert f"END={expected_end_ms}\n" in output_path.read_text()


def test_write_scene_list_ffmetadata_rounds_up(tmp_path: Path):
    """Chapter times round up to the next millisecond, so a chapter never starts before its scene.
    Frame 12 at 23.976 fps is at 500.5 ms, which should be written as 501."""
    scenes = _fake_scenes(Fraction(24000, 1001), [(0, 12), (12, 24)])
    output_path = tmp_path / "chapters.txt"
    write_scene_list_ffmetadata(output_path, scenes)
    content = output_path.read_text()
    assert "START=0\nEND=501\n" in content
    assert "START=501\nEND=1001\n" in content


def test_write_scene_list_ffmetadata_title_format(tmp_path: Path):
    """title_format_template replaces $SCENE_NUMBER with the 1-based scene number."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 60), (60, 90)])
    output_path = tmp_path / "chapters.txt"
    write_scene_list_ffmetadata(output_path, scenes, title_format_template="Shot $SCENE_NUMBER")
    titles = [line for line in output_path.read_text().splitlines() if line.startswith("title=")]
    assert titles == ["title=Shot 1", "title=Shot 2", "title=Shot 3"]


def test_write_scene_list_ffmetadata_escapes_title(tmp_path: Path):
    """Special characters in chapter titles are escaped so ffmpeg reads them literally."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    output_path = tmp_path / "chapters.txt"
    write_scene_list_ffmetadata(output_path, scenes, title_format_template="A=B; #$SCENE_NUMBER")
    assert "title=A\\=B\\; \\#1\n" in output_path.read_text()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Scene 1", "Scene 1"),
        ("a=b", "a\\=b"),
        ("a;b", "a\\;b"),
        ("#1", "\\#1"),
        ("back\\slash", "back\\\\slash"),
        ("two\nlines", "two\\\nlines"),
        ("two\r\nlines", "two\\\r\\\nlines"),
        ("ends in \\", "ends in \\\\ "),
        ("=;#\\", "\\=\\;\\#\\\\ "),
    ],
)
def test_escape_ffmetadata(value: str, expected: str):
    """Each FFmetadata special character is escaped with a single backslash."""
    assert _escape_ffmetadata(value) == expected


@pytest.mark.skipif(not is_ffmpeg_available(), reason="ffmpeg is not available")
def test_write_scene_list_ffmetadata_ffmpeg_roundtrip(test_video_file, tmp_path: Path):
    """ffmpeg can mux the generated chapters into a video and reads them back."""
    import subprocess

    scenes = _fake_scenes(_FPS_CFR, [(0, 30), (30, 60)])
    chapters_path = tmp_path / "chapters.txt"
    output_path = tmp_path / "output.mp4"
    write_scene_list_ffmetadata(chapters_path, scenes)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            test_video_file,
            "-i",
            str(chapters_path),
            "-map_chapters",
            "1",
            "-codec",
            "copy",
            str(output_path),
        ],
        check=True,
    )
    probe = subprocess.run(
        ["ffmpeg", "-i", str(output_path)], capture_output=True, text=True, check=False
    )
    assert "Chapter #0:0: start 0.000000, end 1.000000" in probe.stderr
    assert "Chapter #0:1: start 1.000000, end 2.000000" in probe.stderr
    assert "title           : Scene 2" in probe.stderr


def test_write_scene_list_fcpx(tmp_path: Path):
    """FCPXML output declares version 1.9, rational time strings, and an asset-clip per scene."""
    scenes = _fake_scenes(_FPS_NTSC, [(48, 96), (96, 144)])
    output_path = tmp_path / "scenes.xml"
    # `video_path` need not exist; only `.absolute().as_uri()` is called on it.
    write_scene_list_fcpx(
        output_path=output_path,
        scene_list=scenes,
        video_path=tmp_path / "fake_video.mp4",
        frame_rate=_FPS_NTSC,
        frame_size=(1280, 544),
    )

    root = ElementTree.parse(output_path).getroot()
    assert root.tag == "fcpxml"
    assert root.attrib["version"] == "1.9"

    fmt = root.find("resources/format")
    assert fmt is not None
    # 24000/1001 fps -> frameDuration is the reciprocal: 1001/24000s.
    assert fmt.attrib["frameDuration"] == "1001/24000s"
    assert fmt.attrib["width"] == "1280"
    assert fmt.attrib["height"] == "544"

    media_rep = root.find("resources/asset/media-rep")
    assert media_rep is not None
    assert media_rep.attrib["src"].startswith("file://")

    clips = root.findall("library/event/project/sequence/spine/asset-clip")
    assert len(clips) == 2
    for clip in clips:
        for attr in ("offset", "start", "duration"):
            assert clip.attrib[attr].endswith("s")


def test_write_scene_list_fcpx_video_name_defaults_to_path_stem(tmp_path: Path):
    """Omitting `video_name` falls back to the stem of `video_path`."""
    scenes = _fake_scenes(_FPS_NTSC, [(0, 24)])
    output_path = tmp_path / "scenes.xml"
    write_scene_list_fcpx(
        output_path=output_path,
        scene_list=scenes,
        video_path=tmp_path / "my_clip.mp4",
        frame_rate=_FPS_NTSC,
        frame_size=(640, 360),
    )
    root = ElementTree.parse(output_path).getroot()
    asset = root.find("resources/asset")
    assert asset is not None and asset.attrib["name"] == "my_clip"


@pytest.mark.parametrize("target_kind", _OUTPUT_TARGET_KINDS)
def test_write_scene_list_fcpx_output_target(tmp_path: Path, target_kind: str):
    """FCPXML output accepts a file handle, string, Path, or bytes path."""
    scenes = _fake_scenes(_FPS_NTSC, [(48, 96), (96, 144)])
    output_target, read_output = _make_output_target(tmp_path, target_kind, "scenes.xml")
    # `video_path` need not exist; only `.absolute().as_uri()` is called on it.
    write_scene_list_fcpx(
        output_path=output_target,
        scene_list=scenes,
        video_path=Path("fake_video.mp4"),
        frame_rate=_FPS_NTSC,
        frame_size=(1280, 544),
    )
    text = read_output()
    assert text.startswith('<?xml version="1.0"')
    assert "\r\n" not in text


def test_write_scene_list_fcp7(tmp_path: Path):
    """FCP7 xmeml declares version 5, a clipitem per scene, and a shared <file id> reference."""
    scenes = _fake_scenes(_FPS_NTSC, [(0, 48), (48, 96)])
    output_path = tmp_path / "scenes.xml"
    write_scene_list_fcp7(
        output_path=output_path,
        scene_list=scenes,
        video_path=tmp_path / "source.mp4",
        frame_rate=_FPS_NTSC,
        frame_size=(1920, 1080),
        source_duration=FrameTimecode(240, fps=_FPS_NTSC),
    )

    root = ElementTree.parse(output_path).getroot()
    assert root.tag == "xmeml"
    assert root.attrib["version"] == "5"

    ntsc = root.find("project/sequence/rate/ntsc")
    assert ntsc is not None and ntsc.text == "True"

    clipitems = root.findall("project/sequence/media/video/track/clipitem")
    assert len(clipitems) == 2
    # First clipitem carries the full <file> declaration; later ones reference it by id.
    first_file = clipitems[0].find("file")
    assert first_file is not None and first_file.attrib["id"] == "file1"
    pathurl = first_file.find("pathurl")
    assert pathurl is not None and pathurl.text is not None
    assert pathurl.text.startswith("file://")
    assert first_file.find("duration") is not None
    second_file = clipitems[1].find("file")
    assert second_file is not None and second_file.attrib["id"] == "file1"
    assert second_file.find("pathurl") is None


def test_write_scene_list_fcp7_cfr_sets_ntsc_false(tmp_path: Path):
    """Integer frame rates (denominator == 1) must set ntsc="False"."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    output_path = tmp_path / "scenes.xml"
    write_scene_list_fcp7(
        output_path=output_path,
        scene_list=scenes,
        video_path=tmp_path / "source.mp4",
        frame_rate=_FPS_CFR,
        frame_size=(640, 360),
    )
    root = ElementTree.parse(output_path).getroot()
    ntsc = root.find("project/sequence/rate/ntsc")
    assert ntsc is not None and ntsc.text == "False"


@pytest.mark.parametrize("target_kind", _OUTPUT_TARGET_KINDS)
def test_write_scene_list_fcp7_output_target(tmp_path: Path, target_kind: str):
    """FCP7 XML output accepts a file handle, string, Path, or bytes path."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    output_target, read_output = _make_output_target(tmp_path, target_kind, "scenes.xml")
    write_scene_list_fcp7(
        output_target,
        scene_list=scenes,
        video_path=Path("source.mp4"),
        frame_rate=_FPS_CFR,
        frame_size=(640, 360),
    )
    text = read_output()
    assert text.startswith('<?xml version="1.0"')
    assert "\r\n" not in text


def test_write_scene_list_otio(tmp_path: Path):
    """OTIO output is valid JSON with a Timeline.1 schema and one Clip.2 per scene per track."""
    scenes = _fake_scenes(_FPS_NTSC, [(24, 72), (72, 120)])
    output_path = tmp_path / "scenes.otio"
    write_scene_list_otio(
        output_path=output_path,
        scene_list=scenes,
        video_path=tmp_path / "clip.mp4",
        frame_rate=_FPS_NTSC,
        name="my-timeline",
    )

    doc = json.loads(output_path.read_text())
    assert doc["OTIO_SCHEMA"] == "Timeline.1"
    assert doc["name"] == "my-timeline"
    assert doc["global_start_time"]["rate"] == pytest.approx(float(_FPS_NTSC))

    tracks = doc["tracks"]["children"]
    # Default `audio=True` yields both a video and an audio track.
    assert [t["kind"] for t in tracks] == ["Video", "Audio"]
    for track in tracks:
        assert len(track["children"]) == len(scenes)
        for clip in track["children"]:
            assert clip["OTIO_SCHEMA"] == "Clip.2"
            ref = clip["media_references"]["DEFAULT_MEDIA"]
            assert ref["OTIO_SCHEMA"] == "ExternalReference.1"
            assert Path(ref["target_url"]).is_absolute()


def test_write_scene_list_otio_no_audio(tmp_path: Path):
    """`audio=False` omits the audio track."""
    scenes = _fake_scenes(_FPS_NTSC, [(0, 24)])
    output_path = tmp_path / "scenes.otio"
    write_scene_list_otio(
        output_path=output_path,
        scene_list=scenes,
        video_path=tmp_path / "clip.mp4",
        frame_rate=_FPS_NTSC,
        audio=False,
    )
    doc = json.loads(output_path.read_text())
    tracks = doc["tracks"]["children"]
    assert [t["kind"] for t in tracks] == ["Video"]


def test_write_scene_list_otio_rational_time_precision(tmp_path: Path):
    """Serialized frame-count values must be free of sub-10us float drift (cf. 914ca31)."""
    # Frames on integer-frame boundaries under NTSC 24000/1001: seconds * 23.976...
    # should land on integers but floats can produce values like 214.00001 without
    # the explicit round(..., 6) in the writer.
    scenes = _fake_scenes(
        _FPS_NTSC,
        [(start, start + 24) for start in (0, 24, 48, 96, 120)],
    )
    output_path = tmp_path / "scenes.otio"
    write_scene_list_otio(
        output_path=output_path,
        scene_list=scenes,
        video_path=tmp_path / "clip.mp4",
        frame_rate=_FPS_NTSC,
    )
    doc = json.loads(output_path.read_text())
    for track in doc["tracks"]["children"]:
        for clip in track["children"]:
            for key in ("start_time", "duration"):
                value = clip["source_range"][key]["value"]
                assert value == round(value, 6), f"value {value!r} carries sub-10us float drift"


@pytest.mark.parametrize("target_kind", _OUTPUT_TARGET_KINDS)
def test_write_scene_list_otio_output_target(tmp_path: Path, target_kind: str):
    """OTIO output accepts a file handle, string, Path, or bytes path."""
    scenes = _fake_scenes(_FPS_NTSC, [(24, 72), (72, 120)])
    output_target, read_output = _make_output_target(tmp_path, target_kind, "scenes.otio")
    write_scene_list_otio(
        output_path=output_target,
        scene_list=scenes,
        video_path=tmp_path / "clip.mp4",
        frame_rate=_FPS_NTSC,
        name="my-timeline",
    )
    text = read_output()
    assert "\r\n" not in text
    doc = json.loads(text)
    assert doc["OTIO_SCHEMA"] == "Timeline.1"


@pytest.mark.parametrize("frame_rate", [_FPS_CFR, _FPS_NTSC])
@pytest.mark.parametrize("audio", [False, True])
@pytest.mark.parametrize("ranges", [[], [(0, 24)], [(2400, 4800)], [(24, 72), (3000, 3600)]])
def test_write_scene_list_otio_unknown_available_range(tmp_path, frame_rate, audio, ranges):
    """Scene ranges do not reveal the source video's full available duration."""
    output_path = tmp_path / "scenes.otio"
    write_scene_list_otio(
        output_path,
        scene_list=_fake_scenes(frame_rate, ranges),
        video_path=tmp_path / "source.mp4",
        frame_rate=frame_rate,
        audio=audio,
    )

    doc = json.loads(output_path.read_text())
    tracks = doc["tracks"]["children"]
    assert len(tracks) == (2 if audio else 1)
    for track in tracks:
        assert len(track["children"]) == len(ranges)
        for clip, (start, end) in zip(track["children"], ranges, strict=True):
            ref = clip["media_references"]["DEFAULT_MEDIA"]
            assert ref["available_range"] is None
            assert clip["source_range"]["start_time"]["value"] == pytest.approx(start)
            assert clip["source_range"]["duration"]["value"] == pytest.approx(end - start)


@pytest.mark.parametrize("frame_rate", [_FPS_CFR, _FPS_NTSC])
@pytest.mark.parametrize("source_frame_rate", [_FPS_CFR, _FPS_NTSC])
@pytest.mark.parametrize("source_frames", [0, 6000])
@pytest.mark.parametrize("audio", [False, True])
def test_write_scene_list_otio_source_duration(
    tmp_path, frame_rate, source_frame_rate, source_frames, audio
):
    """Available media duration uses the full source, not the selected scenes."""
    source_duration = FrameTimecode(source_frames, fps=source_frame_rate)
    ranges = [(24, 72), (120, 180)] if source_frames else [(0, 0)]
    output_path = tmp_path / "scenes.otio"
    write_scene_list_otio(
        output_path,
        scene_list=_fake_scenes(frame_rate, ranges),
        video_path=tmp_path / "source.mp4",
        frame_rate=frame_rate,
        audio=audio,
        source_duration=source_duration,
    )

    doc = json.loads(output_path.read_text())
    fps = float(frame_rate)
    expected_duration = round(source_duration.seconds * fps, 6)
    tracks = doc["tracks"]["children"]
    assert len(tracks) == (2 if audio else 1)
    for track in tracks:
        assert len(track["children"]) == len(ranges)
        for clip, (start, end) in zip(track["children"], ranges, strict=True):
            available = clip["media_references"]["DEFAULT_MEDIA"]["available_range"]
            assert available["OTIO_SCHEMA"] == "TimeRange.1"
            assert available["start_time"] == {
                "OTIO_SCHEMA": "RationalTime.1",
                "rate": fps,
                "value": 0.0,
            }
            assert available["duration"] == {
                "OTIO_SCHEMA": "RationalTime.1",
                "rate": fps,
                "value": expected_duration,
            }
            assert clip["source_range"]["start_time"]["value"] == pytest.approx(start)
            assert clip["source_range"]["duration"]["value"] == pytest.approx(end - start)
