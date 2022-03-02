# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the above pages for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
""" ``scenedetect.cli.config`` Module """

import logging
import os.path
from configparser import ConfigParser
from typing import Dict, List, Optional, Tuple, Union

from appdirs import user_config_dir

from scenedetect.frame_timecode import FrameTimecode


class TimecodeValue:

    def __init__(self, value: Union[int, str]):
        # Ensure value is a valid timecode.
        FrameTimecode(timecode=value, fps=100.0)
        self.value = value

    def __repr__(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)


ConfigValue = Union[bool, int, float, str, TimecodeValue]
ConfigDict = Dict[str, Dict[str, ConfigValue]]

_CONFIG_FILE_NAME = 'scenedetect.cfg'
_CONFIG_FILE_DIR = user_config_dir("PySceneDetect", False)

CONFIG_FILE_PATH = os.path.join(_CONFIG_FILE_DIR, _CONFIG_FILE_NAME)

CONFIG_MAP: ConfigDict = {
    'global': {
        'verbosity': 'info',
        'min-scene-len': TimecodeValue('0.6s'),
        'downscale': 0,
        'frame-skip': 0,
        'backend': 'opencv',
        'drop-short-scenes': False,
        'output': '',
    },
    'detect-content': {
        'luma-only': False,                                                # NOT DONE
        'threshold': 27,                                                   # NOT DONE
    },
    'split-video': {
        'copy': False,                                                     # NOT DONE
        'filename': '$VIDEO_NAME-Scene-$SCENE_NUMBER',                     # NOT DONE
        'high-quality': False,                                             # NOT DONE
        'mkvmerge': False,                                                 # NOT DONE
        'output': '/usr/tmp/encoded',                                      # NOT DONE
        'override-args': "-c:v libx264 -preset veryfast -crf 22 -c:a aac", # NOT DONE
        'preset': 'veryfast',                                              # NOT DONE
        'quiet': False,                                                    # NOT DONE
        'rate-factor': 22,                                                 # NOT DONE
    },
}
"""Mapping of valid configuration file parameters and their default values."""

# We use a list instead of a set to preserve order when generating error contexts.
# TODO: This should probably be a type like TimecodeValue rather than a separate constant.
CHOICE_MAP: Dict[str, Dict[str, List[str]]] = {
    'global': {
        'backend': ['opencv', 'pyav'],
        'verbosity': ['debug', 'info', 'warning', 'error', 'none'],
    },
}
"""Mapping of options which can only be of a particular set of values."""


def _validate_structure(config) -> List[str]:
    errors: List[str] = []
    for section in config.sections():
        if not section in CONFIG_MAP.keys():
            errors.append('Error: Unknown section: %s' % (section))
            continue
        for (option_name, _) in config.items(section):
            if not option_name in CONFIG_MAP[section].keys():
                errors.append('Error: Unknown %s option: %s' % (section, option_name))
    return errors


def _parse_config(config) -> Tuple[ConfigDict, List[str]]:
    out_map: ConfigDict = {}
    errors: List[str] = []
    for command in CONFIG_MAP:
        out_map[command] = {}
        for option in CONFIG_MAP[command]:
            if command in config and option in config[command]:
                try:
                    value_type = None
                    if isinstance(CONFIG_MAP[command][option], bool):
                        value_type = 'yes/no value'
                        out_map[command][option] = config.getboolean(command, option)
                    elif isinstance(CONFIG_MAP[command][option], int):
                        value_type = 'integer'
                        out_map[command][option] = config.getint(command, option)
                    elif isinstance(CONFIG_MAP[command][option], float):
                        value_type = 'number'
                        out_map[command][option] = config.getfloat(command, option)
                except ValueError as _:
                    errors.append('Invalid [%s] value for %s: %s is not a valid %s.' %
                                  (command, option, config.get(command, option), value_type))
                if value_type:
                    continue

                if isinstance(CONFIG_MAP[command][option], TimecodeValue):
                    value = config.get(command, option).replace('\n', ' ').strip()
                    try:
                        new_value = TimecodeValue(value)
                        out_map[command][option] = new_value
                    except ValueError:
                        errors.append(
                            'Invalid [%s] value for %s: %s is not a valid timecode. Timecodes'
                            ' must be in frames (1234), seconds (123.4s), or HH:MM:SS'
                            ' (00:02:03.400).' % (command, option, value))
                    continue

                # If we didn't process the value as a given type, handle it as a string. We also
                # replace newlines with spaces, and strip any remaining leading/trailing whitespace.
                if value_type is None:
                    config_value = config.get(command, option).replace('\n', ' ').strip()
                    if command in CHOICE_MAP and option in CHOICE_MAP[command]:
                        if config_value.lower() not in CHOICE_MAP[command][option]:
                            errors.append('Invalid [%s] value for %s: %s. Must be one of: %s.' %
                                          (command, option, config.get(command, option), ', '.join(
                                              choice for choice in CHOICE_MAP[command][option])))
                            continue
                    out_map[command][option] = config_value

    return (out_map, errors)


class ConfigLoadFailure(Exception):

    def __init__(self, init_log: Tuple[int, str]):
        super().__init__()
        self.init_log = init_log


class ConfigRegistry:

    def __init__(self, path: Optional[str] = None):
        self._config: ConfigDict = {} # Options set in the loaded config file.
        self._init_log: List[Tuple[int, str]] = []
        if self._load_from_disk(path) is False and path is not None:
            raise ConfigLoadFailure(self._init_log)

    @property
    def config_dict(self) -> ConfigDict:
        return self._config

    def get_init_log(self):
        """Get initialization log. Consumes the log, so subsequent calls will return None."""
        init_log = self._init_log
        self._init_log = []
        return init_log

    def _log(self, log_level, log_str):
        self._init_log.append((log_level, log_str))

    def _load_from_disk(self, path=None) -> bool:
        """Tries to find a configuration file and load it."""
        config = ConfigParser()
        config_file_path = path if path is not None else CONFIG_FILE_PATH
        result = config.read(config_file_path)
        if not result:
            if not os.path.exists(config_file_path):
                self._log(logging.DEBUG,
                          "User config file not found (path: %s)" % (config_file_path))
            else:
                self._log(logging.ERROR, "Failed to read config file.")
            return False
        self._log(logging.INFO, "Loading config from file:\n%s" % (os.path.abspath(result[0])))
        errors = _validate_structure(config)
        if not errors:
            self._config, errors = _parse_config(config)
        if errors:
            for log_str in errors:
                self._log(logging.ERROR, log_str)
            return False
        return True

    def is_default(self, command: str, option: str) -> bool:
        return not (command in self._config and option in self._config[command])

    def get_value(self, command: str, option: str, override: Optional[ConfigValue] = None) -> ConfigValue:
        """Get the current setting or default value of the specified command option."""
        assert command in CONFIG_MAP and option in CONFIG_MAP[command]
        if override is not None:
            return override
        if command in self._config and option in self._config[command]:
            return self._config[command][option]
        return CONFIG_MAP[command][option]

    def get_help_string(self, command: str, option: str) -> str:
        """Get a string to specify for the help text indicating the current command option value,
        if set, or the default.

        Arguments:
            command: A command name or, "global" for global options.
            option: Command-line option to set within `command`.
            show_flag_default: """
        assert command in CONFIG_MAP and option in CONFIG_MAP[command]
        is_flag = isinstance(CONFIG_MAP[command][option], bool)
        if command in self._config and option in self._config[command]:
            if is_flag:
                value_str = 'on' if self._config[command][option] else 'off'
            else:
                value_str = str(self._config[command][option])
            return ' [setting: %s]' % (value_str)
        # Flags do not take values.
        if is_flag:
            return ''
        return ' [default: %s]' % (str(CONFIG_MAP[command][option]))
