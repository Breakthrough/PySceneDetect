# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2020 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" ``scenedetect.scene_detector`` Module

This module implements the base SceneDetector class, from which all scene
detectors in the scenedetect.dectectors module are derived from.

The SceneDetector class represents the interface which detection algorithms
are expected to provide in order to be compatible with PySceneDetect.
"""

# pylint: disable=unused-argument, no-self-use


class SceneDetector(object):
    """ Base class to inherit from when implementing a scene detection algorithm.

    This represents a "dense" scene detector, which returns a list of frames where
    the next scene/shot begins in a video.

    Also see the implemented scene detectors in the scenedetect.detectors module
    to get an idea of how a particular detector can be created.
    """

    stats_manager = None
    """ Optional :py:class:`StatsManager <scenedetect.stats_manager.StatsManager>` to
    use for caching frame metrics to and from."""

    _metric_keys = []
    """ List of frame metric keys to be registered with the :py:attr:`stats_manager`,
    if available. """

    cli_name = 'detect-none'
    """ Name of detector to use in command-line interface description. """

    def is_processing_required(self, frame_num):
        # type: (int) -> bool
        """ Is Processing Required: Test if all calculations for a given frame are already done.

        Returns:
            bool: False if the SceneDetector has assigned _metric_keys, and the
            stats_manager property is set to a valid StatsManager object containing
            the required frame metrics/calculations for the given frame - thus, not
            needing the frame to perform scene detection.

            True otherwise (i.e. the frame_img passed to process_frame is required
            to be passed to process_frame for the given frame_num).
        """
        return not self._metric_keys or not (
            self.stats_manager is not None and
            self.stats_manager.metrics_exist(frame_num, self._metric_keys))


    def get_metrics(self):
        # type: () -> List[str]
        """ Get Metrics:  Get a list of all metric names/keys used by the detector.

        Returns:
            List[str]: A list of strings of frame metric key names that will be used by
            the detector when a StatsManager is passed to process_frame.
        """
        return self._metric_keys


    def process_frame(self, frame_num, frame_img):
        # type: (int, numpy.ndarray) -> List[int]
        """ Process Frame: Computes/stores metrics and detects any scene changes.

        Prototype method, no actual detection.

        Returns:
            List[int]: List of frame numbers of cuts to be added to the cutting list.
        """
        return []


    def post_process(self, frame_num):
        # type: (int) -> List[int]
        """ Post Process: Performs any processing after the last frame has been read.

        Prototype method, no actual detection.

        Returns:
            List[int]: List of frame numbers of cuts to be added to the cutting list.
        """
        return []


class SparseSceneDetector(SceneDetector):
    """ Base class to inheret from when implementing a sparse scene detection algorithm.

    Unlike dense detectors, sparse detectors detect "events" and return a *pair* of frames,
    as opposed to just a single cut.

    An example of a SparseSceneDetector is the MotionDetector.
    """

    def process_frame(self, frame_num, frame_img):
        # type: (int, numpy.ndarray) -> List[Tuple[int, int]]
        """ Process Frame: Computes/stores metrics and detects any scene changes.

        Prototype method, no actual detection.

        Returns:
            List[Tuple[int,int]]: List of frame pairs representing individual scenes
            to be added to the output scene list directly.
        """
        return []


    def post_process(self, frame_num):
        # type: (int) -> List[Tuple[int, int]]
        """ Post Process: Performs any processing after the last frame has been read.

        Prototype method, no actual detection.

        Returns:
            List[Tuple[int,int]]: List of frame pairs representing individual scenes
            to be added to the output scene list directly.
        """
        return []
