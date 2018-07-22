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
# This software uses the Numpy, OpenCV, click, tqdm, and pytest libraries.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.timecode Tests

This file includes unit tests for the scenedetect.timecode module (specifically, the
FrameTimecode object, used for representing frame-accurate timestamps and time values).

These unit tests test the FrameTimecode object with respect to object construction,
testing argument format/limits, operators (addition/subtraction), and conversion
to and from various time formats like integer frame number, float number of seconds,
or string HH:MM:SS[.nnn]. timecode format.
"""

# Standard project pylint disables for unit tests using pytest.
# pylint: disable=no-self-use, protected-access, multiple-statements, invalid-name
# pylint: disable=redefined-outer-name


# Third-Party Library Imports
import pytest

# Standard Library Imports
import scenedetect
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.frame_timecode import MINIMUM_FRAMES_PER_SECOND_FLOAT


def test_framerate():
    ''' Test FrameTimecode constructor argument "fps". '''
    # Not passing fps results in TypeError.
    with pytest.raises(TypeError): FrameTimecode()
    with pytest.raises(TypeError): FrameTimecode(timecode=0, fps=None)
    with pytest.raises(TypeError): FrameTimecode(timecode=0, fps=None, new_time=1)
    # Test zero FPS/negative.
    with pytest.raises(ValueError): FrameTimecode(timecode=0, fps=0)
    with pytest.raises(ValueError): FrameTimecode(timecode=0, fps=-1)
    with pytest.raises(ValueError): FrameTimecode(timecode=0, fps=-100)
    with pytest.raises(ValueError): FrameTimecode(timecode=0, fps=0.0)
    with pytest.raises(ValueError): FrameTimecode(timecode=0, fps=-1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode=0, fps=-1000.0)
    with pytest.raises(ValueError):
        FrameTimecode(timecode=0, fps=MINIMUM_FRAMES_PER_SECOND_FLOAT / 2)
    # Test positive framerates.
    assert FrameTimecode(timecode=0, fps=1).frame_num == 0
    assert FrameTimecode(timecode=0, fps=MINIMUM_FRAMES_PER_SECOND_FLOAT).frame_num == 0
    assert FrameTimecode(timecode=0, fps=10).frame_num == 0
    assert FrameTimecode(timecode=0, fps=MINIMUM_FRAMES_PER_SECOND_FLOAT * 2).frame_num == 0
    assert FrameTimecode(timecode=0, fps=1000).frame_num == 0
    assert FrameTimecode(timecode=0, fps=1000.0).frame_num == 0

def test_new_time():
    ''' Test FrameTimecode constructor argument "new_time". '''
    with pytest.raises(TypeError): FrameTimecode(timecode = 0, fps = 1, new_time = 1)
    with pytest.raises(TypeError): FrameTimecode(timecode = 0.0, fps = 1.0, new_time = 1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode = FrameTimecode(
        timecode = 0, fps = 1), fps = None, new_time = -0.001)
    with pytest.raises(ValueError): FrameTimecode(timecode = FrameTimecode(
        timecode = 0, fps = 1), fps = None, new_time = "-1")
    with pytest.raises(ValueError): FrameTimecode(timecode = FrameTimecode(
        timecode = 0, fps = 1), fps = None, new_time = "1x")
    with pytest.raises(ValueError): FrameTimecode(timecode = FrameTimecode(
        timecode = 0, fps = 1), fps = None, new_time = -1)
    assert FrameTimecode(timecode = FrameTimecode(
        timecode = 1, fps = 1), fps = None, new_time = 0).frame_num == 0
    assert FrameTimecode(timecode = FrameTimecode(
        timecode = 1, fps = 1), fps = None, new_time = 1.0).frame_num == 1
    assert FrameTimecode(timecode = FrameTimecode(
        timecode = 1, fps = 1), fps = None, new_time = "2").frame_num == 2
    assert FrameTimecode(timecode = FrameTimecode(
        timecode = 1, fps = 1), fps = None, new_time = "00:00:03").frame_num == 3
    assert FrameTimecode(timecode = FrameTimecode(
        timecode = 1, fps = 1), fps = None, new_time = "00:00:03.900").frame_num == 3

def test_timecode_numeric():
    ''' Test FrameTimecode constructor argument "timecode" with numeric arguments. '''
    with pytest.raises(ValueError): FrameTimecode(timecode = -1, fps = 1)
    with pytest.raises(ValueError): FrameTimecode(timecode = -1.0, fps = 1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode = -0.1, fps = 1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode = -1.0/1000, fps = 1.0)
    assert FrameTimecode(timecode = 0, fps = 1).frame_num == 0
    assert FrameTimecode(timecode = 1, fps = 1).frame_num == 1
    assert FrameTimecode(timecode = 0.0, fps = 1.0).frame_num == 0
    assert FrameTimecode(timecode = 1.0, fps = 1.0).frame_num == 1

def test_timecode_string():
    ''' Test FrameTimecode constructor argument "timecode" with string arguments. '''
    # Invalid strings:
    with pytest.raises(ValueError): FrameTimecode(timecode = '-1', fps = 1)
    with pytest.raises(ValueError): FrameTimecode(timecode = '-1.0', fps = 1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode = '-0.1', fps = 1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode = '1.0', fps = 1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode = '1.9x', fps = 1)
    with pytest.raises(ValueError): FrameTimecode(timecode = '1x', fps = 1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode = '1.9.9', fps = 1.0)
    with pytest.raises(ValueError): FrameTimecode(timecode = '1.0-', fps = 1.0)

    # Frame number integer [int->str] ('%d', integer number as string)
    assert FrameTimecode(timecode = '0', fps = 1).frame_num == 0
    assert FrameTimecode(timecode = '1', fps = 1).frame_num == 1
    assert FrameTimecode(timecode = '10', fps = 1.0).frame_num == 10

    # Seconds format [float->str] ('%fs', number as string followed by 's' for seconds)
    assert FrameTimecode(timecode = '0s', fps = 1).frame_num == 0
    assert FrameTimecode(timecode = '1s', fps = 1).frame_num == 1
    assert FrameTimecode(timecode = '10s', fps = 1.0).frame_num == 10
    assert FrameTimecode(timecode = '10.0s', fps = 1.0).frame_num == 10
    assert FrameTimecode(timecode = '10.0000000000s', fps = 1.0).frame_num == 10
    assert FrameTimecode(timecode = '10.100s', fps = 1.0).frame_num == 10
    assert FrameTimecode(timecode = '1.100s', fps = 10.0).frame_num == 11

    # Standard timecode format [timecode->str] ('HH:MM:SS[.nnn]', where [.nnn] is optional)
    assert FrameTimecode(timecode = '00:00:01', fps = 1).frame_num == 1
    assert FrameTimecode(timecode = '00:00:01.9999', fps = 1).frame_num == 1
    assert FrameTimecode(timecode = '00:00:02.0000', fps = 1).frame_num == 2
    assert FrameTimecode(timecode = '00:00:02.0001', fps = 1).frame_num == 2

    assert FrameTimecode(timecode = '00:00:01', fps = 10).frame_num == 10
    assert FrameTimecode(timecode = '00:00:00.5', fps = 10).frame_num == 5
    assert FrameTimecode(timecode = '00:00:00.100', fps = 10).frame_num == 1
    assert FrameTimecode(timecode = '00:00:00.001', fps = 1000).frame_num == 1

    assert FrameTimecode(timecode = '00:00:59.999', fps = 1).frame_num == 59
    assert FrameTimecode(timecode = '00:01:00.000', fps = 1).frame_num == 60
    assert FrameTimecode(timecode = '00:01:00.001', fps = 1).frame_num == 60

    assert FrameTimecode(timecode = '00:59:59.999', fps = 1).frame_num == 3599
    assert FrameTimecode(timecode = '01:00:00.000', fps = 1).frame_num == 3600
    assert FrameTimecode(timecode = '01:00:00.001', fps = 1).frame_num == 3600

def test_get_frames():
    ''' Test FrameTimecode get_frames() method. '''
    assert FrameTimecode(timecode = 1, fps = 1.0).get_frames(), 1
    assert FrameTimecode(timecode = 1000, fps = 60.0).get_frames(), 1000
    assert FrameTimecode(timecode = 1000000000, fps = 29.97).get_frames(), 1000000000

    assert FrameTimecode(timecode = 1.0, fps = 1.0).get_frames(), int(1.0/1.0)
    assert FrameTimecode(timecode = 1000.0, fps = 60.0).get_frames(), int(1000.0*60.0)
    assert FrameTimecode(timecode = 1000000000.0, fps = 29.97).get_frames(), int(1000000000.0*29.97)

    assert FrameTimecode(timecode = '00:00:02.0000', fps = 1).get_frames(), 2
    assert FrameTimecode(timecode = '00:00:00.5', fps = 10).get_frames(), 5
    assert FrameTimecode(timecode = '00:00:01', fps = 10).get_frames(), 10
    assert FrameTimecode(timecode = '00:01:00.000', fps = 1).get_frames(), 60

def test_get_seconds():
    ''' Test FrameTimecode get_seconds() method. '''
    assert FrameTimecode(timecode = 1, fps = 1.0).get_seconds(), pytest.approx(1.0/1.0)
    assert FrameTimecode(timecode = 1000, fps = 60.0).get_seconds(), pytest.approx(1000/60.0)
    assert FrameTimecode(timecode = 1000000000, fps = 29.97).get_seconds(), pytest.approx(1000000000/29.97)

    assert FrameTimecode(timecode = 1.0, fps = 1.0).get_seconds(), pytest.approx(1.0)
    assert FrameTimecode(timecode = 1000.0, fps = 60.0).get_seconds(), pytest.approx(1000.0)
    assert FrameTimecode(timecode = 1000000000.0, fps = 29.97).get_seconds(), pytest.approx(1000000000.0)

    assert FrameTimecode(timecode = '00:00:02.0000', fps = 1).get_seconds(), pytest.approx(2.0)
    assert FrameTimecode(timecode = '00:00:00.5', fps = 10).get_seconds(), pytest.approx(0.5)
    assert FrameTimecode(timecode = '00:00:01', fps = 10).get_seconds(), pytest.approx(1.0)
    assert FrameTimecode(timecode = '00:01:00.000', fps = 1).get_seconds(), pytest.approx(60.0)

def test_get_timecode():
    ''' Test FrameTimecode get_timecode() method. '''
    assert FrameTimecode(timecode = 1.0, fps = 1.0).get_timecode() == '00:00:01.000'
    assert FrameTimecode(timecode = 60.117, fps = 60.0).get_timecode() == '00:01:00.117'
    assert FrameTimecode(timecode = 3600.234, fps = 29.97).get_timecode() == '01:00:00.234'

    assert FrameTimecode(timecode = '00:00:02.0000', fps = 1).get_timecode() == '00:00:02.000'
    assert FrameTimecode(timecode = '00:00:00.5', fps = 10).get_timecode() == '00:00:00.500'
    assert FrameTimecode(timecode = '00:00:01.501', fps = 10).get_timecode() == '00:00:01.500'
    assert FrameTimecode(timecode = '00:01:00.000', fps = 1).get_timecode() == '00:01:00.000'

def test_equality():
    ''' Test FrameTimecode equality (==, __eq__) operator. '''
    x = FrameTimecode(timecode = 1.0, fps = 10.0)
    assert x == x
    assert x == FrameTimecode(timecode = 1.0, fps = 10.0)
    assert not x != FrameTimecode(timecode = 1.0, fps = 10.0)
    assert x != FrameTimecode(timecode = 10.0, fps = 10.0)
    assert not x == FrameTimecode(timecode = 10.0, fps = 10.0)
    # Comparing FrameTimecodes with different framerates raises a TypeError.
    with pytest.raises(TypeError): x == FrameTimecode(timecode = 1.0, fps = 100.0)
    with pytest.raises(TypeError): x == FrameTimecode(timecode = 1.0, fps = 10.1)

    assert x == FrameTimecode(x)
    assert x == FrameTimecode(x, new_time = 1.0)
    assert x == FrameTimecode(x, new_time = 10)
    assert x == '00:00:01'
    assert x == '00:00:01.0'
    assert x == '00:00:01.00'
    assert x == '00:00:01.000'
    assert x == '00:00:01.0000'
    assert x == '00:00:01.00000'
    assert x == 10
    assert x == 1.0

    with pytest.raises(ValueError): x == '0x'
    with pytest.raises(ValueError): x == 'x00:00:00.000'
    with pytest.raises(TypeError): x == [0]
    with pytest.raises(TypeError): x == (0,)
    with pytest.raises(TypeError): x == [0, 1, 2, 3]
    with pytest.raises(TypeError): x == {0:0}

    assert FrameTimecode(timecode = '00:00:00.5', fps = 10) == '00:00:00.500'
    assert FrameTimecode(timecode = '00:00:01.500', fps = 10) == '00:00:01.500'
    assert FrameTimecode(timecode = '00:00:01.500', fps = 10) == '00:00:01.501'
    assert FrameTimecode(timecode = '00:00:01.500', fps = 10) == '00:00:01.502'
    assert FrameTimecode(timecode = '00:00:01.500', fps = 10) == '00:00:01.508'
    assert FrameTimecode(timecode = '00:00:01.500', fps = 10) == '00:00:01.509'
    assert FrameTimecode(timecode = '00:00:01.519', fps = 10) == '00:00:01.510'

def test_addition():
    ''' Test FrameTimecode addition (+/+=, __add__/__iadd__) operator. '''
    x = FrameTimecode(timecode = 1.0, fps = 10.0)
    assert x + 1 == FrameTimecode(timecode = 1.1, fps = 10.0)
    assert x + 1 == FrameTimecode(x, new_time = 1.1)
    assert x + 10 == 20
    assert x + 10 == 2.0

    assert x + 10 == '00:00:02.000'

    with pytest.raises(TypeError): FrameTimecode('00:00:02.000', fps = 20.0) == x + 10

def test_subtraction():
    ''' Test FrameTimecode subtraction (-/-=, __sub__) operator. '''
    x = FrameTimecode(timecode = 1.0, fps = 10.0)
    assert x - 1 == FrameTimecode(timecode = 0.9, fps = 10.0)
    assert x - 2 == FrameTimecode(x, new_time = 0.8)
    assert x - 10 == FrameTimecode(x, new_time = 0.0)
    assert x - 11 == FrameTimecode(x, new_time = 0.0)
    assert x - 100 == FrameTimecode(x, new_time = 0.0)

    assert x - 1.0 == FrameTimecode(x, new_time = 0.0)
    assert x - 100.0 == FrameTimecode(x, new_time = 0.0)

    assert x - 1 == FrameTimecode(timecode = 0.9, fps = 10.0)

    with pytest.raises(TypeError): FrameTimecode('00:00:02.000', fps = 20.0) == x - 10

