#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://www.scenedetect.com/docs/         ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
#
# Runtime hook: redirect imageio_ffmpeg and moviepy to the bundled ffmpeg.exe (staged next to
# scenedetect.exe) so we ship a single copy of ffmpeg. Runs before any user imports, which is
# required because moviepy.config reads FFMPEG_BINARY at import time.


def _pyi_rthook():
    import os
    import sys

    bundle_dir = os.path.dirname(sys.executable)
    ffmpeg_exe = os.path.join(bundle_dir, "ffmpeg.exe")
    if os.path.isfile(ffmpeg_exe):
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe
        os.environ.setdefault("FFMPEG_BINARY", ffmpeg_exe)
        os.environ["PATH"] = bundle_dir + os.pathsep + os.environ.get("PATH", "")


_pyi_rthook()
del _pyi_rthook
