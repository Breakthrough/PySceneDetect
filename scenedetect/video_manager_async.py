# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains the VideoManagerAsync class, which provides a
# consistent interface to reading videos (asynchronously).
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
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

""" PySceneDetect scenedetect.video_manager_async Module

This module includes the asynchronous (VideoManagerAsync) video manager
class, which can be used to pass a video (or sequence of videos) and a
start and end time/duration to a SceneManager object for performing scene
detection analysis.

The VideoManagerAsync uses a separate process to perform all file I/O
and video decoding, leaving all frame parsing/scene detection to the
main process.

This may be replaced with a C++11 implementation in the future, as there
appears to be resource contention issues with the Python implementation
(on both Python 2.x and 3.x).  Also under consideration is implementing
the scene detection algorithms in C++11.  None of these changes will
affect the Python API, and if these changes are made, equivalent Python
objects acting as light-weight ctypes wrappers shall be provided.

The VideoManager class attempts to emulate some methods of the OpenCV
cv2.VideoCapture object, and can be used interchangably with one with
respect to a SceneManager object.
"""


# Standard Library Imports
from __future__ import print_function
import os
import math
import time

# multiprocessing requires pickling objects, limits to < 32MB per frame, may not
# work for 8K video yet (will require splitting frame up into N chunks).
# Should make a non-multiprocessing version which is quicker for small videos.
import multiprocessing
import scenedetect.platform
from scenedetect.platform import queue

# PySceneDetect Library Imports
import scenedetect.frame_timecode
from scenedetect.frame_timecode import FrameTimecode

import scenedetect.video_manager

from scenedetect.video_manager import get_video_name
from scenedetect.video_manager import open_captures
from scenedetect.video_manager import release_captures
from scenedetect.video_manager import close_captures
from scenedetect.video_manager import validate_capture_framerate
from scenedetect.video_manager import validate_capture_parameters

from scenedetect.video_manager import VideoManager
from scenedetect.video_manager import VideoOpenFailure
from scenedetect.video_manager import VideoFramerateUnavailable
from scenedetect.video_manager import VideoParameterMismatch
from scenedetect.video_manager import VideoDecodingInProgress
from scenedetect.video_manager import VideoDecoderProcessStarted
from scenedetect.video_manager import VideoDecoderProcessNotStarted


# Third-Party Library Imports
import cv2


def compute_queue_size(frame_size, max_frames = 512, max_memory_mb = 4096):
    # type: (Tuple[int, int], int, int) -> int
    # Queue up to max_frames frames or max_memory_gb worth of frames (assume 3 bytes/pixel).
    frame_size_bytes = (frame_size[0] * frame_size[1] * 3)
    # If max_frames takes up less than max_memory_gb, than we take that as the max size.
    max_frames_size_mb = (max_frames * frame_size_bytes) / (1024**2)
    if max_frames_size_mb < max_memory_mb:
        return max_frames
    else:
        # Compute number of frames that can fit into max_memory_gb.
        max_frames = (max_memory_mb * (1024**2)) / frame_size_bytes
        return max_frames


class VideoManagerAsync(object):
    """ Object for providing a multithreaded queue of frames decoded from a passed
    list of video files (one-element list of integer device ID).  Attempts to emulate
    *most* of the API methods provided by the OpenCV cv2.VideoCapture class. This
    class handles validating the input videos, managing the frame queue, and managing
    the decoder process, whereas the VideoDecoder object is responsible for the logic
    of the decoder process only (i.e. decoding the required frames into the queue).

    Arguments:
        video_files (list of str(s)/int): A list of one or more paths (str), or a list
            of a single integer device ID, to open as an OpenCV VideoCapture object and
            start reading and queuing frames from when start() is called.
        framerate (float, optional): Framerate to assume when storing FrameTimecodes.
            If not set (i.e. is None), it will be deduced from the first open capture
            in video_files, else raises a VideoFramerateUnavailable exception.
        max_queue_size_mb (int, optional): Maximum amount of memory that can be used
            for the frame queue, in megabytes (MiB).  Default is 4096 (4 gigabytes).
    Raises:
        VideoOpenFailure, VideoFramerateUnavailable, VideoFramerateMismatch
    """
    def __init__(self, video_files, framerate = None, max_queue_size_mb = 4096):
        # type: (List[str], Optional[float], Optional[int])
        if not len(video_files) > 0:
            raise ValueError("At least one string/integer must be passed in the video_files list.")
        # These VideoCaptures are only open in this process.
        self._cap_list, self._cap_framerate, self._cap_framesize = open_captures(
            video_files = video_files, framerate = framerate)
        self._frame_queue = multiprocessing.Queue(compute_queue_size(
            frame_size = self._cap_framesize, max_memory_mb = max_queue_size_mb))
        self._stop_decoder = multiprocessing.Event()
        self._stop_decoder.set()
        self._end_of_video = multiprocessing.Event()
        self._end_of_video.clear()
        self._decoder_done = multiprocessing.Event()
        self._decoder_done.clear()
        self._decoder = VideoDecoder(video_files = video_files, framerate = framerate,
                                     frame_queue = self._frame_queue)
        self._decoder_process = None
        self._start_time = None
        self._end_time = None
        self._last_frame = None
        self._end_of_video_sentinel = False

    def get_framerate(self):
        # type: () -> float
        return self._cap_framerate

    def get_framesize(self):
        # type: () -> Tuple[int, int]
        return self._cap_framesize

    def set_duration(self, duration = None, start_time = None, end_time = None):
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
        if not self._stop_decoder.is_set() or (
            (self._decoder_process is not None and self._decoder_process.is_alive())):
            raise VideoDecoderProcessStarted()
        self._stop_decoder.clear()
        self._decoder_process = multiprocessing.Process(
            target = self._decoder.thread_func, args = (
                (self._stop_decoder, self._end_of_video, self._decoder_done),
                self._start_time, self._end_time))
        self._decoder_process.start()

    def stop(self, timeout = 1.0):
        # type: (float) -> None
        """ Stop - stops video decoding/frame queuing thread/process. """
        if self._stop_decoder.is_set():
            raise VideoDecoderProcessNotStarted()
        self._stop_decoder.set()
        if self._decoder_process.is_alive():
            self._decoder_process.join(timeout=timeout)
            if self._decoder_process.is_alive():
                self._decoder_process.terminate()

    def release(self):
        # type: () -> None
        """ Release (cv2.VideoCapture method), releases all open capture(s).

        Raises:
            VideoDecoderProcessStarted
        """
        if not self._stop_decoder.is_set():
            raise VideoDecoderProcessStarted()
        release_captures(self._cap_list)
        del self._cap_list[:]

    def get(self, property, index = 0):
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


    def _get_frame_from_queue(self, max_wait_time = 30.0):
        # type: (Optional[float]) -> Union[None, numpy.ndarray]
        frame = None
        if not self._end_of_video_sentinel:
            try:
                frame = self._frame_queue.get(timeout=max_wait_time)
                if isinstance(frame, str) and frame == 'EOF':
                    self._end_of_video_sentinel = True
                    frame = None
            except queue.Empty:
                frame = None
        return frame

    def grab(self):
        # type: () -> bool
        """ Grab (cv2.VideoCapture method) - retrieves a frame but does not return it.
        Returns:
            True if a frame was grabbed, False otherwise.
        Raises:
            VideoDecoderProcessNotStarted
        """
        if self._stop_decoder.is_set():
            raise VideoDecoderProcessNotStarted()
        
        self._last_frame = self._get_frame_from_queue()
        return self._last_frame is not None

    def retrieve(self):
        # type: () -> Tuple[bool, Union[None, numpy.ndarray]]
        """ Retrieve (cv2.VideoCapture method) - retrieves and returns a frame.

        Returns:
            Tuple of (True, frame_image) where frame_image is the frame from the last
            call to grab(), returns (False, None) otherwise (i.e. no more frames).
        """
        if self._stop_decoder.is_set():
            raise VideoDecoderProcessNotStarted()
        
        return (self._last_frame is not None, self._last_frame)

    def read(self):
        # type: () -> Tuple[bool, Union[None, numpy.ndarray]]
        """ Read (cv2.VideoCapture method) - retrieves and returns a frame.

        Returns:
            Tuple of (True, frame_image) if a frame was grabbed,
            (False, None) otherwise.
        """
        if self._stop_decoder.is_set():
            raise VideoDecoderProcessNotStarted()
        
        self._last_frame = self._get_frame_from_queue()
        return (self._last_frame is not None, self._last_frame)



class VideoDecoder(object):
    """ Object for providing a multithreaded queue of frames decoded from a passed
    list of video files (one-element list of integer device ID).  Underlying
    implementation of video decoding for the VideoManager class.  Unlike the
    VideoManager, this class is solely responsible for decoding the required frames
    and placing them asynchronously into the queue.

    Arguments:
        video_files (list of str(s)/int): A list of one or more paths (str), or a list
            of a single integer device ID, to open as an OpenCV VideoCapture object and
            start reading and queuing frames from when start() is called.
        decoder_events (tuple, required): Tuple of multiprocessing.Event objects
            in the form (stop_decoder, end_of_video) where each tuple element is:
                stop_decoder: Signal for decoder process to stop running.
                end_of_video: Signaled by decoder process when end of video(s) is reached.
        frame_queue (multiprocessing.Queue, required): Queue to put decoded frames into.
        framerate (float, optional): Framerate to assume when storing FrameTimecodes.
            If not set (i.e. is None), it will be deduced from the first open capture
            in video_files, else raises a VideoFramerateUnavailable exception.
    """

    def __init__(self, video_files,frame_queue, framerate = None):
        # type: (List[str], multiprocessing.Queue, Optional[float])

        self._video_files = video_files
        self._framerate = framerate
        self._stop_decoder, self._end_of_video, self._decoder_done = None, None, None
        self._frame_queue = frame_queue

        self._cap_list = None


    def _get_next_cap(self, curr_cap_idx):
        # type: (int) -> Tuple[Union[None, cv2.VideoCapture], int]
        curr_cap = None
        if curr_cap_idx is None:
            curr_cap_idx = 0
            curr_cap = self._cap_list[0]
        else:
            if not (curr_cap_idx + 1) < len(self._cap_list):
                return (None, curr_cap_idx + 1)
            curr_cap_idx += 1
            curr_cap = self._cap_list[curr_cap_idx]
        return (curr_cap, curr_cap_idx)
        

    def _put_frame_into_queue(self, frame):
        # type(Union[numpy.ndarray, str]) -> bool
        frame_queued = False
        while not frame_queued:
            try:
                self._frame_queue.put_nowait(frame)
                frame_queued = True
            except queue.Full:
                pass
            if self._stop_decoder.is_set():
                break
        return frame_queued



    def thread_func(self, decoder_events, start_time = None, end_time = None):
        # type: (Tuple[multiprocessing.Event, multiprocessing.Event, multiprocessing.Event],
        #        Optional[FrameTimecode], Optional[FrameTimecode]) -> int
        """ 
        Arguments:
            decoder_events (tuple, required): Tuple of multiprocessing.Event objects
                in the form (stop_decoder, end_of_video) where each tuple element is:
                    stop_decoder: Signal for decoder process to stop running.
                    end_of_video: Signaled by decoder process when end of video(s) is reached.
                    decoder_done: Signaled by decoder process when end of decode loop reached.
        """

        self._stop_decoder, self._end_of_video, self._decoder_done = decoder_events

        # These VideoCaptures are only open in this process.
        self._cap_list, cap_framerate, cap_framesize = open_captures(
            video_files = self._video_files, framerate = self._framerate)

        if not len(self._cap_list) > 0:
            return 1

        curr_cap, curr_cap_idx = self._get_next_cap(None)
        curr_frame = 0

        start_frame = 0 if start_time is None else start_time.get_frames()
        end_frame = None if end_time is None else end_time.get_frames()

        try:
            while not self._stop_decoder.is_set():
                if curr_cap is None:
                    self._end_of_video.set()
                    break
                # Seek to start if required.
                if start_frame is not None and curr_frame < start_frame:
                    if not curr_cap.grab():
                        curr_cap, curr_cap_idx = self._get_next_cap(curr_cap_idx)
                        continue
                    curr_frame += 1
                    continue
                # Start decoding frames into queue.
                if end_frame is not None and curr_frame >= end_frame:
                    self._end_of_video.set()
                    break
                (ret_val, im_cap) = curr_cap.read()
                if not ret_val:
                    curr_cap, curr_cap_idx = self._get_next_cap(curr_cap_idx)
                    continue
                if not self._put_frame_into_queue(im_cap):
                    break
                curr_frame += 1
        finally:
            # Flag to other processes that queue will be empty soon.
            self._put_frame_into_queue('EOF')
            self._decoder_done.set()
            # Close all captures before closing process.
            release_captures(self._cap_list)

        return 0
        

