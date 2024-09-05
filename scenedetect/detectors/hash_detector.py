# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
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
"""``scenedetect.detectors.hash_detector`` Module

This module implements the :py:class:`HashDetector`, which calculates a hash
value for each from of a video using a perceptual hashing algorithm. Then, the
differences in hash value between frames is calculated. If this difference
exceeds a set threshold, a scene cut is triggered.

This detector is available from the command-line interface by using the
`detect-hash` command.
"""

# Third-Party Library Imports
import numpy
import cv2

# PySceneDetect Library Imports
from scenedetect.scene_detector import SceneDetector


class HashDetector(SceneDetector):
    """Detects cuts using a perceptual hashing algorithm. Applies a direct cosine transform (DCT)
    and lowpass filter, followed by binary thresholding on the median. See references below:

    1. https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    2. https://github.com/JohannesBuchner/imagehash

    Arguments:
        threshold: Value from 0.0 and 1.0 representing the relative hamming distance between
            the perceptual hashes of adjacent frames. A distance of 0 means the image is the same,
            and 1 means no correlation. Smaller threshold values thus require more correlation,
            making the detector more sensitive. The hamming distance is divided by `size` x `size`
            before comparing to `threshold` for normalization.
        size: Size of square of low frequency data to use for the DCT
        lowpass:  How much high frequency information to filter from the DCT. A value of 2 means
            keep lower 1/2 of the frequency data, 4 means only keep 1/4, etc...
        min_scene_len: Minimum length of any given scene, in frames (int) or FrameTimecode
    """

    def __init__(
        self,
        threshold: float = 0.395,
        size: int = 16,
        lowpass: int = 2,
        min_scene_len: int = 15,
    ):
        super(HashDetector, self).__init__()
        self._threshold = threshold
        self._min_scene_len = min_scene_len
        self._size = size
        self._size_sq = float(size * size)
        self._factor = lowpass
        self._last_frame = None
        self._last_scene_cut = None
        self._last_hash = numpy.array([])
        self._metric_key = f"hash_dist [size={self._size} lowpass={self._factor}]"

    def get_metrics(self):
        return [self._metric_key]

    def is_processing_required(self, frame_num):
        return True

    def process_frame(self, frame_num, frame_img):
        """Similar to ContentDetector, but using a perceptual hashing algorithm
        to calculate a hash for each frame and then calculate a hash difference
        frame to frame.

        Arguments:
            frame_num (int): Frame number of frame that is being passed.

            frame_img (Optional[int]): Decoded frame image (numpy.ndarray) to perform scene
                detection on. Can be None *only* if the self.is_processing_required() method
                (inhereted from the base SceneDetector class) returns True.

        Returns:
            List[int]: List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.
        """

        cut_list = []

        # Initialize last scene cut point at the beginning of the frames of interest.
        if self._last_scene_cut is None:
            self._last_scene_cut = frame_num

        # We can only start detecting once we have a frame to compare with.
        if self._last_frame is not None:
            # We obtain the change in hash value between subsequent frames.
            curr_hash = self.hash_frame(
                frame_img=frame_img, hash_size=self._size, factor=self._factor
            )

            last_hash = self._last_hash

            if last_hash.size == 0:
                # Calculate hash of last frame
                last_hash = self.hash_frame(
                    frame_img=self._last_frame,
                    hash_size=self._size,
                    factor=self._factor,
                )

            # Hamming distance is calculated to compare to last frame
            hash_dist = numpy.count_nonzero(curr_hash.flatten() != last_hash.flatten())

            # Normalize based on size of the hash
            hash_dist_norm = hash_dist / self._size_sq

            if self.stats_manager is not None:
                self.stats_manager.set_metrics(
                    frame_num, {self._metric_key: hash_dist_norm}
                )

            self._last_hash = curr_hash

            # We consider any frame over the threshold a new scene, but only if
            # the minimum scene length has been reached (otherwise it is ignored).
            if hash_dist_norm >= self._threshold and (
                (frame_num - self._last_scene_cut) >= self._min_scene_len
            ):
                cut_list.append(frame_num)
                self._last_scene_cut = frame_num

        self._last_frame = frame_img.copy()

        return cut_list

    @staticmethod
    def hash_frame(frame_img, hash_size, factor) -> numpy.ndarray:
        """Calculates the perceptual hash of a frame and returns it. Based on phash from
        https://github.com/JohannesBuchner/imagehash.
        """

        # Transform to grayscale
        gray_img = cv2.cvtColor(frame_img, cv2.COLOR_BGR2GRAY)

        # Resize image to square to help with DCT
        imsize = hash_size * factor
        resized_img = cv2.resize(
            gray_img, (imsize, imsize), interpolation=cv2.INTER_AREA
        )

        # Check to avoid dividing by zero
        max_value = numpy.max(numpy.max(resized_img))
        if max_value == 0:
            # Just set the max to 1 to not change the values
            max_value = 1

        # Calculate discrete cosine tranformation of the image
        resized_img = numpy.float32(resized_img) / max_value
        dct_complete = cv2.dct(resized_img)

        # Only keep the low frequency information
        dct_low_freq = dct_complete[:hash_size, :hash_size]

        # Calculate the median of the low frequency informations
        med = numpy.median(dct_low_freq)

        # Transform the low frequency information into a binary image based on > or < median
        hash_img = dct_low_freq > med

        return hash_img
