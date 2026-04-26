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
