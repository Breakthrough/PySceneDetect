#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains all of the detection methods/algorithms that can be used
# in PySceneDetect.  This includes a base object (SceneDetector) upon which all
# other detection method objects are based, which can be used as templates for
# implementing custom/application-specific scene detection methods.
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy, OpenCV, and click; see the included LICENSE-
# files for copyright information, or visit one of the above URLs.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

# Third-Party Library Imports
import cv2
import numpy


# Default value for -d / --detector CLI argument (see get_available_detectors()
# for a list of valid/enabled detection methods and their string equivalents).
DETECTOR_DEFAULT = 'threshold'


def get_available():
    """Returns a dictionary of the available/enabled scene detectors.

    Returns:
        A dictionary with the form {name (string): detector (SceneDetector)},
        where name is the common name used via the command-line, and detector
        is a reference to the object instantiator.
    """
    detector_dict = {
        'threshold': ThresholdDetector,
        'content': ContentDetector
    }
    return detector_dict


class SceneDetector(object):
    """Base SceneDetector class to implement a scene detection algorithm."""
    def __init__(self):
        self.stats_manager = None
        self._metric_keys = []

    def get_metrics(self):
        # type: () -> List[str]
        """ Get Metrics:  Get a list of all metric names/keys used by the detector.
        
        Returns:
            A List[str] of the frame metric key names that will be used by
            the detector when a StatsManager is passed to process_frame.
        """
        return self._metric_keys

    def process_frame(self, frame_num, frame_img):
        # type: (int, numpy.ndarray) -> Tuple[bool, Union[None, int]]
        """ Process Frame: Computes/stores metrics and detects any scene changes.

        Prototype method, no actual detection.

        Returns:
            Tuple of (cut_detected: bool, frame_num: int/None), where if cut_detected
            is True, frame_num is the integer frame number of the cut to add, else None. 
        """
        return (False, 0)

    def post_process(self, frame_num):
        # type: (int) -> List[int]
        """ Post Process: Performs any processing after the last frame has been read.

        Prototype method, no actual detection.

        Returns:
            List of frame numbers of additional cuts to be added.
        """
        return []

