# -*- coding: utf-8 -*-
#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""``scenedetect.detectors`` Module

This module contains the following scene detection algorithms:

 * :mod:`ContentDetector <scenedetect.detectors.content_detector>`:
    Detects shot changes by considering pixel changes in the HSV colorspace.

 * :mod:`ThresholdDetector <scenedetect.detectors.threshold_detector>`:
    Detects transitions below a set pixel intensity (cuts or fades to black).

 * :mod:`AdaptiveDetector <scenedetect.detectors.adaptive_detector>`:
    Two-pass version of `ContentDetector` that handles fast camera movement better in some cases.

Detection algorithms are created by implementing the
:class:`SceneDetector <scenedetect.scene_detector.SceneDetector>` interface. Detectors are
typically attached to a :class:`SceneManager <scenedetect.scene_manager.SceneManager>` when
processing videos, however they can also be used to process frames directly.
"""

from scenedetect.detectors.content_detector import ContentDetector
from scenedetect.detectors.threshold_detector import ThresholdDetector
from scenedetect.detectors.adaptive_detector import AdaptiveDetector
from scenedetect.detectors.hash_detector import HashDetector
from scenedetect.detectors.histogram_detector import HistogramDetector

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                             #
#          Detection Methods & Algorithms Planned or In Development           #
#                                                                             #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# class DissolveDetector(SceneDetector):
#    """Detects slow fades (dissolve cuts) via changes in the HSV colour space.
#
#    Detects slow fades only; to detect fast cuts between content scenes, the
#    ContentDetector should be used instead.
#    """
#
#    def __init__(self):
#        super(DissolveDetector, self).__init__()
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# class MotionDetector(SceneDetector):
#    """Detects motion events in scenes containing a static background.
#
#    Uses background subtraction followed by noise removal (via morphological
#    opening) to generate a frame score compared against the set threshold.
#    """
#
#    def __init__(self):
#        super(MotionDetector, self).__init__()
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
