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
"""CLI Permutation Smoke Tests

Exercises CLI command chains via subprocess.
"""

import os
import subprocess
import sys

import pytest


def _run(args, cwd):
    result = subprocess.run(
        [sys.executable, "-m", "scenedetect", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result


@pytest.mark.release
def test_cli_chain_smoke(test_video_file, tmp_path):
    # detect-content save-images list-scenes chain.
    result = _run(
        [
            "-i",
            os.path.abspath(test_video_file),
            "-o",
            str(tmp_path),
            "detect-content",
            "save-images",
            "list-scenes",
        ],
        cwd=os.path.abspath(os.path.dirname(test_video_file) + "/../.."),
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    csvs = [p for p in tmp_path.iterdir() if p.suffix == ".csv"]
    images = [p for p in tmp_path.iterdir() if p.suffix == ".jpg"]
    assert csvs, "No scenes CSV produced"
    assert images, "No scene images produced"


@pytest.mark.release
def test_cli_range_smoke(test_video_file, tmp_path):
    result = _run(
        [
            "-i",
            os.path.abspath(test_video_file),
            "-o",
            str(tmp_path),
            "time",
            "-e",
            "2s",
            "detect-content",
            "list-scenes",
        ],
        cwd=os.path.abspath(os.path.dirname(test_video_file) + "/../.."),
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"


@pytest.mark.release
def test_cli_stats_roundtrip(test_video_file, tmp_path):
    stats_path = tmp_path / "stats.csv"
    repo_cwd = os.path.abspath(os.path.dirname(test_video_file) + "/../..")

    # First run: generate stats.
    run1 = _run(
        [
            "-i",
            os.path.abspath(test_video_file),
            "-s",
            str(stats_path),
            "-o",
            str(tmp_path),
            "detect-content",
            "list-scenes",
            "-f",
            "run1",
        ],
        cwd=repo_cwd,
    )
    assert run1.returncode == 0, run1.stderr
    assert stats_path.exists()

    # Second run: reuse stats.
    run2 = _run(
        [
            "-i",
            os.path.abspath(test_video_file),
            "-s",
            str(stats_path),
            "-o",
            str(tmp_path),
            "detect-content",
            "list-scenes",
            "-f",
            "run2",
        ],
        cwd=repo_cwd,
    )
    assert run2.returncode == 0, run2.stderr

    def _cuts(csv_path):
        # First line is the cut-list summary; extract it for comparison.
        return csv_path.read_text().splitlines()[0]

    assert _cuts(tmp_path / "run1.csv") == _cuts(tmp_path / "run2.csv"), (
        "Cut list differs between stats-producing run and stats-consuming run."
    )


@pytest.mark.release
def test_cli_min_scene_len_smoke(test_video_file, tmp_path):
    # A min-scene-len longer than the video collapses everything to a single scene.
    result = _run(
        [
            "-i",
            os.path.abspath(test_video_file),
            "-o",
            str(tmp_path),
            "detect-content",
            "--min-scene-len",
            "1000s",
            "list-scenes",
        ],
        cwd=os.path.abspath(os.path.dirname(test_video_file) + "/../.."),
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"


@pytest.mark.release
def test_cli_save_fcp_smoke(test_video_file, tmp_path):
    """save-fcp writes a well-formed Final Cut Pro XML."""
    import xml.etree.ElementTree as ET

    result = _run(
        [
            "-i",
            os.path.abspath(test_video_file),
            "-o",
            str(tmp_path),
            "detect-content",
            "save-fcp",
        ],
        cwd=os.path.abspath(os.path.dirname(test_video_file) + "/../.."),
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    xml_files = [p for p in tmp_path.iterdir() if p.suffix == ".xml"]
    assert xml_files, "save-fcp produced no .xml file"
    # Parse must succeed; root <fcpxml> or <xmeml> depending on the FCP variant.
    root = ET.parse(xml_files[0]).getroot()
    assert root.tag in ("fcpxml", "xmeml"), f"Unexpected root element: {root.tag}"


@pytest.mark.release
def test_cli_save_qp_smoke(test_video_file, tmp_path):
    """save-qp writes a QP file with `<frame> I <shift>` lines for scene boundaries."""
    result = _run(
        [
            "-i",
            os.path.abspath(test_video_file),
            "-o",
            str(tmp_path),
            "detect-content",
            "save-qp",
        ],
        cwd=os.path.abspath(os.path.dirname(test_video_file) + "/../.."),
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    qp_files = [p for p in tmp_path.iterdir() if p.suffix == ".qp"]
    assert qp_files, "save-qp produced no .qp file"
    contents = qp_files[0].read_text().strip()
    assert contents, "save-qp produced an empty file"
    # Each line must be `<frame_number> I <shift>` where shift is an integer.
    for line in contents.splitlines():
        parts = line.split()
        assert len(parts) == 3 and parts[0].isdigit() and parts[1] == "I", (
            f"Malformed QP line: {line!r}"
        )
        int(parts[2])  # shift must parse as int (may be negative)


@pytest.mark.release
def test_cli_save_html_smoke(test_video_file, tmp_path):
    """save-html replaces the deprecated export-html and produces an HTML report.

    Note: save-html lacks its own --output option and ignores the global -o, so the
    file is routed via --filename with an absolute path.
    """
    out_html = tmp_path / "scenes.html"
    result = _run(
        [
            "-i",
            os.path.abspath(test_video_file),
            "detect-content",
            "save-html",
            "--filename",
            str(out_html),
            "--no-images",
        ],
        cwd=os.path.abspath(os.path.dirname(test_video_file) + "/../.."),
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    assert out_html.exists(), f"save-html produced no file at {out_html}"
    contents = out_html.read_text(encoding="utf-8")
    # The output is an HTML fragment (a <table> of scenes), not a full document.
    lowered = contents.lower()
    assert "<table" in lowered and "</table>" in lowered, (
        f"save-html output is missing the scenes <table>:\n{contents[:500]}"
    )


@pytest.mark.release
def test_cli_save_edl_start_timecode_smoke(test_video_file, tmp_path):
    """save-edl --start-timecode produces an EDL where event timestamps are offset by the
    requested start. Both SMPTE (HH:MM:SS:FF) and 8-digit (HHMMSSFF) inputs must be accepted."""
    repo_cwd = os.path.abspath(os.path.dirname(test_video_file) + "/../..")

    def _edl(form: str, out_dir):
        result = _run(
            [
                "-i",
                os.path.abspath(test_video_file),
                "-o",
                str(out_dir),
                "detect-content",
                "save-edl",
                "--start-timecode",
                form,
            ],
            cwd=repo_cwd,
        )
        assert result.returncode == 0, (
            f"start-timecode {form!r} failed:\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
        )
        edls = [p for p in out_dir.iterdir() if p.suffix == ".edl"]
        assert edls, f"save-edl --start-timecode {form!r} produced no .edl file"
        return edls[0].read_text()

    # SMPTE form.
    smpte_dir = tmp_path / "smpte"
    smpte_dir.mkdir()
    smpte_text = _edl("01:00:00:00", smpte_dir)
    # 8-digit form (semantically equivalent to 01:00:00:00).
    digit_dir = tmp_path / "digit"
    digit_dir.mkdir()
    digit_text = _edl("01000000", digit_dir)
    # Both EDLs must contain at least one event line with the 01:00:... offset visible.
    assert "01:00:" in smpte_text, f"SMPTE start TC not propagated to EDL:\n{smpte_text}"
    assert "01:00:" in digit_text, f"8-digit start TC not propagated to EDL:\n{digit_text}"
