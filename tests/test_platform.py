#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2020 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect scenedetect.platform Tests

This file includes unit tests for the scenedetect.platform module, containing
all platform/library/OS-specific compatibility fixes.
"""

import platform

import pytest

from scenedetect.platform import CommandTooLong, get_file_name, invoke_command, is_url


def test_invoke_command():
    """Ensures the function exists and is callable without throwing
    an exception."""
    if platform.system() == "Windows":
        invoke_command(["cmd"])
    else:
        invoke_command(["echo"])


def test_long_command():
    """[Windows Only] Ensures that a command string too large to be handled
    is translated to the correct exception for error handling.
    """
    if platform.system() == "Windows":
        with pytest.raises(CommandTooLong):
            invoke_command(["x" * 2**15])


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/tmp/foo.bar", "foo"),
        ("foo.bar", "foo"),
        ("foo", "foo"),
        ("https://example.com/videos/clip.mp4", "clip"),
        # Query strings and fragments are not part of the name, even if they contain a "." or "/".
        ("https://example.com/videos/clip.mp4?token=1.2&dir=a/b", "clip"),
        ("https://example.com/videos/clip.mp4#t=10", "clip"),
        ("https://example.com/videos/clip.mp4/", "clip"),
        ("https://example.com/videos/my%20clip.mp4", "my clip"),
        ("rtsp://user:pass@192.168.0.1:554/live/stream1", "stream1"),
        # No path component: fall back to the host, which must stay a valid file name.
        ("https://example.com", "example.com"),
        ("https://example.com/", "example.com"),
        ("rtsp://192.168.0.1:554", "192.168.0.1_554"),
        ("rtsp://user:pass@192.168.0.1:554", "192.168.0.1_554"),
    ],
)
def test_get_file_name_without_extension(path: str, expected: str):
    assert get_file_name(path, include_extension=False) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/tmp/foo.bar", "foo.bar"),
        ("https://example.com/videos/clip.mp4?token=1", "clip.mp4"),
        ("https://example.com/", "example.com"),
    ],
)
def test_get_file_name_with_extension(path: str, expected: str):
    assert get_file_name(path, include_extension=True) == expected


def test_is_url():
    assert is_url("https://example.com/clip.mp4")
    assert is_url("rtsp://192.168.0.1:554/live")
    assert not is_url("/tmp/clip.mp4")
    assert not is_url(r"C:\videos\clip.mp4")
    assert not is_url("img_%04d.jpg")
