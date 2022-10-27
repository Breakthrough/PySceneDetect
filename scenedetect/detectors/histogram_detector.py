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
""":py:class:`HistogramDetector` compares the difference in the RGB histograms of subsequent
frames. If the difference exceeds a given threshold, a cut is detected.

This detector is available from the command-line as the `detect-hist` command.
"""

from typing import List

import numpy

# PySceneDetect Library Imports
from scenedetect.scene_detector import SceneDetector


class HistogramDetector(SceneDetector):
    """Compares the difference in the RGB histograms of subsequent
    frames. If the difference exceeds a given threshold, a cut is detected."""

    METRIC_KEYS = ['hist_diff']

    def __init__(self, threshold: float = 20000.0, bits: int = 4, min_scene_len: int = 15):
        """
        Arguments:
            threshold: Threshold value (float) that the calculated difference between subsequent
                histograms must exceed to trigger a new scene.
            bits: Number of most significant bits to keep of the pixel values. Most videos and
                images are 8-bit rgb (0-255) and the default is to just keep the 4 most siginificant
                bits. This compresses the 3*8bit (24bit) image down to 3*4bits (12bits). This makes
                quantizing the rgb histogram a bit easier and comparisons more meaningful.
            min_scene_len:  Minimum length of any scene.
        """
        super().__init__()
        self.threshold = threshold
        self.bits = bits
        self.min_scene_len = min_scene_len
        self._hist_bins = range(2**(3 * self.bits))
        self._last_hist = None
        self._last_scene_cut = None

    def process_frame(self, frame_num: int, frame_img: numpy.ndarray) -> List[int]:
        """First, compress the image according to the self.bits value, then build a histogram for
        the input frame. Afterward, compare against the previously analyzed frame and check if the
        difference is large enough to trigger a cut.

        Arguments:
            frame_num: Frame number of frame that is being passed.
            frame_img: Decoded frame image (numpy.ndarray) to perform scene
                detection on.

        Returns:
            List of frames where scene cuts have been detected. There may be 0
            or more frames in the list, and not necessarily the same as frame_num.
        """
        cut_list = []

        np_data_type = frame_img.dtype

        if np_data_type != numpy.uint8:
            raise ValueError('Image must be 8-bit rgb for HistogramDetector')

        # Initialize last scene cut point at the beginning of the frames of interest.
        if not self._last_scene_cut:
            self._last_scene_cut = frame_num

        # Quantize the image and separate the color channels
        quantized_imgs = self._quantize_frame(frame_img=frame_img, bits=self.bits)

        # Perform bit shifting operations and bitwise combine color channels into one array
        composite_img = self._shift_bits(quantized_imgs=quantized_imgs, bits=self.bits)

        # Create the histogram with a bin for every rgb value
        hist, _ = numpy.histogram(composite_img, bins=self._hist_bins)

        # We can only start detecting once we have a frame to compare with.
        if self._last_hist is not None:
            # Compute histogram difference between frames
            hist_diff = numpy.sum(numpy.fabs(self._last_hist - hist))

            # Check if a new scene should be triggered
            if hist_diff >= self.threshold and (
                (frame_num - self._last_scene_cut) >= self.min_scene_len):
                cut_list.append(frame_num)
                self._last_scene_cut = frame_num

            # Save stats to a StatsManager if it is being used
            if self.stats_manager is not None:
                self.stats_manager.set_metrics(frame_num, {self.METRIC_KEYS[0]: hist_diff})

        self._last_hist = hist

        return cut_list

    def _quantize_frame(self, frame_img, bits):
        """Quantizes the image based on the number of most significant figures to be preserved.

        Arguments:
            frame_img: The 8-bit rgb image of the frame being analyzed.
            bits: The number of most significant bits to keep during quantization.

        Returns:
            [red_img, green_img, blue_img]:
                The three separated color channels of the frame image that have been quantized.
        """
        # First, find the value of the number of most significant bits, padding with zeroes
        bit_value = int(bin(2**bits - 1).ljust(10, '0'), 2)

        # Separate R, G, and B color channels and cast to int for easier bitwise operations
        red_img = frame_img[:, :, 0].astype(int)
        green_img = frame_img[:, :, 1].astype(int)
        blue_img = frame_img[:, :, 2].astype(int)

        # Quantize the frame images
        red_img = red_img & bit_value
        green_img = green_img & bit_value
        blue_img = blue_img & bit_value

        return [red_img, green_img, blue_img]

    def _shift_bits(self, quantized_imgs, bits):
        """Takes care of the bit shifting operations to combine the RGB color
        channels into a single array.

        Arguments:
            quantized_imgs: A list of the three quantized images of the RGB color channels
                respectively.
            bits: The number of most significant bits to use for quantizing the image.

        Returns:
            composite_img: The resulting array after all bitwise operations.
        """
        # First, figure out how much each shift needs to be
        blue_shift = 8 - bits
        green_shift = 8 - 2 * bits
        red_shift = 8 - 3 * bits

        # Separate our color channels for ease
        red_img = quantized_imgs[0]
        green_img = quantized_imgs[1]
        blue_img = quantized_imgs[2]

        # Perform the bit shifting for each color
        red_img = self._shift_images(img=red_img, img_shift=red_shift)
        green_img = self._shift_images(img=green_img, img_shift=green_shift)
        blue_img = self._shift_images(img=blue_img, img_shift=blue_shift)

        # Join our rgb arrays together
        composite_img = numpy.bitwise_or(red_img, numpy.bitwise_or(green_img, blue_img))

        return composite_img

    def _shift_images(self, img, img_shift):
        """Do bitwise shifting operations for a color channel image checking for shift direction.

        Arguments:
            img: A quantized image of a single color channel
            img_shift: How many bits to shift the values of img. If the value is negative, the shift
                direction is to the left and 8 is added to make it a positive value.

        Returns:
            shifted_img: The bitwise shifted image.
        """
        if img_shift < 0:
            img_shift += 8
            shifted_img = numpy.left_shift(img, img_shift)
        else:
            shifted_img = numpy.right_shift(img, img_shift)

        return shifted_img

    def is_processing_required(self, frame_num: int) -> bool:
        return True

    def get_metrics(self) -> List[str]:
        return HistogramDetector.METRIC_KEYS
