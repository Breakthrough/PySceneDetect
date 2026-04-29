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
"""Synthetic Video Generation

Functions to generate synthetic video files using ffmpeg for testing purposes.
"""

import subprocess


def generate_vfr_swing(output_path: str):
    """Generates a VFR video with three segments separated by visible luma steps.

    Segments: black @ 1 fps (5s) -> gray @ 60 fps (5s) -> white @ 1 fps (5s).
    Solid colors make the cuts unambiguous for ContentDetector; mixed rates
    exercise the VFR code path. Boundary timestamps: 5.0s and 10.0s.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=black:size=320x240:duration=5:rate=1",
        "-f",
        "lavfi",
        "-i",
        "color=gray:size=320x240:duration=5:rate=60",
        "-f",
        "lavfi",
        "-i",
        "color=white:size=320x240:duration=5:rate=1",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0",
        "-vsync",
        "vfr",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def generate_vfr_pts_gap(output_path: str):
    """Generates a video where setpts filter drops 3 frames mid-clip."""
    # ffmpeg -f lavfi -i "testsrc2=duration=5:rate=30" -vf "select='not(between(n,30,32))',setpts=N/FRAME_RATE/TB" output.mp4
    # Actually to make it VFR with a gap:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=duration=5:rate=30",
        "-vf",
        "select='not(between(n,30,32))'",
        "-vsync",
        "vfr",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def generate_vfr_bframes(output_path: str):
    """Generates H.264 video with B-frames to exercise DTS/PTS divergence."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=duration=5:rate=30",
        "-c:v",
        "libx264",
        "-bf",
        "4",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def generate_synthetic_matrix_video(
    output_path: str, codec: str, container: str, extra_args: list | None = None
):
    """Generates a video with specific codec and container."""
    input_args = ["-f", "lavfi", "-i", "testsrc2=duration=2:rate=30"]
    codec_args = ["-c:v", codec] if codec else []
    if extra_args:
        codec_args.extend(extra_args)

    cmd = ["ffmpeg", "-y", *input_args, *codec_args, output_path]
    subprocess.run(cmd, check=True, capture_output=True)
