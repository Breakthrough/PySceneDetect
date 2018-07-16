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
# PySceneDetect is licensed under the BSD 2-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses Numpy, OpenCV, click, pytest, mkvmerge, and ffmpeg. See
# the included LICENSE-* files, or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
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
import logging

# Third-Party Library Imports
import cv2

# PySceneDetect Library Imports
from scenedetect.platform import STRING_TYPE
import scenedetect.frame_timecode
from scenedetect.frame_timecode import FrameTimecode


class VideoOpenFailure(Exception):
    """ VideoOpenFailure: Raised when an OpenCV VideoCapture object fails to open (i.e. calling
    the isOpened() method returns a non True value). """
    def __init__(self, file_list=None, message=
                 "OpenCV VideoCapture object failed to return True when calling isOpened()."):
        # type: (Iterable[(str, str)], str)
        # Pass message string to base Exception class.
        super(VideoOpenFailure, self).__init__(message)
        # list of (filename: str, filepath: str)
        self.file_list = file_list


class VideoFramerateUnavailable(Exception):
    """ VideoFramerateUnavailable: Raised when the framerate cannot be determined from the video,
    and the framerate has not been overriden/forced in the VideoManager. """
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
    """ VideoParameterMismatch: Raised when opening multiple videos with a VideoManager, and some 
    of the video parameters (frame height, frame width, and framerate/FPS) do not match. """
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
    """ VideoDecodingInProgress: Raised when attempting to call certain VideoManager methods that
    must be called *before* start() has been called. """
    pass


class VideoDecoderNotStarted(RuntimeError):
    """ VideoDecodingInProgress: Raised when attempting to call certain VideoManager methods that
    must be called *after* start() has been called. """
    pass


def get_video_name(video_file):
    # type: (str) -> Tuple[str, str]
    """ Get Video Name: Returns a string representing the video file/device name.
    
    Returns:
        str: Video file name or device ID. In the case of a video, only the file
            name is returned, not the whole path. For a device, the string format
            is 'Device 123', where 123 is the integer ID of the capture device.
    """
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
    elif not all([isinstance(video_file, (str, STRING_TYPE)) for video_file in video_files]):
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
        # Store frame sizes as integers (VideoCapture.get() returns float).
        cap_frame_sizes = [(math.trunc(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                            math.trunc(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
                           for cap in cap_list]
        cap_frame_size = cap_frame_sizes[0]

        # If we need to validate the parameters, we check that the FPS and width/height
        # of all open captures is identical (or almost identical in the case of FPS).
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
    """ Close Captures:  Calls the release() method on every capture in cap_list. """
    for cap in cap_list:
        cap.release()


def close_captures(cap_list):
    # type: (Iterable[VideoCapture]) -> None
    """ Close Captures:  Calls the close() method on every capture in cap_list. """
    for cap in cap_list:
        cap.close()


def validate_capture_framerate(video_names, cap_framerates, framerate=None):
    # type: (List[Tuple[str, str]], List[float], Optional[float]) -> Tuple[float, bool]
    """ Validate Capture Framerate: Ensures that the passed capture framerates are valid and equal.
    
    Raises:
        ValueError, TypeError, VideoFramerateUnavailable
    """
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
    """ Validate Capture Parameters: Ensures that all passed capture frame sizes and (optionally)
    framerates are equal.  Raises VideoParameterMismatch if there is a mismatch.
    
    Raises:
        VideoParameterMismatch
    """
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
        self._start_time = self.get_base_timecode()
        self._end_time = None
        self._curr_time = self.get_base_timecode()
        self._last_frame = None
        self._curr_cap, self._curr_cap_idx = None, None
        self._video_file_paths = video_files
        logging.info(
            'VideoManager: Loaded %d video%s, framerate: %.2f FPS, resolution: %d x %d.',
            len(self._cap_list), 's' if len(self._cap_list) > 1 else '',
            self.get_framerate(), *self.get_framesize())
        self._started = False


    def get_num_videos(self):
        # type: () -> int
        """ Get Number of Videos - returns the length of the capture list (self._cap_list),
        representing the number of videos the VideoManager has opened.
        Returns:
            (int) Number of videos, equal to length of capture list.
        """
        return len(self._cap_list)


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
        """ Get Base Timecode - returns a FrameTimecode object at frame 0 / time 00:00:00.

        The timecode returned by this method can be used to perform arithmetic (e.g.
        addition), passing the resulting values back to the VideoManager (e.g. for the
        set_duration() method), as the framerate of the returned FrameTimecode object
        matches that of the VideoManager.

        As such, this method is equivalent to creating a FrameTimecode at frame 0 with
        the VideoManager framerate, for example, given a VideoManager called obj,
        the following expression will evaluate as True:
            obj.get_base_timecode() == FrameTimecode(0, obj.get_framerate())

        Furthermore, the base timecode object returned by a particular VideoManager
        should not be passed to another one, unless you first verify that their
        framerates are the same.

        Returns:
            FrameTimecode object set to frame 0/time 00:00:00 with the video(s) framerate.
        """
        return FrameTimecode(timecode=0, fps=self._cap_framerate)


    def get_current_timecode(self):
        # type: () -> FrameTimecode
        """ Get Current Timecode - returns a FrameTimecode object at current VideoManager position.

        Returns:
            FrameTimecode object at the current VideoManager position with the video(s) framerate.
        """
        return self._curr_time


    def get_framesize(self):
        # type: () -> Tuple[int, int]
        """ Get Framerate - returns the framerate the VideoManager is assuming for all
        open VideoCaptures.  Obtained from either the capture itself, or the passed
        framerate parameter when the VideoManager object was constructed.

        Returns:
            Tuple[int, int]: Video frame size in the form (width, height) where width
                and height represent the size of the video frame in pixels.
        """
        return self._cap_framesize


    def set_duration(self, duration=None, start_time=None, end_time=None):
        # type: (Optional[FrameTimecode], Optional[FrameTimecode], Optional[FrameTimecode]) -> None
        """ Set Duration - sets the duration/length of the video(s) to decode, as well as
        the start/end times.  Must be called before start() is called, otherwise a
        VideoDecodingInProgress exception will be thrown.  May be called after reset()
        as well.

        Arguments:
            duration (Optional[FrameTimecode]): The (maximum) duration in time to
                decode from the opened video(s). Mutually exclusive with end_time
                (i.e. if duration is set, end_time must be None).
            start_time (Optional[FrameTimecode]): The time/first frame at which to
                start decoding frames from. If set, the input video(s) will be
                seeked to when start() is called, at which point the frame at
                start_time can be obtained by calling retrieve().
            end_time (Optional[FrameTimecode]): The time at which to stop decoding
                frames from the opened video(s). Mutually exclusive with duration
                (i.e. if end_time is set, duration must be None).

        Raises:
            VideoDecodingInProgress
        """
        if self._started:
            raise VideoDecodingInProgress()

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
            self._end_time = self._start_time + duration

        logging.info('VideoManager: Duration set, start: %s, duration: %s, end: %s.',
                     start_time.get_timecode() if start_time is not None else start_time,
                     duration.get_timecode() if duration is not None else duration,
                     end_time.get_timecode() if end_time is not None else end_time)


    def start(self):
        # type: () -> None
        """ Start - starts video decoding and seeks to start time.  Raises
        exception VideoDecodingInProgress if the method is called after the
        decoder process has already been started.

        Raises:
            VideoDecodingInProgress
        """
        if self._started:
            raise VideoDecodingInProgress()
            
        self._started = True
        self._get_next_cap()
        self.seek(self._start_time)


    def seek(self, timecode):
        # type: (FrameTimecode) -> None
        """ Seek - seeks forwards to the passed timecode.

        Only supports seeking forwards (i.e. timecode must be greater than the
        current VideoManager position).  Can only be used after the start()
        method has been called.

        Arguments:
            timecode (FrameTimecode): Time in video to seek forwards to.

        Raises:
            VideoDecoderNotStarted
        """
        if not self._started:
            raise VideoDecoderNotStarted()

        while self._curr_time < timecode:
            # Seek to required time.
            if self._curr_cap.grab():
                self._curr_time += 1
            else:
                if not self._get_next_cap():
                    break


    def release(self):
        # type: () -> None
        """ Release (cv2.VideoCapture method), releases all open capture(s). """
        release_captures(self._cap_list)
        self._cap_list = []
        self._started = False


    def reset(self):
        # type: () -> None
        """ Reset - Reopens captures passed to the constructor of the VideoManager.

        Can only be called after the release method has been called.

        Raises:
            VideoDecodingInProgress
        """
        if self._started:
            raise VideoDecodingInProgress()

        self._started = False
        self._curr_time = self.get_base_timecode()
        self._cap_list, self._cap_framerate, self._cap_framesize = open_captures(
            video_files=self._video_file_paths, framerate=self._curr_time.get_framerate())


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
            bool: True if a frame was grabbed, False otherwise.

        Raises:
            VideoDecoderNotStarted
        """
        if not self._started:
            raise VideoDecoderNotStarted()

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

        Frame returned corresponds to last call to get().

        Returns:
            Tuple[bool, Union[None, numpy.ndarray]]: Returns tuple of
                (True, frame_image) if a frame was grabbed during the last call
                to grab(), and where frame_image is a numpy ndarray of the
                decoded frame, otherwise returns (False, None).

        Raises:
            VideoDecoderNotStarted
        """
        if not self._started:
            raise VideoDecoderNotStarted()

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
            Tuple[bool, Union[None, numpy.ndarray]]: Returns tuple of
                (True, frame_image) if a frame was grabbed, where frame_image
                is a numpy ndarray of the decoded frame, otherwise (False, None).

        Raises:
            VideoDecoderNotStarted
        """
        if not self._started:
            raise VideoDecoderNotStarted()

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

