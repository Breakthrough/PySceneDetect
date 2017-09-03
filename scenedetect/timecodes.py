#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# This file contains all code related to timecode formats, interpreting,
# parsing, and conversion.
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

import math

# New class for maintaining a consistent API for frame-accurate timecode objects.
class FrameTimecode(object):
    """ Object for frame-based timecodes, using the video framerate
    to compute back and forth between frame number and second/timecode formats.

    The passed argument is declared valid if it meets one of three valid forms:
      1) Standard timecode HH:MM:SS[.nnn]:
            in string form 'HH:MM:SS' or 'HH:MM:SS.nnn', or
            in list/tuple form [HH, MM, SS] or [HH, MM, SS.nnn]
      2) Number of seconds S[.SSS], where S >= 0.0:
            in string form 'Ss' or 'S.SSSs' (e.g. '5s', '1.234s'), or
            in integer or floating point form S or S.SSS
      3) Exact number of frames N, where N >= 0:
            in either integer or string form N or 'N'

    Arguments:
        timecode:  A timecode or frame number, given in any of the above valid
                   formats/types.  This argument is always required.
        fps:       The framerate to base all frame to time arithmetic on, to
                   allow frame-accurate arithmetic.  The framerate must be the
                   same when combining FrameTimecode objects in operations.
                   This argument is required argument, unless the passed
                   timecode is of type FrameTimecode, from which it is copied.
        new_time:  A timecode or frame number to overwrite the existing one.
                   This can only be set/used when the passed timecode value is
                   of type FrameTimecode, where it overrides the passed frames.
    Raises:
        TypeError, ValueError
    """

    def __init__(self, timecode = None, fps = None, new_time = None):
        # The following two properties are what is used to keep track of time
        # in a frame-specific manner.  Note that once the framerate is set,
        # the value should never be modified (only read if required).
        self.framerate = None
        self.frame_num = None

        # Copy constructor.  Only the timecode (and, optionally, new_time)
        # arguments are used in this case.
        if isinstance(timecode, FrameTimecode):
            self.framerate = timecode.framerate
            self.frame_num = timecode.frame_num
            if fps is not None:
                raise TypeError('Framerate cannot be overwritten when copying a FrameTimecode.')
            if new_time is None:
                return
            else:
                # Overwrite timecode so it will be replaced below as usual.
                timecode = new_time
        else:
            # Ensure other arguments are consistent with API.
            if fps is None:
                raise TypeError('Framerate (fps) is a required argument.')

            # Process the given framerate, if it was not already set.
            elif not isinstance(fps, (int, float)):
                raise TypeError('Framerate must be of type int/float.')
            self.framerate = float(fps)

        # Process the timecode value, storing it as an exact number of frames.
        # Exact number of frames N
        if isinstance(timecode, int):
            if timecode < 0:
                raise ValueError('Timecode frame number must be positive.')
            self.frame_num = timecode
        # Number of seconds S
        elif isinstance(timecode, float):
            if timecode < 0.0:
                raise ValueError('Timecode value must be positive.')
            self.frame_num = int(timecode * self.framerate)
        # Standard timecode in list format [HH, MM, SS.nnn]
        elif isinstance(timecode, (list, tuple)) and len(timecode) == 3:
            if any(not isinstance(x, (int, float)) for x in timecode):
                raise ValueError('Timecode components must be of type int/float.')
            hrs, mins, secs = timecode
            if not (hrs >= 0 and mins >= 0 and secs >= 0 and mins < 60
                    and secs < 60):
                raise ValueError('Timecode components must be positive.')
            secs += (((hrs * 60.0) + mins) * 60.0)
            self.frame_num = int(secs * self.framerate)
        elif isinstance(timecode, str):
            # The _parse_timecode_string method handles the three time formats.
            self.frame_num = self._parse_timecode_string(timecode)

        else:
            raise TypeError('Timecode format unrecognized.')

    """ Parses a string based on the three possible forms (in timecode format,
    as an integer number of frames, or floating-point seconds, ending with 's').
    Requires that the framerate property is set before calling this method.
    Assuming a framerate of 30.0 FPS, the strings '00:05:00.000', '00:05:00',
    '9000', '300s', and '300.0s' are all possible valid values, all representing
    a period of time equal to 5 minutes, 300 seconds, or 9000 frames (at 30 FPS).

    Raises:
        TypeError, ValueError
    """
    def _parse_timecode_string(self, timecode_string):
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
                raise TypeError('Unrecognized or improperly formatted timecode string.')
            hrs, mins = int(tc_val[0]), int(tc_val[1])
            secs = float(tc_val[2]) if '.' in tc_val[2] else int(tc_val[2])
            if not (hrs >= 0 and mins >= 0 and secs >= 0 and mins < 60 and secs < 60):
                raise ValueError('Invalid timecode range (values outside allowed range).')
            secs += (((hrs * 60.0) + mins) * 60.0)
            return int(secs * self.framerate)

    def __add__(self, other):
        if isinstance(other, int):
            self.frame_num += other
        elif isinstance(other, FrameTimecode):
            if math.fabs(self.framerate - other.framerate) < 0.001:
                self.frame_num += other.frame_num
            else:
                raise ValueError('FrameTimecode instances require equal framerates for addition.')
        # Check if value to add is in number of seconds.
        elif isinstance(other, float):
            raise NotImplementedError()
        else:
            raise TypeError('Unsupported type for performing addition with FrameTimecode objects.')
        return FrameTimecode(self)

    def __sub__(self, other):
        raise NotImplementedError()

    def get_frames(self):
        """ Get the current time/position in number of frames.  This is the
        equivalent of accessing the self.frame_num property (which, along
        with the specified framerate, forms the base for all of the other
        time measurement calculations, e.g. the get_seconds() method).

        Returns:
            An integer of the current time/frame number.
        """
        return int(self.frame_num)

    def get_seconds(self):
        """ Get the frame's position in number of seconds.

        Returns:
            A float of the current time/position in seconds.
        """
        return float(self.frame_num) / self.framerate

    def get_timecode(self, precision = 3, use_rounding = True):
        """ Get a formatted timecode string of the form HH:MM:SS[.nnn].

        Args:
            precision:     The number of decimal places to include in the output [.nnn].
            use_rounding:  True (default) to round the output to the desired precision.

        Returns:
            A string with a formatted timecode (HH:MM:SS[.nnn]).
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
            msec = format(secs, '.%df' % precision)[-precision:]
            secs = '%02d.%s' % (int(secs), msec)
        else:
            secs = '%02d' % int(round(secs, 0)) if use_rounding else '%02d' % int(secs)
        # Return hours, minutes, and seconds as a formatted timecode string.
        return '%02d:%02d:%s' % (hrs, mins, secs)


#
# Once the above class implementation is finished, and the API has fully
# transitioned to the new FrameTimecode format, the below legacy code can then
# be removed, since there is no need to differentiate between timecode formats
# now. Note that the above implementation was heavily inspired by my work on
# processing timecode formats for the DVR-Scan project.
#
# The code below can now all be safely called legacy (v0.4 and below), and will
# be completely removed by the release of the new API with PySceneDetect v0.5.
#


# # # # # # # # # # # # 


# Default value for -f / --format-timecode CLI argument (see the
# get_timecode_formats() function for a list of timecode formats and names).
FORMAT_DEFAULT = 'standard'


def get_available():
    """Returns a tuple of two dicts of the available/enabled timecode formats.

    In the future, timecode parsing will be moved to discrete objects like what
    is done with the SceneDetector objects in get_available_detectors().

    Returns:
        A dictionary with the form {name (string): description (string)},
        where name is the common name used via the command-line, and
        description is a human-readable description of the format.
    """
    timecode_format_dict = {
        'standard': 'Cut times will be given in HH:MM:SS.nnnn format.',
        'frames': 'Cut times will be given in frames (exact integers).',
        'seconds': 'Cut times will be given in seconds (3 decimal places).'
    }
    return timecode_format_dict


def get_string(time_msec, show_msec = True):
    """ Formats a time, in ms, into a timecode of the form HH:MM:SS.nnnn.

    This is the default timecode format used by mkvmerge for splitting a video.

    Args:
        time_msec:  Integer representing milliseconds from start of video.
        show_msec:  If False, omits the milliseconds part from the output.
    Returns:
        A string with a formatted timecode (HH:MM:SS.nnnn).
    """
    out_nn, timecode_str = int(time_msec), ''

    base_msec = 1000 * 60 * 60  # 1 hour in ms
    out_HH = int(out_nn / base_msec)
    out_nn -= out_HH * base_msec

    base_msec = 1000 * 60       # 1 minute in ms
    out_MM = int(out_nn / base_msec)
    out_nn -= out_MM * base_msec

    base_msec = 1000            # 1 second in ms
    out_SS = int(out_nn / base_msec)
    out_nn -= out_SS * base_msec

    if show_msec:
        timecode_str = "%02d:%02d:%02d.%03d" % (out_HH, out_MM, out_SS, out_nn)
    else:
        timecode_str = "%02d:%02d:%02d" % (out_HH, out_MM, out_SS)

    return timecode_str


def frame_to_timecode(frames, fps, show_msec = True):
    """ Converts a given frame/FPS into a timecode of the form HH:MM:SS.nnnn.

    Args:
        frames:     Integer representing the frame number to get the time of.
        fps:        Float representing framerate of the video.
        show_msec:  If False, omits the milliseconds part from the output.
    Returns:
        A string with a formatted timecode (HH:MM:SS.nnnn).
    """
    time_msec = 1000.0 * float(frames) / fps
    return get_string(time_msec, show_msec)

