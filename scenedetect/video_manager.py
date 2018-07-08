# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
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

""" PySceneDetect scenedetect.video_manager Module

This file contains the VideoManager class, which provides a consistent
interface to reading videos.

This module includes both single-threaded (VideoManager) and asynchronous
(VideoManagerAsync) video manager classes, which can be used to pass a
video (or sequence of videos) and a start and end time/duration to a
SceneManager object for performing scene detection analysis.

The VideoManager class attempts to emulate some methods of the OpenCV
cv2.VideoCapture object, and can be used interchangably with one with
respect to a SceneManager object.
"""


# Standard Library Imports
from __future__ import print_function
import os
import math

# PySceneDetect Library Imports
import scenedetect.platform
import scenedetect.frame_timecode
from scenedetect.frame_timecode import FrameTimecode

# Third-Party Library Imports
import cv2


class VideoOpenFailure(Exception):
    def __init__(self, file_list=None, message=
                 "OpenCV VideoCapture object failed to return True when calling isOpened()."):
        # type: (Iterable[(str, str)], str)
        # Pass message string to base Exception class.
        super(VideoOpenFailure, self).__init__(message)
        # list of (filename: str, filepath: str)
        self.file_list = file_list

class VideoFramerateUnavailable(Exception):
    def __init__(self, file_name=None, file_path=None, message=
                 "OpenCV VideoCapture object failed to return framerate when calling "
                 "get(cv2.CAP_PROP_FPS)."):
        # type: (str, str, str)
        # Pass message string to base Exception class.
        super(VideoFramerateUnavailable, self).__init__(message)
        # Set other exception properties.
        self.file_name = file_name
        self.file_path = file_path

class VideoParameterMismatch(Exception):
    def __init__(self, file_list=None, message=
                 "OpenCV VideoCapture object parameters do not match."):
        # type: (Iterable[Tuple[int, float, float, str, str]], str)
        # Pass message string to base Exception class.
        super(VideoParameterMismatch, self).__init__(message)
        # list of (param_mismatch_type: int, parameter value, expected value,
        #          filename: str, filepath: str)
        # where param_mismatch_type is an OpenCV CAP_PROP (e.g. CAP_PROP_FPS).
        self.file_list = file_list

class VideoDecodingInProgress(RuntimeError):
    pass

class VideoDecoderProcessStarted(RuntimeError):
    pass

class VideoDecoderProcessNotStarted(RuntimeError):
    pass

def get_video_name(video_file):
    # type: (str) -> Tuple[str, str]
    if isinstance(video_file, int):
        return ('Device %d' % video_file, video_file)
    return (os.path.split(video_file)[1], video_file)


def open_captures(video_files, framerate=None, validate_parameters=True):
    # type: (Iterable[str], float, bool) -> Tuple[List[VideoCapture], float, Tuple[int, int]]
    """ Open Captures - helper function to open all capture objects, set the framerate,
    and ensure that all open captures have been opened and the framerates match on a list
    of video file paths, or a list containing a single device ID.

    Arguments:
        video_files (list of str(s)/int): A list of one or more paths (str), or a list
            of a single integer device ID, to open as an OpenCV VideoCapture object.
            A ValueError will be raised if the list does not conform to the above.
        framerate (float, optional): Framerate to assume when opening the video_files.
            If not set, the first open video is used for deducing the framerate of
            all videos in the sequence.
        validate_parameters (bool, optional): If true, will ensure that the frame sizes
            (width, height) and frame rate (FPS) of all passed videos is the same.
            A VideoParameterMismatch is raised if the framerates do not match.

    Returns:
        A tuple of form (cap_list, framerate, framesize) where cap_list is a list of open
        OpenCV VideoCapture objects in the same order as the video_files list, framerate
        is a float of the video(s) framerate(s), and framesize is a tuple of (width, height)
        where width and height are integers representing the frame size in pixels.

    Raises:
        ValueError, IOError, VideoFramerateUnavailable, VideoParameterMismatch
    """
    is_device = False
    if not video_files:
        raise ValueError("Expected at least 1 video file or device ID.")
    if isinstance(video_files[0], int):
        if len(video_files) > 1:
            raise ValueError("If device ID is specified, no video sources may be appended.")
        elif video_files[0] < 0:
            raise ValueError("Invalid/negative device ID specified.")
        is_device = True
    elif not all([isinstance(video_file, str) for video_file in video_files]):
        raise ValueError("Unexpected element type in video_files list (expected str(s)/int).")
    elif framerate is not None and not isinstance(framerate, float):
        raise TypeError("Expected type float for parameter framerate.")
    # Check if files exist.
    if not is_device and any([not os.path.exists(video_file) for video_file in video_files]):
        raise IOError("Video file(s) not found.")
    cap_list = []

    try:
        cap_list = [cv2.VideoCapture(video_file) for video_file in video_files]
        video_names = [get_video_name(video_file) for video_file in video_files]
        closed_caps = [video_names[i] for i, cap in
                       enumerate(cap_list) if not cap.isOpened()]
        if closed_caps:
            raise VideoOpenFailure(closed_caps)

        cap_framerates = [cap.get(cv2.CAP_PROP_FPS) for cap in cap_list]
        cap_framerate, check_framerate = validate_capture_framerate(
            video_names, cap_framerates, framerate)
        
        cap_frame_sizes = [(math.trunc(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                            math.trunc(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
                           for cap in cap_list]
        cap_frame_size = cap_frame_sizes[0]

        # If we need to validate the parameters, we check that the FPS and width/height of all
        # open captures is identical (or almost identical in the case of FPS).
        if validate_parameters:
            validate_capture_parameters(
                video_names=video_names, cap_frame_sizes=cap_frame_sizes,
                check_framerate=check_framerate, cap_framerates=cap_framerates)

    except:
        release_captures(cap_list)
        raise

    return (cap_list, cap_framerate, cap_frame_size)

def release_captures(cap_list):
    # type: (Iterable[VideoCapture]) -> None
    for cap in cap_list:
        cap.release()

def close_captures(cap_list):
    # type: (Iterable[VideoCapture]) -> None
    for cap in cap_list:
        cap.close()

def validate_capture_framerate(video_names, cap_framerates, framerate=None):
    # type: (List[Tuple[str, str]], List[float], Optional[float]) -> Tuple[float, bool]
    check_framerate = True
    cap_framerate = cap_framerates[0]
    if framerate is not None:
        if isinstance(framerate, float):
            if framerate < scenedetect.frame_timecode.MINIMUM_FRAMES_PER_SECOND_FLOAT:
                raise ValueError("Invalid framerate (must be a positive non-zero value).")
            cap_framerate = framerate
            check_framerate = False
        else:
            raise TypeError("Expected float for framerate, got %s." % type(framerate).__name__)
    else:
        unavailable_framerates = [(video_names[i][0], video_names[i][1]) for
                                  i, fps in enumerate(cap_framerates) if fps <
                                  scenedetect.frame_timecode.MINIMUM_FRAMES_PER_SECOND_FLOAT]
        if unavailable_framerates:
            raise VideoFramerateUnavailable(unavailable_framerates)
    return (cap_framerate, check_framerate)

def validate_capture_parameters(video_names, cap_frame_sizes, check_framerate=False,
                                cap_framerates=None):
    # type: (List[Tuple[str, str]], List[Tuple[int, int]], Optional[bool], Optional[List[float]]) -> None
    bad_params = []
    max_framerate_delta = scenedetect.frame_timecode.MINIMUM_FRAMES_PER_SECOND_FLOAT
    # Check heights/widths match.
    bad_params += [(cv2.CAP_PROP_FRAME_WIDTH, frame_size[0],
                    cap_frame_sizes[0][0], video_names[i][0], video_names[i][1]) for
                   i, frame_size in enumerate(cap_frame_sizes)
                   if abs(frame_size[0] - cap_frame_sizes[0][0]) > 0]
    bad_params += [(cv2.CAP_PROP_FRAME_HEIGHT, frame_size[1],
                    cap_frame_sizes[0][1], video_names[i][0], video_names[i][1]) for
                   i, frame_size in enumerate(cap_frame_sizes)
                   if abs(frame_size[1] - cap_frame_sizes[0][1]) > 0]
    # Check framerates if required.
    if check_framerate:
        bad_params += [(cv2.CAP_PROP_FPS, fps, cap_framerates[0], video_names[i][0],
                        video_names[i][1]) for i, fps in enumerate(cap_framerates)
                       if math.fabs(fps - cap_framerates[0]) > max_framerate_delta]

    if bad_params:
        raise VideoParameterMismatch(bad_params)




class VideoManager(object):
    """ Object for providing a cv2.VideoCapture-like interface to a set of one or more
    video files, or a single device ID.  Similar to VideoManagerAsync, but runs in the
    same thread that it is created in.  Supports seeking and setting end time/duration.
    """
    def __init__(self, video_files, framerate=None):
        # type: (List[str], Optional[float])
        """ VideoManager Constructor Method (__init__)

        Arguments:
            video_files (list of str(s)/int): A list of one or more paths (str), or a list
                of a single integer device ID, to open as an OpenCV VideoCapture object.
            framerate (float, optional): Framerate to assume when storing FrameTimecodes.
                If not set (i.e. is None), it will be deduced from the first open capture
                in video_files, else raises a VideoFramerateUnavailable exception.

        Raises:
            ValueError, TypeError, IOError, VideoOpenFailure, VideoFramerateUnavailable,
            VideoFramerateMismatch
        """
        if not video_files:
            raise ValueError("At least one string/integer must be passed in the video_files list.")
        # These VideoCaptures are only open in this process.
        self._cap_list, self._cap_framerate, self._cap_framesize = open_captures(
            video_files=video_files, framerate=framerate)
        self._end_of_video = False
        self._start_time = FrameTimecode(0, self.get_framerate())
        self._end_time = None
        self._curr_time = FrameTimecode(0, self.get_framerate())
        self._last_frame = None
        self._curr_cap, self._curr_cap_idx = None, None

    def get_framerate(self):
        # type: () -> float
        """ Get Framerate - returns the framerate the VideoManager is assuming for all
        open VideoCaptures.  Obtained from either the capture itself, or the passed
        framerate parameter when the VideoManager object was constructed.
        Returns:
            (float) Framerate, in frames/sec.
        """
        return self._cap_framerate

    def get_base_timecode(self):
        # type: () -> FrameTimecode
        """ Get Base Timecode - returns a FrameTimecode object at frame 0 (i.e. time 00:00:00).

        Returns:
            (FrameTimecode) FrameTimecode with video framerate set to frame 0 (time 00:00:00).
        """
        return FrameTimecode(timecode=0, fps=self.get_framerate())

    def get_framesize(self):
        # type: () -> Tuple[int, int]
        """ Get Framerate - returns the framerate the VideoManager is assuming for all
        open VideoCaptures.  Obtained from either the capture itself, or the passed
        framerate parameter when the VideoManager object was constructed.
        Returns:
            Tuple of ints of the form (width, height) where width and height represent
            the size of the video frame in pixels.
        """
        return self._cap_framesize

    def set_duration(self, duration=None, start_time=None, end_time=None):
        # type: (Optional[FrameTimecode], Optional[FrameTimecode], Optional[FrameTimecode]) -> None
        """ Set Duration - sets the duration/length of the video(s) to decode, as well as
        the start/end times.  Must be called before start() is called, otherwise a
        VideoDecodingInProgress exception will be thrown.

        Arguments:
        Raises:
            VideoDecodingInProgress
        """
        # Ensure any passed timecodes have the proper framerate.
        if ((duration is not None and not duration.equal_framerate(self._cap_framerate)) or
                (start_time is not None and not start_time.equal_framerate(self._cap_framerate)) or
                (end_time is not None and not end_time.equal_framerate(self._cap_framerate))):
            raise ValueError("FrameTimecode framerate does not match.")

        if duration is not None and end_time is not None:
            raise TypeError("Only one of duration and end_time may be specified, not both.")

        if start_time is not None:
            self._start_time = start_time

        if end_time is not None:
            if end_time < start_time:
                raise ValueError("end_time is before start_time in time.")
            self._end_time = end_time
        elif duration is not None:
            self._end_time = start_time + duration

    def start(self):
        # type: () -> None
        """ Start - starts video decoding/frame queuing thread/process.  Raises
        exception VideoDecoderProcessStarted if the method is called after the
        decoder process has already been started.

        Raises:
            VideoDecoderProcessStarted
        """
        self._get_next_cap()
        self.seek(self._start_time)

    def seek(self, timecode):
        # type: (FrameTimecode) -> None

        while timecode < self._curr_time:
            # Seek to required time.
            if self._curr_cap.grab():
                self._curr_time += 1
            else:
                if not self._get_next_cap():
                    break

    def stop(self, timeout=None):
        # type: (Optional[float]) -> None
        """ Stop - not required for synchronous version of VideoManager. """
        pass

    def release(self):
        # type: () -> None
        """ Release (cv2.VideoCapture method), releases all open capture(s).

        Raises:
            VideoDecoderProcessStarted
        """
        release_captures(self._cap_list)
        del self._cap_list[:]

    def get(self, property, index=0):
        # type: (int, Optional[int]) -> float
        """ Get (cv2.VideoCapture method) - obtains capture properties from the current
        VideoCapture object in use.  Index represents the same index as the original
        video_files list passed to the constructor.  Getting/setting the position (POS)
        properties has no effect; seeking is implemented using VideoDecoder methods.

        Arguments:
            property: OpenCV VideoCapture property to get (i.e. CAP_PROP_FPS).
            index (optional): Index in file_list of capture to get property from (default
                is zero). Index is not checked and will raise exception if out of bounds.

        Returns:
            Return value from calling get(property) on the VideoCapture object.
        """
        return self._cap_list[index].get(property)



    def grab(self):
        # type: () -> bool
        """ Grab (cv2.VideoCapture method) - retrieves a frame but does not return it.
        Returns:
            True if a frame was grabbed, False otherwise.
        """
        grabbed = False
        if self._curr_cap is not None and self._end_of_video != True:
            while not grabbed:
                grabbed = self._curr_cap.grab()
                if not grabbed and not self._get_next_cap():
                    break
                else:
                    self._curr_time += 1
        if self._end_time is not None and self._curr_time >= self._end_time:
            grabbed = False
            self._last_frame = None
        return grabbed


    def retrieve(self):
        # type: () -> Tuple[bool, Union[None, numpy.ndarray]]
        """ Retrieve (cv2.VideoCapture method) - retrieves and returns a frame.

        Returns:
            Tuple of (True, frame_image) where frame_image is the frame from the last
            call to grab(), returns (False, None) otherwise (i.e. no more frames).
        """
        retrieved = False
        if self._curr_cap is not None and self._end_of_video != True:
            while not retrieved:
                retrieved, self._last_frame = self._curr_cap.retrieve()
                if not retrieved and not self._get_next_cap():
                    break
        if self._end_time is not None and self._curr_time >= self._end_time:
            retrieved = False
            self._last_frame = None
        return (retrieved, self._last_frame)

    def read(self):
        # type: () -> Tuple[bool, Union[None, numpy.ndarray]]
        """ Read (cv2.VideoCapture method) - retrieves and returns a frame.

        Returns:
            Tuple of (True, frame_image) if a frame was grabbed,
            (False, None) otherwise.
        """
        read_frame = False
        if self._curr_cap is not None and self._end_of_video != True:
            while not read_frame:
                read_frame, self._last_frame = self._curr_cap.read()
                if not read_frame and not self._get_next_cap():
                    break
        if self._end_time is not None and self._curr_time >= self._end_time:
            read_frame = False
            self._last_frame = None
        if read_frame:
            self._curr_time += 1
        return (read_frame, self._last_frame)


    def _get_next_cap(self):
        # type: () -> bool
        self._curr_cap = None
        if self._curr_cap_idx is None:
            self._curr_cap_idx = 0
            self._curr_cap = self._cap_list[0]
            return True
        else:
            if not (self._curr_cap_idx + 1) < len(self._cap_list):
                self._end_of_video = True
                return False
            self._curr_cap_idx += 1
            self._curr_cap = self._cap_list[self._curr_cap_idx]
            return True
