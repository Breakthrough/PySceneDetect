"""CLI regression tests for the solid-color interval report."""

import csv
from pathlib import Path

import cv2
import numpy as np
import pytest
from click.testing import CliRunner

import scenedetect._cli as cli
from scenedetect._cli import commands
from scenedetect._cli.context import CliContext
from scenedetect._cli.controller import run_scenedetect
from tests.helpers import invoke_cli


@pytest.fixture
def solid_video(tmp_path: Path) -> Path:
    path = tmp_path / "solid.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (32, 32))
    assert writer.isOpened()
    texture = np.zeros((32, 32, 3), dtype=np.uint8)
    texture[:, 16:] = 255
    try:
        # Two solid runs, including a color change within one run and a trailing run.
        for frame, count in [
            (np.zeros_like(texture), 3),
            (np.full_like(texture, 255), 2),
            (texture, 15),
            (255 - texture, 15),
            (np.full_like(texture, 64), 4),
        ]:
            for _ in range(count):
                writer.write(frame)
    finally:
        writer.release()
    return path


def _args(video: Path, output: Path) -> list[str]:
    return ["-c", "scenedetect.cfg", "-i", str(video), "-o", str(output), "-q"]


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as report:
        return list(csv.DictReader(report))


def test_list_solid_csv(solid_video: Path, tmp_path: Path):
    exit_code, output = invoke_cli([*_args(solid_video, tmp_path), "list-solid"])
    assert exit_code == 0, output
    path = tmp_path / "solid-Solid.csv"
    assert path.read_text().splitlines()[0].startswith("Scene Number,Start Frame,")
    assert [(r["Start Frame"], r["End Frame"], r["Length (frames)"]) for r in _rows(path)] == [
        ("1", "5", "5"),
        ("36", "39", "4"),
    ]


def test_list_solid_empty_and_output_override(solid_video: Path, tmp_path: Path):
    destination = tmp_path / "report"
    exit_code, output = invoke_cli(
        [
            *_args(solid_video, tmp_path),
            "list-solid",
            "--min-frames",
            "100",
            "-o",
            str(destination),
            "-f",
            "$VIDEO_NAME-empty",
        ]
    )
    assert exit_code == 0, output
    path = destination / "solid-empty.csv"
    assert len(path.read_text().splitlines()) == 1
    assert _rows(path) == []


def test_list_solid_uses_config_and_source_timecodes(solid_video: Path, tmp_path: Path):
    config = tmp_path / "custom.cfg"
    config.write_text("[list-solid]\nfilename = configured\nmin-frames = 3\nthreshold = 0\n")
    exit_code, output = invoke_cli(
        [
            "-c",
            str(config),
            "-i",
            str(solid_video),
            "-o",
            str(tmp_path),
            "-q",
            "time",
            "--start",
            "2",
            "--end",
            "38",
            "list-solid",
        ]
    )
    assert exit_code == 0, output
    assert [(r["Start Frame"], r["End Frame"]) for r in _rows(tmp_path / "configured.csv")] == [
        ("2", "5"),
        ("36", "38"),
    ]


@pytest.mark.parametrize("report_first", [False, True])
def test_list_solid_preserves_implicit_scenes(
    solid_video: Path, tmp_path: Path, report_first: bool
):
    baseline = tmp_path / "baseline"
    assert invoke_cli([*_args(solid_video, baseline), "list-scenes"])[0] == 0
    scene_command = ["list-scenes"]
    report_command = ["list-solid"]
    command = report_command + scene_command if report_first else scene_command + report_command
    exit_code, output = invoke_cli([*_args(solid_video, tmp_path), *command])
    assert exit_code == 0, output
    expected = (baseline / "solid-Scenes.csv").read_text()
    assert len(expected.splitlines()) > 3  # The baseline actually contains a cut.
    assert (tmp_path / "solid-Scenes.csv").read_text() == expected


@pytest.mark.parametrize("scene_command", [None, "list-scenes", "split-video"])
@pytest.mark.parametrize("report_first", [False, True])
def test_list_solid_detector_selection_and_single_pass(
    solid_video: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scene_command: str | None,
    report_first: bool,
):
    # Avoid invoking an external encoder while checking split-video's implicit detector.
    monkeypatch.setattr(cli, "check_split_video_requirements", lambda **kwargs: None)
    split_scenes = []
    monkeypatch.setattr(
        commands, "split_video", lambda **kwargs: split_scenes.extend(kwargs["scenes"])
    )
    context = CliContext()
    command = ["list-solid"]
    if scene_command:
        command = [*command, scene_command] if report_first else [scene_command, *command]
    try:
        result = CliRunner().invoke(
            cli.scenedetect, [*_args(solid_video, tmp_path), *command], obj=context
        )
        assert result.exit_code == 0, result.output
        manager = context.scene_manager
        assert manager is not None
        original_detect = manager.detect_scenes
        calls = []

        def detect_once(**kwargs):
            calls.append(kwargs)
            return original_detect(**kwargs)

        monkeypatch.setattr(manager, "detect_scenes", detect_once)
        assert run_scenedetect(context)
        assert len(calls) == 1
        assert manager.get_num_detectors() == (2 if scene_command else 1)
        if scene_command == "split-video":
            assert len(split_scenes) > 1
    finally:
        if context.video_stream:
            context.video_stream.close()


@pytest.mark.parametrize("report_first", [False, True])
def test_list_solid_rejects_load_scenes(solid_video: Path, tmp_path: Path, report_first: bool):
    loaded = tmp_path / "scenes.csv"
    loaded.write_text("Start Frame\n1\n")
    load_command = ["load-scenes", "-i", str(loaded)]
    command = ["list-solid", *load_command] if report_first else [*load_command, "list-solid"]
    exit_code, output = invoke_cli([*_args(solid_video, tmp_path), *command])
    assert exit_code != 0
    assert "list-solid" in output and "load-scenes" in output


@pytest.mark.parametrize("report_first", [False, True])
def test_list_solid_rejects_frame_skip(solid_video: Path, tmp_path: Path, report_first: bool):
    command = ["list-solid", "list-scenes"] if report_first else ["list-scenes", "list-solid"]
    exit_code, output = invoke_cli([*_args(solid_video, tmp_path), "--frame-skip", "1", *command])
    assert exit_code != 0
    assert "list-solid" in output and "--frame-skip" in output


@pytest.mark.parametrize(
    "option,value",
    [("--threshold", "-1"), ("--threshold", "128"), ("--threshold", "nan"), ("--min-frames", "0")],
)
def test_list_solid_rejects_invalid_options(
    solid_video: Path, tmp_path: Path, option: str, value: str
):
    exit_code, output = invoke_cli([*_args(solid_video, tmp_path), "list-solid", option, value])
    assert exit_code != 0
    assert "Invalid value" in output


@pytest.mark.parametrize(
    "config,expected_error",
    [
        ("[list-solid]\nthreshold = nan\n", "finite"),
        ("[global]\nframe-skip = 1\n", "--frame-skip"),
    ],
)
def test_list_solid_rejects_invalid_config(
    solid_video: Path, tmp_path: Path, config: str, expected_error: str
):
    config_path = tmp_path / "invalid.cfg"
    config_path.write_text(config)
    exit_code, output = invoke_cli(
        ["-c", str(config_path), "-i", str(solid_video), "-q", "list-solid"]
    )
    assert exit_code != 0
    assert expected_error in output


def test_list_solid_preserves_implicit_stats(solid_video: Path, tmp_path: Path):
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    baseline_stats = baseline / "stats.csv"
    report_stats = tmp_path / "stats.csv"
    assert invoke_cli([*_args(solid_video, baseline), "-s", str(baseline_stats)])[0] == 0
    exit_code, output = invoke_cli(
        [*_args(solid_video, tmp_path), "-s", str(report_stats), "list-solid"]
    )
    assert exit_code == 0, output
    assert report_stats.read_text() == baseline_stats.read_text()
