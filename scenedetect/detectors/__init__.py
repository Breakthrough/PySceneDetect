# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
""" ``scenedetect.detectors`` Module

This module contains the following scene detection algorithms:

 * :py:class:`ContentDetector <scenedetect.detectors.content_detector.ContentDetector>`:
    Detects shot changes by considering pixel changes in the HSV colorspace.

 * :py:class:`ThresholdDetector <scenedetect.detectors.threshold_detector.ThresholdDetector>`:
    Detects transitions below a set pixel intensity (cuts or fades to black).

 * :py:class:`AdaptiveDetector <scenedetect.detectors.adaptive_detector.AdaptiveDetector>`:
    Two-pass version of `ContentDetector` that handles fast camera movement better in some cases.

Detection algorithms are created by implementing the
:py:class:`SceneDetector <scenedetect.scene_detector.SceneDetector>` interface. Detectors are
typically attached to a :py:class:`SceneManager <scenedetect.scene_manager.SceneManager>` when
processing videos, however they can also be used to process frames directly.
"""

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                             #
#          Detection Methods & Algorithms Planned or In Development           #
#                                                                             #
#
# class EdgeDetector(SceneDetector):
#    """Detects fast cuts/slow fades by using edge detection on adjacent frames.
#
#    Computes the difference image between subsequent frames after applying a
#    Sobel filter (can also use a high-pass or other edge detection filters) and
#    comparing the result with a set threshold (may be found using -stats mode).
#    Detects both fast cuts and slow fades, although some parameters may need to
#    be modified for accurate slow fade detection.
#    """
#    def __init__(self):
#        super(EdgeDetector, self).__init__()
#                                                                             #
#                                                                             #
# class DissolveDetector(SceneDetector):
#    """Detects slow fades (dissolve cuts) via changes in the HSV colour space.
#
#    Detects slow fades only; to detect fast cuts between content scenes, the
#    ContentDetector should be used instead.
#    """
#
#    def __init__(self):
#        super(DissolveDetector, self).__init__()
#                                                                             #
#                                                                             #
# class HistogramDetector(SceneDetector):
#    """Detects fast cuts via histogram changes between sequential frames.
#
#    Detects fast cuts between content (using histogram deltas, much like the
#    ContentDetector uses HSV colourspace deltas), as well as both fades and
#    cuts to/from black (using a threshold, much like the ThresholdDetector).
#    """
#
#    def __init__(self):
#        super(DissolveDetector, self).__init__()
#                                                                             #
#                                                                             #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# PySceneDetect Detection Algorithm Imports
from scenedetect.detectors.content_detector import ContentDetector
from scenedetect.detectors.threshold_detector import ThresholdDetector
from scenedetect.detectors.adaptive_detector import AdaptiveDetector

# Algorithms being ported:
#from scenedetect.detectors.motion_detector import MotionDetector
