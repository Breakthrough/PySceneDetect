#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""DEPRECATED"""

import warnings

warnings.warn(
    "The `frame_timecode` submodule is deprecated, import from the base package instead.",
    DeprecationWarning,
    stacklevel=2,
)

from scenedetect.common import *  # noqa: E402, F403
