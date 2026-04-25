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
from fractions import Fraction
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
    is_ffmpeg_available,
    split_video_ffmpeg,
    write_scene_list_edl,
    write_scene_list_fcp7,
    write_scene_list_fcpx,
    write_scene_list_otio,
)

FFMPEG_ARGS = (
    "-vf crop=128:128:0:0 -map 0:v:0 -c:v libx264 -preset ultrafast -qp 0 -tune zerolatency"
)
"""Only encodes a small crop of the frame and tuned for performance to speed up tests."""


@pytest.mark.skipif(condition=not is_ffmpeg_available(), reason="ffmpeg is not available")
def test_split_video_ffmpeg_default(tmp_path, test_movie_clip):
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


def test_write_scene_list_edl_accepts_str_path(tmp_path: Path):
    """`output_path` must accept both Path and str."""
    scenes = _fake_scenes(_FPS_CFR, [(0, 30)])
    output_path = tmp_path / "scenes.edl"
    write_scene_list_edl(str(output_path), scenes)
    assert output_path.exists()


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
    with pytest.raises(ValueError):
        write_scene_list_edl(tmp_path / "scenes.edl", scenes, start_timecode=bad_value)


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
    # 24000/1001 fps → frameDuration is the reciprocal: 1001/24000s.
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
    """Serialized frame-count values must be free of sub-10µs float drift (cf. 914ca31)."""
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
                assert value == round(value, 6), f"value {value!r} carries sub-10µs float drift"
