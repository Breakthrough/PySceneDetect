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
"""Diagnostic for the av 17.1.0 VFR EOF regression: compares decoded frame count,
final PTS, and detected scene list between the PyAV and OpenCV backends on
`goldeneye-vfr.mp4`. See https://github.com/Breakthrough/PySceneDetect/actions/runs/27387628846."""

import av
import cv2

from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector

VIDEO = "tests/resources/goldeneye-vfr.mp4"

print(f"av version: {av.__version__}")
print(f"cv2 version: {cv2.__version__}")

for backend in ("pyav", "opencv"):
    video = open_video(VIDEO, backend=backend)
    frames = 0
    while video.read(decode=False) is not False:
        frames += 1
    final_pos = video.position
    print(
        f"[{backend}] frames={frames} final_pos={final_pos.get_timecode()} "
        f"({final_pos.seconds:.6f}s)"
    )

    video = open_video(VIDEO, backend=backend)
    sm = SceneManager()
    sm.add_detector(ContentDetector())
    sm.detect_scenes(video=video, show_progress=False)
    scenes = sm.get_scene_list()
    print(f"[{backend}] scenes={len(scenes)}")
    for i, (s, e) in enumerate(scenes):
        print(f"  {i + 1:3d}: {s.get_timecode()} -> {e.get_timecode()}")
