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
"""``scenedetect.cli.config`` Module

Handles loading configuration files from disk and validating each section. Only validation
of the config file schema and data types are performed. Constants/defaults are also defined
here where possible and re-used by the CLI so that there is one source of truth.
"""

import logging
import os.path
from configparser import ConfigParser
from typing import AnyStr, Dict, List, Optional, Tuple, Union

from appdirs import user_config_dir

from scenedetect.frame_timecode import FrameTimecode


class TimecodeValue:

    def __init__(self, value: Union[int, str]):
        self.value = value
        # Ensure value is a valid timecode.
        FrameTimecode(timecode=value, fps=100.0)

    def __repr__(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)


class RangeValue:

    def __init__(self, value: Union[int, float], min_val: Union[int, float], max_val: Union[int,
                                                                                            float]):
        self.value = value
        if value < min_val or value > max_val:
            # min and max are inclusive.
            raise ValueError()
        self.min_val = min_val
        self.max_val = max_val

    def __repr__(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)


ConfigValue = Union[bool, int, float, str]
ConfigDict = Dict[str, Dict[str, ConfigValue]]

_CONFIG_FILE_NAME: AnyStr = 'scenedetect.cfg'
_CONFIG_FILE_DIR: AnyStr = user_config_dir("PySceneDetect", False)

CONFIG_FILE_PATH: AnyStr = os.path.join(_CONFIG_FILE_DIR, _CONFIG_FILE_NAME)

DEFAULT_BACKENDS = ['pyav', 'opencv']


CONFIG_MAP: ConfigDict = {
    'detect-adaptive': {
        'frame-window': 2,
        'luma-only': False,
        'min-delta-hsv': RangeValue(15.0, min_val=0.0, max_val=255.0),
        'min-scene-len': TimecodeValue(0),
        'threshold': RangeValue(3.0, min_val=0.0, max_val=255.0),
    },
    'detect-content': {
        'luma-only': False,
        'min-scene-len': TimecodeValue(0),
        'threshold': RangeValue(27.0, min_val=0.0, max_val=255.0),
    },
    'detect-threshold': {
        'add-last-scene': True,
        'fade-bias': RangeValue(0, min_val=-100.0, max_val=100.0),
        'min-scene-len': TimecodeValue(0),
        'threshold': RangeValue(12.0, min_val=0.0, max_val=255.0),
    },
    'export-html': {
        'filename': '$VIDEO_NAME-Scenes.html',
        'image-height': 0,
        'image-width': 0,
        'no-images': False,
    },
    'list-scenes': {
        'output': '',
        'filename': '$VIDEO_NAME-Scenes.csv',
        'no-output-file': False,
        'quiet': False,
        'skip-cuts': False,
    },
    'global': {
        'backend': 'try `pyav`, then `opencv`',
        'downscale': 0,
        'drop-short-scenes': False,
        'frame-skip': 0,
        'min-scene-len': TimecodeValue('0.6s'),
        'output': '',
        'verbosity': 'info',
    },
    'save-images': {
        'output': '',
        'filename': '$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER',
        'num-images': 3,
        'format': 'jpeg',
        'quality': RangeValue(95, 0, 100),
        'compression': RangeValue(3, 0, 9),
        'frame-margin': 1,
        'scale': 1.0,
        'height': 0,
        'width': 0,
    },
    'split-video': {
        'args': "-c:v libx264 -preset veryfast -crf 22 -c:a aac",
        'copy': False,
        'filename': '$VIDEO_NAME-Scene-$SCENE_NUMBER',
        'high-quality': False,
        'mkvmerge': False,
        'output': '/usr/tmp/encoded',
        'preset': 'veryfast',
        'quiet': False,
        'rate-factor': RangeValue(22, min_val=0, max_val=100),
    },
}
"""Mapping of valid configuration file parameters and their default values or placeholders.
The types of these values are used when decoding the configuration file. Valid choices for
certain string options are stored in `CHOICE_MAP`."""

CHOICE_MAP: Dict[str, Dict[str, List[str]]] = {
    'global': {
        'backend': ['opencv', 'pyav'],
        'verbosity': ['debug', 'info', 'warning', 'error', 'none'],
    },
    'split-video': {
        'preset': [
            'ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower',
            'veryslow'
        ],
    },
    'save-images': {
        'format': ['jpeg', 'png', 'webp'],
    }
}
"""Mapping of string options which can only be of a particular set of values. We use a list instead
of a set to preserve order when generating error contexts."""


def _validate_structure(config: ConfigParser) -> List[str]:
    """Validates the layout of the section/option mapping.

    Returns:
        List of any parsing errors in human-readable form.
    """
    errors: List[str] = []
    for section in config.sections():
        if not section in CONFIG_MAP.keys():
            errors.append('Unsupported config section: [%s]' % (section))
            continue
        for (option_name, _) in config.items(section):
            if not option_name in CONFIG_MAP[section].keys():
                errors.append('Unsupported config option in [%s]: %s' % (section, option_name))
    return errors


def _parse_config(config: ConfigParser) -> Tuple[ConfigDict, List[str]]:
    """Process the given configuration into a key-value mapping.

    Returns:
        Configuration mapping and list of any processing errors in human readable form.
    """
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
                        continue
                    elif isinstance(CONFIG_MAP[command][option], int):
                        value_type = 'integer'
                        out_map[command][option] = config.getint(command, option)
                        continue
                    elif isinstance(CONFIG_MAP[command][option], float):
                        value_type = 'number'
                        out_map[command][option] = config.getfloat(command, option)
                        continue
                except ValueError as _:
                    errors.append('Invalid [%s] value for %s: %s is not a valid %s.' %
                                  (command, option, config.get(command, option), value_type))
                    continue

                if isinstance(CONFIG_MAP[command][option], RangeValue):
                    default: RangeValue = CONFIG_MAP[command][option]
                    value = (
                        config.getint(command, option)
                        if isinstance(default.value, int) else config.getfloat(command, option))
                    try:
                        new_value = RangeValue(value, default.min_val, default.max_val)
                        out_map[command][option] = new_value
                    except ValueError:
                        errors.append(
                            'Invalid [%s] value for %s: %s. Value must be be between %s and %s.' %
                            ((command, option, value, default.min_val, default.max_val)))
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
                    continue

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
        """Current configuration options that are set for each command."""
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

    def get_value(self,
                  command: str,
                  option: str,
                  override: Optional[ConfigValue] = None,
                  ignore_default: bool = False) -> ConfigValue:
        """Get the current setting or default value of the specified command option."""
        assert command in CONFIG_MAP and option in CONFIG_MAP[command]
        if override is not None:
            return override
        if command in self._config and option in self._config[command]:
            value = self._config[command][option]
        else:
            value = CONFIG_MAP[command][option]
            if ignore_default:
                return None
        if isinstance(value, (TimecodeValue, RangeValue)):
            return value.value
        return value

    def get_help_string(self,
                        command: str,
                        option: str,
                        show_default: Optional[bool] = None) -> str:
        """Get a string to specify for the help text indicating the current command option value,
        if set, or the default.

        Arguments:
            command: A command name or, "global" for global options.
            option: Command-line option to set within `command`.
            show_default: Always show default value. Default is False for flag/bool values,
                True otherwise.
        """
        assert command in CONFIG_MAP and option in CONFIG_MAP[command]
        is_flag = isinstance(CONFIG_MAP[command][option], bool)
        if command in self._config and option in self._config[command]:
            if is_flag:
                value_str = 'on' if self._config[command][option] else 'off'
            else:
                value_str = str(self._config[command][option])
            return ' [setting: %s]' % (value_str)
        if show_default is False or (show_default is None and is_flag
                                     and CONFIG_MAP[command][option] is False):
            return ''
        return ' [default: %s]' % (str(CONFIG_MAP[command][option]))
