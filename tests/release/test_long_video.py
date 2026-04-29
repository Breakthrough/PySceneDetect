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
"""Long-Video Stress Test

Verifies no memory leaks or file descriptors during processing of long videos.
"""

import os
import sys
import threading
import time

import pytest

from scenedetect import ContentDetector, SceneManager, open_video

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@pytest.mark.release
@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Long stress test runs on Linux only (num_fds/handles semantics differ elsewhere).",
)
def test_long_video_stress(long_video):
    if not HAS_PSUTIL:
        pytest.skip("psutil not installed.")

    process = psutil.Process(os.getpid())
    baseline_rss = process.memory_info().rss
    peak_rss = [baseline_rss]
    stop_event = threading.Event()

    def monitor_memory():
        while not stop_event.is_set():
            try:
                current_rss = process.memory_info().rss
                if current_rss > peak_rss[0]:
                    peak_rss[0] = current_rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(1)

    monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
    monitor_thread.start()

    try:
        video = open_video(long_video)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector())
        scene_manager.detect_scenes(video)

        # Ensure it actually did something
        assert video.frame_number > 0
    finally:
        stop_event.set()
        monitor_thread.join()

    # Assert peak RSS <= 3x baseline
    # Some increase is expected due to internal buffering, but not 3x for 480p.
    assert peak_rss[0] <= 3 * baseline_rss, (
        f"Memory leak suspected: Peak RSS {peak_rss[0]} > 3x Baseline RSS {baseline_rss}"
    )

    # Check open file descriptors (only works on some platforms easily)
    # On Windows it's num_handles
    if sys.platform == "win32":
        assert process.num_handles() <= 100  # Conservative baseline
    else:
        assert process.num_fds() <= 50
