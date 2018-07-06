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

""" PySceneDetect scenedetect.timecode Tests

This file includes unit tests for the scenedetect.timecode module (specifically, the
FrameTimecode object, used for representing frame-accurate timestamps and time values).
"""

import unittest

import scenedetect
from scenedetect.frame_timecode import FrameTimecode


class TestFrameTimecode(unittest.TestCase):
    """ FrameTimecode Unit Test Cases

    These unit tests test the FrameTimecode object with respect to object construction,
    testing argument format/limits, operators (addition/subtraction), and conversion
    to and from various time formats like integer frame number, float number of seconds,
    or string HH:MM:SS[.nnn]. timecode format.
    """

    def test_framerate(self):
        ''' Test FrameTimecode constructor argument "fps". '''
        # Not passing fps results in TypeError.
        self.assertRaises(TypeError, FrameTimecode)
        self.assertRaises(TypeError, FrameTimecode, timecode = 0, fps = None)
        self.assertRaises(TypeError, FrameTimecode, timecode = 0, fps = None, new_time = 1)
        # Test zero FPS/negative.
        self.assertRaises(ValueError, FrameTimecode, timecode = 0, fps = 0)
        self.assertRaises(ValueError, FrameTimecode, timecode = 0, fps = -1)
        self.assertRaises(ValueError, FrameTimecode, timecode = 0, fps = -100)
        self.assertRaises(ValueError, FrameTimecode, timecode = 0, fps = 0.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = 0,
                          fps = scenedetect.frame_timecode.MINIMUM_FRAMES_PER_SECOND_FLOAT / 2)
        self.assertRaises(ValueError, FrameTimecode, timecode = 0, fps = -1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = 0, fps = -1000.0)
        # Test positive framerates.
        self.assertEqual(FrameTimecode(timecode = 0, fps = 1).frame_num, 0)
        self.assertEqual(
            FrameTimecode(timecode = 0,
                          fps = scenedetect.frame_timecode.MINIMUM_FRAMES_PER_SECOND_FLOAT)
            .frame_num, 0)
        self.assertEqual(FrameTimecode(timecode = 0, fps = 10).frame_num, 0)
        self.assertEqual(
            FrameTimecode(timecode = 0,
                          fps = scenedetect.frame_timecode.MINIMUM_FRAMES_PER_SECOND_FLOAT * 2)
            .frame_num, 0)
        self.assertEqual(FrameTimecode(timecode = 0, fps = 1000).frame_num, 0)
        self.assertEqual(FrameTimecode(timecode = 0, fps = 1000.0).frame_num, 0)

    def test_new_time(self):
        ''' Test FrameTimecode constructor argument "new_time". '''
        self.assertRaises(TypeError, FrameTimecode, timecode = 0, fps = 1, new_time = 1)
        self.assertRaises(TypeError, FrameTimecode, timecode = 0.0, fps = 1.0, new_time = 1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = FrameTimecode(
            timecode = 0, fps = 1), fps = None, new_time = -0.001)
        self.assertRaises(ValueError, FrameTimecode, timecode = FrameTimecode(
            timecode = 0, fps = 1), fps = None, new_time = "-1")
        self.assertRaises(ValueError, FrameTimecode, timecode = FrameTimecode(
            timecode = 0, fps = 1), fps = None, new_time = "1x")
        self.assertRaises(ValueError, FrameTimecode, timecode = FrameTimecode(
            timecode = 0, fps = 1), fps = None, new_time = -1)
        self.assertEqual(FrameTimecode(timecode = FrameTimecode(
            timecode = 1, fps = 1), fps = None, new_time = 0).frame_num, 0)
        self.assertEqual(FrameTimecode(timecode = FrameTimecode(
            timecode = 1, fps = 1), fps = None, new_time = 1.0).frame_num, 1)
        self.assertEqual(FrameTimecode(timecode = FrameTimecode(
            timecode = 1, fps = 1), fps = None, new_time = "2").frame_num, 2)
        self.assertEqual(FrameTimecode(timecode = FrameTimecode(
            timecode = 1, fps = 1), fps = None, new_time = "00:00:03").frame_num, 3)
        self.assertEqual(FrameTimecode(timecode = FrameTimecode(
            timecode = 1, fps = 1), fps = None, new_time = "00:00:03.900").frame_num, 3)

    def test_timecode_numeric(self):
        ''' Test FrameTimecode constructor argument "timecode" with numeric arguments. '''
        self.assertRaises(ValueError, FrameTimecode, timecode = -1, fps = 1)
        self.assertRaises(ValueError, FrameTimecode, timecode = -1.0, fps = 1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = -0.1, fps = 1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = -1.0/1000, fps = 1.0)
        self.assertEqual(FrameTimecode(timecode = 0, fps = 1).frame_num, 0)
        self.assertEqual(FrameTimecode(timecode = 1, fps = 1).frame_num, 1)
        self.assertEqual(FrameTimecode(timecode = 0.0, fps = 1.0).frame_num, 0)
        self.assertEqual(FrameTimecode(timecode = 1.0, fps = 1.0).frame_num, 1)

    def test_timecode_string(self):
        ''' Test FrameTimecode constructor argument "timecode" with string arguments. '''
        # Invalid strings:
        self.assertRaises(ValueError, FrameTimecode, timecode = '-1', fps = 1)
        self.assertRaises(ValueError, FrameTimecode, timecode = '-1.0', fps = 1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = '-0.1', fps = 1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = '1.0', fps = 1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = '1.9x', fps = 1)
        self.assertRaises(ValueError, FrameTimecode, timecode = '1x', fps = 1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = '1.9.9', fps = 1.0)
        self.assertRaises(ValueError, FrameTimecode, timecode = '1.0-', fps = 1.0)

        # Frame number integer [int->str] ('%d', integer number as string)
        self.assertEqual(FrameTimecode(timecode = '0', fps = 1).frame_num, 0)
        self.assertEqual(FrameTimecode(timecode = '1', fps = 1).frame_num, 1)
        self.assertEqual(FrameTimecode(timecode = '10', fps = 1.0).frame_num, 10)

        # Seconds format [float->str] ('%fs', number as string followed by 's' for seconds)
        self.assertEqual(FrameTimecode(timecode = '0s', fps = 1).frame_num, 0)
        self.assertEqual(FrameTimecode(timecode = '1s', fps = 1).frame_num, 1)
        self.assertEqual(FrameTimecode(timecode = '10s', fps = 1.0).frame_num, 10)
        self.assertEqual(FrameTimecode(timecode = '10.0s', fps = 1.0).frame_num, 10)
        self.assertEqual(FrameTimecode(timecode = '10.0000000000s', fps = 1.0).frame_num, 10)
        self.assertEqual(FrameTimecode(timecode = '10.100s', fps = 1.0).frame_num, 10)
        self.assertEqual(FrameTimecode(timecode = '1.100s', fps = 10.0).frame_num, 11)

        # Standard timecode format [timecode->str] ('HH:MM:SS[.nnn]', where [.nnn] is optional)
        self.assertEqual(FrameTimecode(timecode = '00:00:01', fps = 1).frame_num, 1)
        self.assertEqual(FrameTimecode(timecode = '00:00:01.9999', fps = 1).frame_num, 1)
        self.assertEqual(FrameTimecode(timecode = '00:00:02.0000', fps = 1).frame_num, 2)
        self.assertEqual(FrameTimecode(timecode = '00:00:02.0001', fps = 1).frame_num, 2)

        self.assertEqual(FrameTimecode(timecode = '00:00:01', fps = 10).frame_num, 10)
        self.assertEqual(FrameTimecode(timecode = '00:00:00.5', fps = 10).frame_num, 5)
        self.assertEqual(FrameTimecode(timecode = '00:00:00.100', fps = 10).frame_num, 1)
        self.assertEqual(FrameTimecode(timecode = '00:00:00.001', fps = 1000).frame_num, 1)

        self.assertEqual(FrameTimecode(timecode = '00:00:59.999', fps = 1).frame_num, 59)
        self.assertEqual(FrameTimecode(timecode = '00:01:00.000', fps = 1).frame_num, 60)
        self.assertEqual(FrameTimecode(timecode = '00:01:00.001', fps = 1).frame_num, 60)

        self.assertEqual(FrameTimecode(timecode = '00:59:59.999', fps = 1).frame_num, 3599)
        self.assertEqual(FrameTimecode(timecode = '01:00:00.000', fps = 1).frame_num, 3600)
        self.assertEqual(FrameTimecode(timecode = '01:00:00.001', fps = 1).frame_num, 3600)

    def test_get_frames(self):
        ''' Test FrameTimecode get_frames() method. '''
        self.assertEqual(FrameTimecode(timecode = 1, fps = 1.0).get_frames(), 1)
        self.assertEqual(FrameTimecode(timecode = 1000, fps = 60.0).get_frames(), 1000)
        self.assertEqual(FrameTimecode(timecode = 1000000000, fps = 29.97).get_frames(), 1000000000)

        self.assertEqual(FrameTimecode(timecode = 1.0, fps = 1.0).get_frames(), int(1.0/1.0))
        self.assertEqual(FrameTimecode(timecode = 1000.0, fps = 60.0).get_frames(), int(1000.0*60.0))
        self.assertEqual(FrameTimecode(timecode = 1000000000.0, fps = 29.97).get_frames(), int(1000000000.0*29.97))

        self.assertEqual(FrameTimecode(timecode = '00:00:02.0000', fps = 1).get_frames(), 2)
        self.assertEqual(FrameTimecode(timecode = '00:00:00.5', fps = 10).get_frames(), 5)
        self.assertEqual(FrameTimecode(timecode = '00:00:01', fps = 10).get_frames(), 10)
        self.assertEqual(FrameTimecode(timecode = '00:01:00.000', fps = 1).get_frames(), 60)

    def test_get_seconds(self):
        ''' Test FrameTimecode get_seconds() method. '''
        self.assertAlmostEqual(FrameTimecode(timecode = 1, fps = 1.0).get_seconds(), 1.0/1.0)
        self.assertAlmostEqual(FrameTimecode(timecode = 1000, fps = 60.0).get_seconds(), 1000/60.0)
        self.assertAlmostEqual(FrameTimecode(timecode = 1000000000, fps = 29.97).get_seconds(), 1000000000/29.97)

        self.assertAlmostEqual(FrameTimecode(timecode = 1.0, fps = 1.0).get_seconds(), 1.0)
        self.assertAlmostEqual(FrameTimecode(timecode = 1000.0, fps = 60.0).get_seconds(), 1000.0)
        self.assertAlmostEqual(FrameTimecode(timecode = 1000000000.0, fps = 29.97).get_seconds(), 1000000000.0)

        self.assertAlmostEqual(FrameTimecode(timecode = '00:00:02.0000', fps = 1).get_seconds(), 2.0)
        self.assertAlmostEqual(FrameTimecode(timecode = '00:00:00.5', fps = 10).get_seconds(), 0.5)
        self.assertAlmostEqual(FrameTimecode(timecode = '00:00:01', fps = 10).get_seconds(), 1.0)
        self.assertAlmostEqual(FrameTimecode(timecode = '00:01:00.000', fps = 1).get_seconds(), 60.0)

    def test_get_timecode(self):
        ''' Test FrameTimecode get_timecode() method. '''
        self.assertEqual(FrameTimecode(timecode = 1.0, fps = 1.0).get_timecode(), '00:00:01.000')
        self.assertEqual(FrameTimecode(timecode = 60.117, fps = 60.0).get_timecode(), '00:01:00.117')
        self.assertEqual(FrameTimecode(timecode = 3600.234, fps = 29.97).get_timecode(), '01:00:00.234')

        self.assertEqual(FrameTimecode(timecode = '00:00:02.0000', fps = 1).get_timecode(), '00:00:02.000')
        self.assertEqual(FrameTimecode(timecode = '00:00:00.5', fps = 10).get_timecode(), '00:00:00.500')
        self.assertEqual(FrameTimecode(timecode = '00:00:01.501', fps = 10).get_timecode(), '00:00:01.500')
        self.assertEqual(FrameTimecode(timecode = '00:01:00.000', fps = 1).get_timecode(), '00:01:00.000')

    def test_equality(self):
        ''' Test FrameTimecode equality (==, __eq__) operator. '''
        x = FrameTimecode(timecode = 1.0, fps = 10.0)
        self.assertEqual(x, x)
        self.assertEqual(x, FrameTimecode(timecode = 1.0, fps = 10.0))
        self.assertNotEqual(x, FrameTimecode(timecode = 10.0, fps = 10.0))
        # Comparing FrameTimecodes with different framerates raises a TypeError.
        self.assertRaises(TypeError, x.__eq__, FrameTimecode(timecode = 1.0, fps = 100.0))
        self.assertRaises(TypeError, x.__eq__, FrameTimecode(timecode = 1.0, fps = 10.1))

        self.assertEqual(x, FrameTimecode(x))
        self.assertEqual(x, FrameTimecode(x, new_time = 1.0))
        self.assertEqual(x, FrameTimecode(x, new_time = 10))
        self.assertEqual(x, '00:00:01')
        self.assertEqual(x, '00:00:01.0')
        self.assertEqual(x, '00:00:01.00')
        self.assertEqual(x, '00:00:01.000')
        self.assertEqual(x, '00:00:01.0000')
        self.assertEqual(x, '00:00:01.00000')
        self.assertEqual(x, 10)
        self.assertEqual(x, 1.0)

        self.assertRaises(ValueError, x.__eq__, '0x')
        self.assertRaises(ValueError, x.__eq__, 'x00:00:00.000')
        self.assertRaises(TypeError, x.__eq__, [0])
        self.assertRaises(TypeError, x.__eq__, (0,))
        self.assertRaises(TypeError, x.__eq__, [0, 1, 2, 3])
        self.assertRaises(TypeError, x.__eq__, {0:0})

        self.assertEqual(FrameTimecode(timecode = '00:00:00.5', fps = 10), '00:00:00.500')
        self.assertEqual(FrameTimecode(timecode = '00:00:01.500', fps = 10), '00:00:01.500')
        self.assertEqual(FrameTimecode(timecode = '00:00:01.500', fps = 10), '00:00:01.501')
        self.assertEqual(FrameTimecode(timecode = '00:00:01.500', fps = 10), '00:00:01.502')
        self.assertEqual(FrameTimecode(timecode = '00:00:01.500', fps = 10), '00:00:01.508')
        self.assertEqual(FrameTimecode(timecode = '00:00:01.500', fps = 10), '00:00:01.509')
        self.assertEqual(FrameTimecode(timecode = '00:00:01.519', fps = 10), '00:00:01.510')

    def test_addition(self):
        ''' Test FrameTimecode addition (+/+=, __add__/__iadd__) operator. '''
        x = FrameTimecode(timecode = 1.0, fps = 10.0)
        self.assertEqual(x + 1, FrameTimecode(timecode = 1.1, fps = 10.0))
        self.assertEqual(x + 1, FrameTimecode(x, new_time = 1.1))
        self.assertEqual(x + 10, 20)
        self.assertEqual(x + 10, 2.0)

        self.assertEqual(x + 10, '00:00:02.000')

        self.assertRaises(TypeError, FrameTimecode('00:00:02.000', fps = 20.0).__eq__, x + 10)

    def test_subtraction(self):
        ''' Test FrameTimecode subtraction (-/-=, __sub__) operator. '''
        x = FrameTimecode(timecode = 1.0, fps = 10.0)
        self.assertEqual(x - 1, FrameTimecode(timecode = 0.9, fps = 10.0))
        self.assertEqual(x - 2, FrameTimecode(x, new_time = 0.8))
        self.assertEqual(x - 10, FrameTimecode(x, new_time = 0.0))
        self.assertEqual(x - 11, FrameTimecode(x, new_time = 0.0))
        self.assertEqual(x - 100, FrameTimecode(x, new_time = 0.0))

        self.assertEqual(x - 1.0, FrameTimecode(x, new_time = 0.0))
        self.assertEqual(x - 100.0, FrameTimecode(x, new_time = 0.0))

        self.assertEqual(x - 1, FrameTimecode(timecode = 0.9, fps = 10.0))

        self.assertRaises(TypeError, FrameTimecode('00:00:02.000', fps = 20.0).__eq__, x - 10)

