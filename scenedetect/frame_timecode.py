# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2019 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" ``scenedetect.frame_timecode``

This module contains the :py:class:`FrameTimecode` object, which is used as a way for
PySceneDetect to store frame-accurate timestamps of each cut. This is done by also
specifying the video framerate with the timecode, allowing a frame number to be
converted to/from a floating-point number of seconds, or string in the form
`"HH:MM:SS[.nnn]"` where the `[.nnn]` part is optional.

See the following examples, or the :py:class:`FrameTimecode constructor <FrameTimecode>`.

Unit tests for the FrameTimecode object can be found in `tests/test_timecode.py`.
"""

# Standard Library Imports
import math

# PySceneDetect Library Imports
from scenedetect.platform import STRING_TYPE


MINIMUM_FRAMES_PER_SECOND_FLOAT = 1.0 / 1000.0
MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT = 1.0 / 100000


class FrameTimecode(object):
    """ Object for frame-based timecodes, using the video framerate
    to compute back and forth between frame number and second/timecode formats.

    The timecode argument is valid only if it complies with one of the following
    three types/formats:

    1) string: standard timecode HH:MM:SS[.nnn]:
        `str` in form 'HH:MM:SS' or 'HH:MM:SS.nnn', or
        `list`/`tuple` in form [HH, MM, SS] or [HH, MM, SS.nnn]
    2) float: number of seconds S[.SSS], where S >= 0.0:
        `float` in form S.SSS, or
        `str` in form 'Ss' or 'S.SSSs' (e.g. '5s', '1.234s')
    3) int: Exact number of frames N, where N >= 0:
        `int` in form `N`, or
        `str` in form 'N'

    Arguments:
        timecode (str, float, int, or FrameTimecode):  A timecode or frame
            number, given in any of the above valid formats/types.  This
            argument is always required.
        fps (float, or FrameTimecode, conditionally required): The framerate
            to base all frame to time arithmetic on (if FrameTimecode, copied
            from the passed framerate), to allow frame-accurate arithmetic. The
            framerate must be the same when combining FrameTimecode objects
            in operations. This argument is always required, unless **timecode**
            is a FrameTimecode.
    Raises:
        TypeError: Thrown if timecode is wrong type/format, or if fps is None
            or a type other than int or float.
        ValueError: Thrown when specifying a negative timecode or framerate.
    """

    def __init__(self, timecode=None, fps=None):
        # type: (Union[int, float, str, FrameTimecode], float,
        #        Union[int, float, str, FrameTimecode])
        # The following two properties are what is used to keep track of time
        # in a frame-specific manner.  Note that once the framerate is set,
        # the value should never be modified (only read if required).
        self.framerate = None
        self.frame_num = None

        # Copy constructor.  Only the timecode argument is used in this case.
        if isinstance(timecode, FrameTimecode):
            self.framerate = timecode.framerate
            self.frame_num = timecode.frame_num
            if fps is not None:
                raise TypeError('Framerate cannot be overwritten when copying a FrameTimecode.')
        else:
            # Ensure other arguments are consistent with API.
            if fps is None:
                raise TypeError('Framerate (fps) is a required argument.')
            if isinstance(fps, FrameTimecode):
                fps = fps.framerate

            # Process the given framerate, if it was not already set.
            if not isinstance(fps, (int, float)):
                raise TypeError('Framerate must be of type int/float.')
            elif (isinstance(fps, int) and not fps > 0) or (
                    isinstance(fps, float) and not fps >= MINIMUM_FRAMES_PER_SECOND_FLOAT):
                raise ValueError('Framerate must be positive and greater than zero.')
            self.framerate = float(fps)

        # Process the timecode value, storing it as an exact number of frames.
        if isinstance(timecode, (str, STRING_TYPE)):
            self.frame_num = self._parse_timecode_string(timecode)
        else:
            self.frame_num = self._parse_timecode_number(timecode)

        # Alternative formats under consideration (require unit tests before adding):

        # Standard timecode in list format [HH, MM, SS.nnn]
        #elif isinstance(timecode, (list, tuple)) and len(timecode) == 3:
        #    if any(not isinstance(x, (int, float)) for x in timecode):
        #        raise ValueError('Timecode components must be of type int/float.')
        #    hrs, mins, secs = timecode
        #    if not (hrs >= 0 and mins >= 0 and secs >= 0 and mins < 60
        #            and secs < 60):
        #        raise ValueError('Timecode components must be positive.')
        #    secs += (((hrs * 60.0) + mins) * 60.0)
        #    self.frame_num = int(secs * self.framerate)


    def get_frames(self):
        # type: () -> int
        """ Get the current time/position in number of frames.  This is the
        equivalent of accessing the self.frame_num property (which, along
        with the specified framerate, forms the base for all of the other
        time measurement calculations, e.g. the :py:meth:`get_seconds` method).

        If using to compare a :py:class:`FrameTimecode` with a frame number,
        you can do so directly against the object (e.g. ``FrameTimecode(10, 10.0) <= 10``).

        Returns:
            int: The current time in frames (the current frame number).
        """
        return int(self.frame_num)


    def get_framerate(self):
        # type: () -> float
        """ Get Framerate: Returns the framerate used by the FrameTimecode object.

        Returns:
            float: Framerate of the current FrameTimecode object, in frames per second.
        """
        return self.framerate


    def equal_framerate(self, fps):
        # type: (float) -> bool
        """ Equal Framerate: Determines if the passed framerate is equal to that of the
        FrameTimecode object.

        Arguments:
            fps:    Framerate (float) to compare against within the precision constant
                    MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT defined in this module.

        Returns:
            bool: True if passed fps matches the FrameTimecode object's framerate, False otherwise.

        """
        return math.fabs(self.framerate - fps) < MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT


    def get_seconds(self):
        # type: () -> float
        """ Get the frame's position in number of seconds.

        If using to compare a :py:class:`FrameTimecode` with a frame number,
        you can do so directly against the object (e.g. ``FrameTimecode(10, 10.0) <= 1.0``).

        Returns:
            float: The current time/position in seconds.
        """
        return float(self.frame_num) / self.framerate


    def get_timecode(self, precision=3, use_rounding=True):
        # type: (int, bool) -> str
        """ Get a formatted timecode string of the form HH:MM:SS[.nnn].

        Args:
            precision:     The number of decimal places to include in the output ``[.nnn]``.
            use_rounding:  True (default) to round the output to the desired precision.

        Returns:
            str: The current time in the form ``"HH:MM:SS[.nnn]"``.
        """
        # Compute hours and minutes based off of seconds, and update seconds.
        secs = self.get_seconds()
        base = 60.0 * 60.0
        hrs = int(secs / base)
        secs -= (hrs * base)
        base = 60.0
        mins = int(secs / base)
        secs -= (mins * base)
        # Convert seconds into string based on required precision.
        if precision > 0:
            if use_rounding:
                secs = round(secs, precision)
                #secs = math.ceil(secs * (10**precision)) / float(10**precision)
            msec = format(secs, '.%df' % precision)[-precision:]
            secs = '%02d.%s' % (int(secs), msec)
        else:
            secs = '%02d' % int(round(secs, 0)) if use_rounding else '%02d' % int(secs)
        # Return hours, minutes, and seconds as a formatted timecode string.
        return '%02d:%02d:%s' % (hrs, mins, secs)


    def _seconds_to_frames(self, seconds):
        # type: (float) -> int
        """ Converts the passed value seconds to the nearest number of frames using
        the current FrameTimecode object's FPS (self.framerate).

        Returns:
            Integer number of frames the passed number of seconds represents using
            the current FrameTimecode's framerate property.
        """
        return int(seconds * self.framerate)


    def _parse_timecode_number(self, timecode):
        # type: (Union[int, float]) -> int
        """ Parses a timecode number, storing it as the exact number of frames.
        Can be passed as frame number (int), seconds (float)

        Raises:
            TypeError, ValueError
        """
        # Process the timecode value, storing it as an exact number of frames.
        # Exact number of frames N
        if isinstance(timecode, int):
            if timecode < 0:
                raise ValueError('Timecode frame number must be positive and greater than zero.')
            return timecode
        # Number of seconds S
        elif isinstance(timecode, float):
            if timecode < 0.0:
                raise ValueError('Timecode value must be positive and greater than zero.')
            return self._seconds_to_frames(timecode)
        # FrameTimecode
        elif isinstance(timecode, FrameTimecode):
            return timecode.frame_num
        elif timecode is None:
            raise TypeError('Timecode/frame number must be specified!')
        else:
            raise TypeError('Timecode format/type unrecognized.')


    def _parse_timecode_string(self, timecode_string):
        # type: (str) -> int
        """ Parses a string based on the three possible forms (in timecode format,
        as an integer number of frames, or floating-point seconds, ending with 's').
        Requires that the framerate property is set before calling this method.
        Assuming a framerate of 30.0 FPS, the strings '00:05:00.000', '00:05:00',
        '9000', '300s', and '300.0s' are all possible valid values, all representing
        a period of time equal to 5 minutes, 300 seconds, or 9000 frames (at 30 FPS).

        Raises:
            TypeError, ValueError
        """
        if self.framerate is None:
            raise TypeError('self.framerate must be set before calling _parse_timecode_string.')
        # Number of seconds S
        if timecode_string.endswith('s'):
            secs = timecode_string[:-1]
            if not secs.replace('.', '').isdigit():
                raise ValueError('All characters in timecode seconds string must be digits.')
            secs = float(secs)
            if secs < 0.0:
                raise ValueError('Timecode seconds value must be positive.')
            return int(secs * self.framerate)
        # Exact number of frames N
        elif timecode_string.isdigit():
            timecode = int(timecode_string)
            if timecode < 0:
                raise ValueError('Timecode frame number must be positive.')
            return timecode
        # Standard timecode in string format 'HH:MM:SS[.nnn]'
        else:
            tc_val = timecode_string.split(':')
            if not (len(tc_val) == 3 and tc_val[0].isdigit() and tc_val[1].isdigit()
                    and tc_val[2].replace('.', '').isdigit()):
                raise ValueError('Unrecognized or improperly formatted timecode string.')
            hrs, mins = int(tc_val[0]), int(tc_val[1])
            secs = float(tc_val[2]) if '.' in tc_val[2] else int(tc_val[2])
            if not (hrs >= 0 and mins >= 0 and secs >= 0 and mins < 60 and secs < 60):
                raise ValueError('Invalid timecode range (values outside allowed range).')
            secs += (((hrs * 60.0) + mins) * 60.0)
            return int(secs * self.framerate)


    def __iadd__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> FrameTimecode
        if isinstance(other, int):
            self.frame_num += other
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                self.frame_num += other.frame_num
            else:
                raise ValueError('FrameTimecode instances require equal framerate for addition.')
        # Check if value to add is in number of seconds.
        elif isinstance(other, float):
            self.frame_num += self._seconds_to_frames(other)
        else:
            raise TypeError('Unsupported type for performing addition with FrameTimecode.')
        if self.frame_num < 0:     # Required to allow adding negative seconds/frames.
            self.frame_num = 0
        return self


    def __add__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> FrameTimecode
        to_return = FrameTimecode(timecode=self)
        to_return += other
        return to_return


    def __isub__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> FrameTimecode
        if isinstance(other, int):
            self.frame_num -= other
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                self.frame_num -= other.frame_num
            else:
                raise ValueError('FrameTimecode instances require equal framerate for subtraction.')
        # Check if value to add is in number of seconds.
        elif isinstance(other, float):
            self.frame_num -= self._seconds_to_frames(other)
        else:
            raise TypeError('Unsupported type for performing subtraction with FrameTimecode.')
        if self.frame_num < 0:
            self.frame_num = 0
        return self


    def __sub__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> FrameTimecode
        to_return = FrameTimecode(timecode=self)
        to_return -= other
        return to_return


    def __eq__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> bool
        if isinstance(other, int):
            return self.frame_num == other
        elif isinstance(other, float):
            return self.get_seconds() == other
        elif isinstance(other, str):
            return self.frame_num == self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num == other.frame_num
            else:
                raise TypeError(
                    'FrameTimecode objects must have the same framerate to be compared.')
        elif other is None:
            return False
        else:
            raise TypeError('Unsupported type for performing == with FrameTimecode.')


    def __ne__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> bool
        return not self == other


    def __lt__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> bool
        if isinstance(other, int):
            return self.frame_num < other
        elif isinstance(other, float):
            return self.get_seconds() < other
        elif isinstance(other, str):
            return self.frame_num < self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num < other.frame_num
            else:
                raise TypeError(
                    'FrameTimecode objects must have the same framerate to be compared.')
        #elif other is None:
        #    return False
        else:
            raise TypeError('Unsupported type for performing < with FrameTimecode.')


    def __le__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> bool
        if isinstance(other, int):
            return self.frame_num <= other
        elif isinstance(other, float):
            return self.get_seconds() <= other
        elif isinstance(other, str):
            return self.frame_num <= self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num <= other.frame_num
            else:
                raise TypeError(
                    'FrameTimecode objects must have the same framerate to be compared.')
        #elif other is None:
        #    return False
        else:
            raise TypeError('Unsupported type for performing <= with FrameTimecode.')


    def __gt__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> bool
        if isinstance(other, int):
            return self.frame_num > other
        elif isinstance(other, float):
            return self.get_seconds() > other
        elif isinstance(other, str):
            return self.frame_num > self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num > other.frame_num
            else:
                raise TypeError(
                    'FrameTimecode objects must have the same framerate to be compared.')
        #elif other is None:
        #    return False
        else:
            raise TypeError('Unsupported type (%s) for performing > with FrameTimecode.' %
                            type(other).__name__)


    def __ge__(self, other):
        # type: (Union[int, float, str, FrameTimecode]) -> bool
        if isinstance(other, int):
            return self.frame_num >= other
        elif isinstance(other, float):
            return self.get_seconds() >= other
        elif isinstance(other, str):
            return self.frame_num >= self._parse_timecode_string(other)
        elif isinstance(other, FrameTimecode):
            if self.equal_framerate(other.framerate):
                return self.frame_num >= other.frame_num
            else:
                raise TypeError(
                    'FrameTimecode objects must have the same framerate to be compared.')
        #elif other is None:
        #    return False
        else:
            raise TypeError('Unsupported type for performing >= with FrameTimecode.')



    def __int__(self):
        return self.frame_num

    def __float__(self):
        return self.get_seconds()

    def __str__(self):
        return self.get_timecode()

    def __repr__(self):
        return 'FrameTimecode(frame=%d, fps=%f)' % (self.frame_num, self.framerate)

