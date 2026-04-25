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
"""Category 5: Synthetic Codec / Container / Geometry Matrix

Verifies that PySceneDetect can handle various codecs, containers, and video properties.
"""

import subprocess

import pytest

from scenedetect import ContentDetector, SceneManager, open_video

MATRIX = [
    ("libx264", "mp4", []),
    ("libx265", "mkv", []),
    ("libvpx-vp9", "webm", []),
    ("libx264", "mp4", ["-vf", "transpose=1"]),  # Rotation
    ("libx264", "mp4", ["-pix_fmt", "yuv400p"]),  # Grayscale
]


@pytest.mark.release
@pytest.mark.parametrize("codec, container, extra_args", MATRIX)
@pytest.mark.parametrize("backend", ["opencv", "pyav"])
def test_synthetic_matrix(synthetic_matrix_generator, codec, container, extra_args, backend):
    try:
        video_path = synthetic_matrix_generator(codec, container, extra_args)
    except subprocess.CalledProcessError:
        pytest.skip(f"Codec {codec} or container {container} not supported by ffmpeg.")

    video = open_video(video_path, backend=backend)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    scene_manager.detect_scenes(video)

    # Ensure it processed some frames
    assert video.frame_number > 0
    # Plausible duration
    assert video.duration is not None
    assert abs(video.duration.seconds - 2.0) < 0.2
