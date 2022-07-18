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

This moduke contains all platform/library specific compatibility fixes, as well as some utility
functions to handle logging and invoking external commands.
"""

import logging
import os
import os.path
import subprocess
import sys
from typing import AnyStr, Dict, List, Optional, Union

import cv2

##
## tqdm Library
##


class FakeTqdmObject:
    """Provides a no-op tqdm-like object."""

    # pylint: disable=unused-argument
    def __init__(self, **kawrgs):
        """No-op."""

    def update(self, _):
        """No-op."""

    def close(self):
        """No-op."""

    def set_description(self, _):
        """No-op."""

    # pylint: enable=unused-argument


class FakeTqdmLoggingRedirect:
    """Provides a no-op tqdm context manager for redirecting log messages."""

    # pylint: disable=redefined-builtin,unused-argument
    def __init__(self, **kawrgs):
        """No-op."""

    def __enter__(self):
        """No-op."""

    def __exit__(self, type, value, traceback):
        """No-op."""

    # pylint: enable=redefined-builtin,unused-argument


# Try to import tqdm and the logging redirect, otherwise provide fake implementations..
try:
    # pylint: disable=unused-import
    from tqdm import tqdm
    from tqdm.contrib.logging import logging_redirect_tqdm
    # pylint: enable=unused-import
except ModuleNotFoundError:
    # pylint: disable=invalid-name
    tqdm = FakeTqdmObject
    logging_redirect_tqdm = FakeTqdmLoggingRedirect
    # pylint: enable=invalid-name

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

    If `include_extension` is False, the result will always be a str.

    E.g. /tmp/foo.bar -> foo"""
    file_name = os.path.basename(file_path)
    if not include_extension:
        file_name = str(file_name)
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


def get_ffmpeg_path() -> Optional[str]:
    """Get path to ffmpeg if available on the current system, or None if not available."""
    # Prefer using ffmpeg if it already exists in PATH.
    try:
        subprocess.call(['ffmpeg', '-v', 'quiet'])
        return 'ffmpeg'
    except OSError:
        pass
    # Failed to invoke ffmpeg from PATH, see if we have a copy from imageio_ffmpeg.
    try:
        # pylint: disable=import-outside-toplevel
        from imageio_ffmpeg import get_ffmpeg_exe
        subprocess.call([get_ffmpeg_exe(), '-v', 'quiet'])
        return get_ffmpeg_exe()
    # Gracefully handle case where imageio_ffmpeg is not available.
    except ModuleNotFoundError:
        pass
    # Handle case where path might be wrong/non-existent.
    except OSError:
        pass
    # get_ffmpeg_exe may throw a RuntimeError if the executable is not available.
    except RuntimeError:
        pass
    return None
