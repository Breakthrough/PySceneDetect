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
""" ``scenedetect.platform`` Module

This file contains all platform/library/OS-specific compatibility fixes,
intended to improve the systems that are able to run PySceneDetect, and allow
for maintaining backwards compatibility with existing libraries going forwards.
Other helper functions related to the detection of the appropriate dependency
DLLs on Windows and getting uniform line-terminating csv reader/writer objects
are also included in this module.
"""

import logging
import os
import os.path
import subprocess
import sys
from typing import AnyStr, Dict, List, Optional, Union

import cv2

##
## tqdm Library (`scenedetect.platform.tqdm`` will be tqdm object type or None)
##

# pylint: disable=unused-import
# pylint: disable=invalid-name
try:
    from tqdm import tqdm
except ModuleNotFoundError:
    tqdm = None
# pylint: enable=unused-import
# pylint: enable=invalid-name


# TODO: Move this into scenedetect.backends.opencv.
def get_aspect_ratio(cap: cv2.VideoCapture, epsilon: float = 0.01) -> float:
    """ Compatibility fix for OpenCV < v3.4.1 to get the aspect ratio
    of a video. For older versions, this function always returns 1.0.

    Arguments:
        cap: cv2.VideoCapture object. Must be opened and in valid state.
        epsilon: Used to compare numerator/denominator to zero.

    Returns:
        Display aspect ratio CAP_PROP_SAR_NUM / CAP_PROP_SAR_DEN, or 1.0 if using a version
        of OpenCV < 3.4.1.  Also returns 1.0 if for some reason the numerator/denominator
        returned is zero (can happen if the video was not opened correctly or is corrupt).
    """
    if not 'CAP_PROP_SAR_NUM' in dir(cv2):
        return 1.0
    num = cap.get(cv2.CAP_PROP_SAR_NUM)
    den = cap.get(cv2.CAP_PROP_SAR_DEN)
    # If numerator or denominator are zero, fall back to 1.0 aspect ratio.
    if abs(num) < epsilon or abs(den) < epsilon:
        return 1.0
    return num / den


##
## OpenCV imwrite Supported Image Types & Quality/Compression Parameters
##


# TODO: Move this into scene_manager.
def get_cv2_imwrite_params() -> Dict[str, Union[int, None]]:
    """ Get OpenCV imwrite Params: Returns a dict of supported image formats and
    their associated quality/compression parameter index, or None if that format
    is not supported.

    Returns:
        Dictionary of supported image formats/extensions ('jpg', 'png', etc...) mapped to the
        respective OpenCV quality or compression parameter as {'jpg': cv2.IMWRITE_JPEG_QUALITY,
        'png': cv2.IMWRITE_PNG_COMPRESSION, ...}. Parameter will be None if not found on the
        current system library (e.g. {'jpg': None}).
    """

    def _get_cv2_param(param_name: str) -> Union[int, None]:
        if param_name.startswith('CV_'):
            param_name = param_name[3:]
        try:
            return getattr(cv2, param_name)
        except AttributeError:
            return None

    return {
        'jpg': _get_cv2_param('IMWRITE_JPEG_QUALITY'),
        'png': _get_cv2_param('IMWRITE_PNG_COMPRESSION'),
        'webp': _get_cv2_param('IMWRITE_WEBP_QUALITY')
    }


##
## File I/O
##


def get_file_name(file_path: AnyStr, include_extension=True) -> AnyStr:
    """Return the file name that `file_path` refers to, optionally removing the extension.

    E.g. /tmp/foo.bar -> foo"""
    file_name = os.path.basename(file_path)
    if not include_extension:
        last_dot_pos = file_name.rfind('.')
        if last_dot_pos >= 0:
            file_name = file_name[:last_dot_pos]
    return file_name


def get_and_create_path(file_path: AnyStr, output_directory: Optional[AnyStr] = None) -> AnyStr:
    """ Get & Create Path: Gets and returns the full/absolute path to file_path
    in the specified output_directory if set, creating any required directories
    along the way.

    If file_path is already an absolute path, then output_directory is ignored.

    Arguments:
        file_path: File name to get path for.  If file_path is an absolute
            path (e.g. starts at a drive/root), no modification of the path
            is performed, only ensuring that all output directories are created.
        output_dir: An optional output directory to override the
            directory of file_path if it is relative to the working directory.

    Returns:
        Full path to output file suitable for writing.

    """
    # If an output directory is defined and the file path is a relative path, open
    # the file handle in the output directory instead of the working directory.
    if output_directory is not None and not os.path.isabs(file_path):
        file_path = os.path.join(output_directory, file_path)
    # Now that file_path is an absolute path, let's make sure all the directories
    # exist for us to start writing files there.
    os.makedirs(os.path.split(os.path.abspath(file_path))[0], exist_ok=True)
    return file_path


##
## Logging
##


def init_logger(log_level: int = logging.INFO,
                show_stdout: bool = False,
                log_file: Optional[str] = None):
    """Initializes logging for PySceneDetect. The logger instance used is named 'pyscenedetect'.
    By default the logger has no handlers to suppress output. All existing log handlers are replaced
    every time this function is invoked.

    Arguments:
        log_level: Verbosity of log messages. Should be one of [logging.INFO, logging.DEBUG,
            logging.WARNING, logging.ERROR, logging.CRITICAL].
        show_stdout: If True, add handler to show log messages on stdout (default: False).
        log_file: If set, add handler to dump log messages to given file path.
    """
    # Format of log messages depends on verbosity.
    format_str = '[PySceneDetect] %(message)s'
    if log_level == logging.DEBUG:
        format_str = '%(levelname)s: %(module)s.%(funcName)s(): %(message)s'
    # Get the named logger and remove any existing handlers.
    logger_instance = logging.getLogger('pyscenedetect')
    logger_instance.handlers = []
    logger_instance.setLevel(log_level)
    # Add stdout handler if required.
    if show_stdout:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter(fmt=format_str))
        logger_instance.addHandler(handler)
    # Add file handler if required.
    if log_file:
        log_file = get_and_create_path(log_file)
        handler = logging.FileHandler(log_file)
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter(fmt=format_str))
        logger_instance.addHandler(handler)


init_logger()

##
## Running External Commands
##


class CommandTooLong(Exception):
    """Raised if the length of a command line argument exceeds the limit allowed on Windows."""


def invoke_command(args: List[str]) -> int:
    """ Same as calling Python's subprocess.call() method, but explicitly
    raises a different exception when the command length is too long.

    See https://github.com/Breakthrough/PySceneDetect/issues/164 for details.

    Arguments:
        args: List of strings to pass to subprocess.call().

    Returns:
        Return code of command.

    Raises:
        CommandTooLong: `args` exceeds built in command line length limit on Windows.
    """
    try:
        return subprocess.call(args)
    except OSError as err:
        if os.name != 'nt':
            raise
        exception_string = str(err)
        # Error 206: The filename or extension is too long
        # Error 87:  The parameter is incorrect
        to_match = ('206', '87')
        if any([x in exception_string for x in to_match]):
            raise CommandTooLong() from err
        raise
