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

""" ``scenedetect.detectors.hash_detector`` Module

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
    """Detects cuts using a perceptual hashing algorithm. For more information
    on the perceptual hashing algorithm see references below.

    1. https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    2. https://github.com/JohannesBuchner/imagehash

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.
    """

    def __init__(self, threshold=100.0, min_scene_len=15, hash_size=16, highfreq_factor=2):
        super(HashDetector, self).__init__()
        self.threshold = threshold
        # Minimum length of any given scene, in frames (int) or FrameTimecode
        self.min_scene_len = min_scene_len
        # Size of square of low frequency data to include from the discrete cosine transform
        self.hash_size = hash_size
        # How much high frequency data should be thrown out from the DCT
        # A value of 2 means only keep 1/2 of the freq data, a value of 4 means only keep 1/4
        self.highfreq_factor = highfreq_factor
        self.last_frame = None
        self.last_scene_cut = None
        self.last_hash = numpy.array([])
        self._metric_keys = ['hash_dist']
        self.cli_name = 'detect-hash'
    
    def get_metrics(self):
        return self._metric_keys
    
    def process_frame(self, frame_num, frame_img):
        """ Similar to ContentDetector, but using a perceptual hashing algorithm
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
        metric_keys = self._metric_keys
        _unused = ''

        # Initialize last scene cut point at the beginning of the frames of interest.
        if self.last_scene_cut is None:
            self.last_scene_cut = frame_num
        
        # We can only start detecting once we have a frame to compare with.
        if self.last_frame is not None:
            # We obtain the change in hash value between subsequent frames as 
            # well as the actual hash value. This is refered to in a statsfile
            # as their respective metric keys.
            if (self.stats_manager is not None and
                    self.stats_manager.metrics_exist(frame_num, metric_keys)):
                hash_dist = self.stats_manager.get_metrics(frame_num, metric_keys)
            else:
                # Perceptual hashing algorithm based on phash, updated to use OpenCV instead of PIL + scipy
                # https://github.com/JohannesBuchner/imagehash
                
                # Convert to grayscale
                curr_gray = cv2.cvtColor(frame_img, cv2.COLOR_BGR2GRAY)
                # Resize image to square to help with DCT
                imsize = self.hash_size * self.highfreq_factor
                curr_resized = cv2.resize(curr_gray, (imsize, imsize), interpolation=cv2.INTER_AREA)
                # Calculate discrete cosine tranformation of the image
                curr_resized = numpy.float32(curr_resized) / numpy.max(numpy.max(curr_resized))
                curr_dct = cv2.dct(curr_resized)
                # Only keep the low frequency information
                curr_dct_low_freq = curr_dct[:self.hash_size, :self.hash_size]
                # Calculate the median of the low frequency information
                curr_med = numpy.median(curr_dct_low_freq)
                # Transform the low frequency information into a binary image based on > or < median
                curr_hash = curr_dct_low_freq > curr_med
                
                last_hash = self.last_hash
                
                if last_hash.size == 0:
                    # Calculate hash as above
                    last_gray = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2GRAY)
                    last_resized = cv2.resize(last_gray, (imsize, imsize), interpolation=cv2.INTER_AREA)
                    last_resized = numpy.float32(last_resized) / numpy.max(numpy.max(last_resized))
                    last_dct = cv2.dct(last_resized)
                    last_dct_low_freq = last_dct[:self.hash_size, :self.hash_size]
                    last_med = numpy.median(last_dct_low_freq)
                    last_hash = last_dct_low_freq > last_med
                
                # Hamming distance is calculated to compare to last frame
                hash_dist = numpy.count_nonzero(curr_hash.flatten() != last_hash.flatten())

                if self.stats_manager is not None:
                    self.stats_manager.set_metrics(frame_num, {
                        metric_keys[0]: hash_dist})
                
                self.last_hash = curr_hash
                

            # We consider any frame over the threshold a new scene, but only if
            # the minimum scene length has been reached (otherwise it is ignored).
            if hash_dist >= self.threshold and (
                    (frame_num - self.last_scene_cut) >= self.min_scene_len):
                cut_list.append(frame_num)
                self.last_scene_cut = frame_num

            if self.last_frame is not None and self.last_frame is not _unused:
                del self.last_frame
            
        # If we have the next frame computed, don't copy the current frame
        # into last_frame since we won't use it on the next call anyways.
        if (self.stats_manager is not None and
                self.stats_manager.metrics_exist(frame_num+1, metric_keys)):
            self.last_frame = _unused
        else:
            self.last_frame = frame_img.copy()

        return cut_list