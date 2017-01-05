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
# Copyright (C) 2012-2017 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy and OpenCV; see the LICENSE-NUMPY and
# LICENSE-OPENCV files or visit one of above URLs for details.
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
        pass

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        """Computes/stores metrics and detects any scene changes.

        Prototype method, no actual detection.
        """
        return

    def post_process(self, scene_list):
        pass


class ThresholdDetector(SceneDetector):
    """Detects fast cuts/slow fades in from and out to a given threshold level.

    Detects both fast cuts and slow fades so long as an appropriate threshold
    is chosen (especially taking into account the minimum grey/black level).

    Attributes:
        threshold:  8-bit intensity value that each pixel value (R, G, and B)
            must be <= to in order to trigger a fade in/out.
        min_percent:  Float between 0.0 and 1.0 which represents the minimum
            percent of pixels in a frame that must meet the threshold value in
            order to trigger a fade in/out.
        min_scene_len:  Unsigned integer greater than 0 representing the
            minimum length, in frames, of a scene (or subsequent scene cut).
        fade_bias:  Float between -1.0 and +1.0 representing the percentage of
            timecode skew for the start of a scene (-1.0 causing a cut at the
            fade-to-black, 0.0 in the middle, and +1.0 causing the cut to be
            right at the position where the threshold is passed).
        add_final_scene:  Boolean indicating if the video ends on a fade-out to
            generate an additional scene at this timecode.
        block_size:  Number of rows in the image to sum per iteration (can be
            tuned to increase performance in some cases; should be computed
            programmatically in the future).
    """
    def __init__(self, threshold = 12, min_percent = 0.95, min_scene_len = 15,
                 fade_bias = 0.0, add_final_scene = False, block_size = 8):
        """Initializes threshold-based scene detector object."""
        super(ThresholdDetector, self).__init__()
        self.threshold = int(threshold)
        self.fade_bias = fade_bias
        self.min_percent = min_percent
        self.min_scene_len = min_scene_len
        self.last_frame_avg = None
        self.last_scene_cut = None
        # Whether to add an additional scene or not when ending on a fade out
        # (as cuts are only added on fade ins; see post_process() for details).
        self.add_final_scene = add_final_scene
        # Where the last fade (threshold crossing) was detected.
        self.last_fade = { 
            'frame': 0,         # frame number where the last detected fade is
            'type': None        # type of fade, can be either 'in' or 'out'
          }
        self.block_size = block_size
        return

    def compute_frame_average(self, frame):
        """Computes the average pixel value/intensity over the whole frame.

        The value is computed by adding up the 8-bit R, G, and B values for
        each pixel, and dividing by the number of pixels multiplied by 3.

        Returns:
            Floating point value representing average pixel intensity.
        """
        num_pixel_values = float(
            frame.shape[0] * frame.shape[1] * frame.shape[2])
        avg_pixel_value = numpy.sum(frame[:,:,:]) / num_pixel_values
        return avg_pixel_value

    def frame_under_threshold(self, frame):
        """Check if the frame is below (true) or above (false) the threshold.

        Instead of using the average, we check all pixel values (R, G, and B)
        meet the given threshold (within the minimum percent).  This ensures
        that the threshold is not exceeded while maintaining some tolerance for
        compression and noise.

        This is the algorithm used for absolute mode of the threshold detector.

        Returns:
            Boolean, True if the number of pixels whose R, G, and B values are
            all <= the threshold is within min_percent pixels, or False if not.
        """
        # First we compute the minimum number of pixels that need to meet the
        # threshold. Internally, we check for values greater than the threshold
        # as it's more likely that a given frame contains actual content. This
        # is done in blocks of rows, so in many cases we only have to check a
        # small portion of the frame instead of inspecting every single pixel.
        num_pixel_values = float(frame.shape[0] * frame.shape[1] * frame.shape[2])
        min_pixels = int(num_pixel_values * (1.0 - self.min_percent))

        curr_frame_amt = 0
        curr_frame_row = 0

        while curr_frame_row < frame.shape[0]:
            # Add and total the number of individual pixel values (R, G, and B)
            # in the current row block that exceed the threshold. 
            curr_frame_amt += int(
                numpy.sum(frame[curr_frame_row : 
                    curr_frame_row + self.block_size,:,:] > self.threshold))
            # If we've already exceeded the most pixels allowed to be above the
            # threshold, we can skip processing the rest of the pixels. 
            if curr_frame_amt > min_pixels:
                return False
            curr_frame_row += self.block_size
        return True

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        # Compare the # of pixels under threshold in current_frame & last_frame.
        # If absolute value of pixel intensity delta is above the threshold,
        # then we trigger a new scene cut/break.

        # Value to return indiciating if a scene cut was found or not.
        cut_detected = False

        # The metric used here to detect scene breaks is the percent of pixels
        # less than or equal to the threshold; however, since this differs on
        # user-supplied values, we supply the average pixel intensity as this
        # frame metric instead (to assist with manually selecting a threshold).
        frame_amt = 0.0
        frame_avg = 0.0
        if frame_num in frame_metrics and 'frame_avg_rgb' in frame_metrics[frame_num]:
            frame_avg = frame_metrics[frame_num]['frame_avg_rgb']
        else:
            frame_avg = self.compute_frame_average(frame_img)
            frame_metrics[frame_num]['frame_avg_rgb'] = frame_avg

        if self.last_frame_avg is not None:
            if self.last_fade['type'] == 'in' and self.frame_under_threshold(frame_img):
                # Just faded out of a scene, wait for next fade in.
                self.last_fade['type'] = 'out'
                self.last_fade['frame'] = frame_num
            elif self.last_fade['type'] == 'out' and not self.frame_under_threshold(frame_img):
                # Just faded into a new scene, compute timecode for the scene
                # split based on the fade bias.
                f_in = frame_num
                f_out = self.last_fade['frame']
                f_split = int((f_in + f_out + int(self.fade_bias * (f_in - f_out))) / 2)
                # Only add the scene if min_scene_len frames have passed. 
                if self.last_scene_cut is None or (
                    (frame_num - self.last_scene_cut) >= self.min_scene_len):
                    scene_list.append(f_split)
                    cut_detected = True
                    self.last_scene_cut = frame_num
                self.last_fade['type'] = 'in'
                self.last_fade['frame'] = frame_num
        else:
            self.last_fade['frame'] = 0
            if self.frame_under_threshold(frame_img):
                self.last_fade['type'] = 'out'
            else:
                self.last_fade['type'] = 'in'
        # Before returning, we keep track of the last frame average (can also
        # be used to compute fades independently of the last fade type).
        self.last_frame_avg = frame_avg
        return cut_detected

    def post_process(self, scene_list):
        """Writes a final scene cut if the last detected fade was a fade-out.

        Only writes the scene cut if add_final_scene is true, and the last fade
        that was detected was a fade-out.  There is no bias applied to this cut
        (since there is no corresponding fade-in) so it will be located at the
        exact frame where the fade-out crossed the detection threshold.
        """

        # If the last fade detected was a fade out, we add a corresponding new
        # scene break to indicate the end of the scene.  This is only done for
        # fade-outs, as a scene cut is already added when a fade-in is found.
        cut_detected = False
        if self.last_fade['type'] == 'out' and self.add_final_scene and (
            self.last_scene_cut is None or
            (frame_num - self.last_scene_cut) >= self.min_scene_len):
            scene_list.append(self.last_fade['frame'])
            cut_detected = True
        return cut_detected


class ContentDetector(SceneDetector):
    """Detects fast cuts using changes in colour and intensity between frames.

    Since the difference between frames is used, unlike the ThresholdDetector,
    only fast cuts are detected with this method.  To detect slow fades between
    content scenes still using HSV information, use the DissolveDetector.
    """

    def __init__(self, threshold = 30.0, min_scene_len = 15):
        super(ContentDetector, self).__init__()
        self.threshold = threshold
        self.min_scene_len = min_scene_len  # minimum length of any given scene, in frames
        self.last_frame = None
        self.last_scene_cut = None
        self.last_hsv = None

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):
        # Similar to ThresholdDetector, but using the HSV colour space DIFFERENCE instead
        # of single-frame RGB/grayscale intensity (thus cannot detect slow fades with this method).

        # Value to return indiciating if a scene cut was found or not.
        cut_detected = False
    
        if self.last_frame is not None:
            # Change in average of HSV (hsv), (h)ue only, (s)aturation only, (l)uminance only.
            delta_hsv_avg, delta_h, delta_s, delta_v = 0.0, 0.0, 0.0, 0.0

            if frame_num in frame_metrics and 'delta_hsv_avg' in frame_metrics[frame_num]:
                delta_hsv_avg = frame_metrics[frame_num]['delta_hsv_avg']
                delta_h = frame_metrics[frame_num]['delta_hue']
                delta_s = frame_metrics[frame_num]['delta_sat']
                delta_v = frame_metrics[frame_num]['delta_lum']

            else:
                num_pixels = frame_img.shape[0] * frame_img.shape[1]
                curr_hsv = cv2.split(cv2.cvtColor(frame_img, cv2.COLOR_BGR2HSV))
                last_hsv = self.last_hsv
                if not last_hsv:
                    last_hsv = cv2.split(cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2HSV))

                delta_hsv = [-1, -1, -1]
                for i in range(3):
                    num_pixels = curr_hsv[i].shape[0] * curr_hsv[i].shape[1]
                    curr_hsv[i] = curr_hsv[i].astype(numpy.int32)
                    last_hsv[i] = last_hsv[i].astype(numpy.int32)
                    delta_hsv[i] = numpy.sum(numpy.abs(curr_hsv[i] - last_hsv[i])) / float(num_pixels)
                delta_hsv.append(sum(delta_hsv) / 3.0)
                delta_h, delta_s, delta_v, delta_hsv_avg = delta_hsv

                frame_metrics[frame_num]['delta_hsv_avg'] = delta_hsv_avg
                frame_metrics[frame_num]['delta_hue'] = delta_h
                frame_metrics[frame_num]['delta_sat'] = delta_s
                frame_metrics[frame_num]['delta_lum'] = delta_v

                self.last_hsv = curr_hsv

            if delta_hsv_avg >= self.threshold:
                if self.last_scene_cut is None or (
                  (frame_num - self.last_scene_cut) >= self.min_scene_len):
                    scene_list.append(frame_num)
                    self.last_scene_cut = frame_num
                    cut_detected = True

            #self.last_frame.release()
            del self.last_frame
                
        self.last_frame = frame_img.copy()
        return cut_detected

    def post_process(self, scene_list):
        """Not used for ContentDetector, as cuts are written as they are found."""
        return


class MotionDetector(SceneDetector):
    """Detects motion events in scenes containing a static background.

    Uses background subtraction followed by noise removal (via morphological
    opening) to generate a frame score compared against the set threshold.

    Attributes:
        threshold:  floating point value compared to each frame's score, which
            represents average intensity change per pixel (lower values are
            more sensitive to motion changes).  Default 0.5, must be > 0.0.
        num_frames_post_scene:  Number of frames to include in each motion
            event after the frame score falls below the threshold, adding any
            subsequent motion events to the same scene.
        kernel_size:  Size of morphological opening kernel for noise removal.
            Setting to -1 (default) will auto-compute based on video resolution
            (typically 3 for SD, 5-7 for HD). Must be an odd integer > 1.
    """
    def __init__(self, threshold = 0.50, num_frames_post_scene = 30,
                 kernel_size = -1):
        """Initializes motion-based scene detector object."""
        super(MotionDetector, self).__init__()
        self.threshold = float(threshold)
        self.num_frames_post_scene = int(num_frames_post_scene)

        self.kernel_size = int(kernel_size)
        if self.kernel_size < 0:
            # Set kernel size when process_frame first runs based on
            # video resolution (480p = 3x3, 720p = 5x5, 1080p = 7x7).
            pass

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2( 
            detectShadows = False )

        self.last_frame_score = 0.0

        self.in_motion_event = False
        self.first_motion_frame_index = -1
        self.last_motion_frame_index = -1
        return

    def process_frame(self, frame_num, frame_img, frame_metrics, scene_list):

        # Value to return indiciating if a scene cut was found or not.
        cut_detected = False

        frame_grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        masked_frame = self.bg_subtractor.apply(frame_grayscale)

        kernel = numpy.ones((self.kernel_size, self.kernel_size), numpy.uint8)
        filtered_frame = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)

        frame_score = numpy.sum(filtered_frame) / float( 
            filtered_frame.shape[0] * filtered_frame.shape[1] )

        return cut_detected

    def post_process(self, scene_list):
        """Writes the last scene if the video ends while in a motion event.
        """

        # If the last fade detected was a fade out, we add a corresponding new
        # scene break to indicate the end of the scene.  This is only done for
        # fade-outs, as a scene cut is already added when a fade-in is found.

        if self.in_motion_event:
            # Write new scene based on first and last motion event frames.
            pass
        return self.in_motion_event



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

