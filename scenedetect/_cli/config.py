#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Handles loading configuration files from disk and validating each section. Only validation of the
config file schema and data types are performed. Constants/defaults are also defined here where
possible and re-used by the CLI so that there is one source of truth.
"""

import logging
import os
import os.path
import typing as ty
from abc import ABC, abstractmethod
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from enum import Enum

from platformdirs import user_config_dir

from scenedetect.common import FrameTimecode
from scenedetect.detector import FlashFilter
from scenedetect.detectors import ContentDetector
from scenedetect.scene_manager import Interpolation
from scenedetect.video_splitter import DEFAULT_FFMPEG_ARGS

PYAV_THREADING_MODES = ["NONE", "SLICE", "FRAME", "AUTO"]

LogMessage = ty.Tuple[int, str]


class OptionParseFailure(Exception):
    """Raised when a value provided in a user config file fails validation."""

    def __init__(self, error):
        super().__init__()
        self.error = error


class ValidatedValue(ABC):
    """Used to represent configuration values that must be validated against constraints."""

    @property
    @abstractmethod
    def value(self) -> ty.Any:
        """Get the value after validation."""
        ...

    @staticmethod
    @abstractmethod
    def from_config(config_value: str, default: "ValidatedValue") -> "ValidatedValue":
        """Validate and get the user-specified configuration option.

        Raises:
            OptionParseFailure: Value from config file did not meet validation constraints.
        """
        ...

    def __repr__(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)


class TimecodeValue(ValidatedValue):
    """Validator for timecode values in seconds (100.0), frames (100), or HH:MM:SS.

    Stores value in original representation."""

    def __init__(self, value: ty.Union[int, float, str]):
        # Ensure value is a valid timecode.
        FrameTimecode(timecode=value, fps=100.0)
        self._value = value

    @property
    def value(self) -> ty.Union[int, float, str]:
        return self._value

    @staticmethod
    def from_config(config_value: str, default: "TimecodeValue") -> "TimecodeValue":
        try:
            return TimecodeValue(config_value)
        except ValueError as ex:
            raise OptionParseFailure(
                "Timecodes must be in seconds (100.0), frames (100), or HH:MM:SS."
            ) from ex


class RangeValue(ValidatedValue):
    """Validator for int/float ranges. `min_val` and `max_val` are inclusive."""

    def __init__(
        self,
        value: ty.Union[int, float],
        min_val: ty.Union[int, float],
        max_val: ty.Union[int, float],
    ):
        if value < min_val or value > max_val:
            # min and max are inclusive.
            raise ValueError()
        self._value = value
        self._min_val = min_val
        self._max_val = max_val

    @property
    def value(self) -> ty.Union[int, float]:
        return self._value

    @property
    def min_val(self) -> ty.Union[int, float]:
        """Minimum value of the range."""
        return self._min_val

    @property
    def max_val(self) -> ty.Union[int, float]:
        """Maximum value of the range."""
        return self._max_val

    @staticmethod
    def from_config(config_value: str, default: "RangeValue") -> "RangeValue":
        try:
            return RangeValue(
                value=int(config_value) if isinstance(default.value, int) else float(config_value),
                min_val=default.min_val,
                max_val=default.max_val,
            )
        except ValueError as ex:
            raise OptionParseFailure(
                "Value must be between %s and %s." % (default.min_val, default.max_val)
            ) from ex


class CropValue(ValidatedValue):
    """Validator for crop region defined as X0 Y0 X1 Y1."""

    _IGNORE_CHARS = [",", "/", "(", ")"]
    """Characters to ignore."""

    def __init__(self, value: ty.Optional[ty.Union[str, ty.Tuple[int, int, int, int]]] = None):
        if isinstance(value, CropValue) or value is None:
            self._crop = value
        else:
            crop = ()
            if isinstance(value, str):
                translation_table = str.maketrans(
                    {char: " " for char in ScoreWeightsValue._IGNORE_CHARS}
                )
                values = value.translate(translation_table).split()
                crop = tuple(int(val) for val in values)
            elif isinstance(value, tuple):
                crop = value
            if not len(crop) == 4:
                raise ValueError("Crop region must be four numbers of the form X0 Y0 X1 Y1!")
            if any(coordinate < 0 for coordinate in crop):
                raise ValueError("Crop coordinates must be >= 0")
            (x0, y0, x1, y1) = crop
            self._crop = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    @property
    def value(self) -> ty.Tuple[int, int, int, int]:
        return self._crop

    def __str__(self) -> str:
        return "[%d, %d], [%d, %d]" % self.value

    @staticmethod
    def from_config(config_value: str, default: "CropValue") -> "CropValue":
        try:
            return CropValue(config_value)
        except ValueError as ex:
            raise OptionParseFailure(f"{ex}") from ex


class ScoreWeightsValue(ValidatedValue):
    """Validator for score weight values (currently a tuple of four numbers)."""

    _IGNORE_CHARS = [",", "/", "(", ")"]
    """Characters to ignore."""

    def __init__(self, value: ty.Union[str, ContentDetector.Components]):
        if isinstance(value, ContentDetector.Components):
            self._value = value
        else:
            translation_table = str.maketrans(
                {char: " " for char in ScoreWeightsValue._IGNORE_CHARS}
            )
            values = value.translate(translation_table).split()
            if not len(values) == 4:
                raise ValueError("Score weights must be specified as four numbers!")
            self._value = ContentDetector.Components(*(float(val) for val in values))

    @property
    def value(self) -> ContentDetector.Components:
        return self._value

    def __str__(self) -> str:
        return "%.3f, %.3f, %.3f, %.3f" % self.value

    @staticmethod
    def from_config(config_value: str, default: "ScoreWeightsValue") -> "ScoreWeightsValue":
        try:
            return ScoreWeightsValue(config_value)
        except ValueError as ex:
            raise OptionParseFailure(
                "Score weights must be specified as four numbers in the form (H,S,L,E),"
                " e.g. (0.9, 0.2, 2.0, 0.5). Commas/brackets/slashes are ignored."
            ) from ex


class KernelSizeValue(ValidatedValue):
    """Validator for kernel sizes (odd integer > 1, or -1 for auto size)."""

    def __init__(self, value: int):
        if value == -1:
            # Downscale factor of -1 maps to None internally for auto downscale.
            value = None
        elif value < 0:
            # Disallow other negative values.
            raise ValueError()
        elif value % 2 == 0:
            # Disallow even values.
            raise ValueError()
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    def __str__(self) -> str:
        if self.value is None:
            return "auto"
        return str(self.value)

    @staticmethod
    def from_config(config_value: str, default: "KernelSizeValue") -> "KernelSizeValue":
        try:
            return KernelSizeValue(int(config_value))
        except ValueError as ex:
            raise OptionParseFailure(
                "Value must be an odd integer greater than 1, or set to -1 for auto kernel size."
            ) from ex


class EscapedString(ValidatedValue):
    """Strings that can contain escape sequences, e.g. the literal \n."""

    def __init__(self, value: str, length_limit: int = 0):
        self._value = value.encode("utf-8").decode("unicode_escape")
        if length_limit and len(self._value) > length_limit:
            raise OptionParseFailure(f"Value must be no longer than {length_limit} characters.")

    @property
    def value(self) -> str:
        """Get the value after validation."""
        return self._value

    @staticmethod
    def from_config(
        config_value: str, default: "EscapedString", length_limit: int = 0
    ) -> "EscapedString":
        try:
            return EscapedString(config_value, length_limit)
        except (UnicodeDecodeError, UnicodeEncodeError) as ex:
            raise OptionParseFailure(
                "Value must be valid UTF-8 string with escape characters."
            ) from ex


class EscapedChar(EscapedString):
    """Strings that can contain escape sequences but can be a maximum of 1 character in length."""

    def __init__(self, value: str):
        super().__init__(value, length_limit=1)

    @staticmethod
    def from_config(config_value: str, default: "EscapedString") -> "EscapedChar":
        return EscapedString.from_config(config_value, default, length_limit=1)


class TimecodeFormat(Enum):
    """Format to display timecodes."""

    FRAMES = 0
    """Print timecodes as exact frame number."""
    TIMECODE = 1
    """Print timecodes in format HH:MM:SS.nnn."""
    SECONDS = 2
    """Print timecodes in seconds SSS.sss."""

    def format(self, timecode: FrameTimecode) -> str:
        if self == TimecodeFormat.FRAMES:
            return str(timecode.get_frames())
        if self == TimecodeFormat.TIMECODE:
            return timecode.get_timecode()
        if self == TimecodeFormat.SECONDS:
            return "%.3f" % timecode.get_seconds()
        raise RuntimeError("Unhandled format specifier.")


class XmlFormat(Enum):
    """Format to use with the `save-xml` command."""

    FCPX = 0
    """Final Cut Pro X XML Format"""
    FCP = 1
    """Final Cut Pro 7 XML Format"""


ConfigValue = ty.Union[bool, int, float, str]
ConfigDict = ty.Dict[str, ty.Dict[str, ConfigValue]]

_CONFIG_FILE_NAME: ty.AnyStr = "scenedetect.cfg"
_CONFIG_FILE_DIR: ty.AnyStr = user_config_dir("PySceneDetect", False)
_PLACEHOLDER = 0  # Placeholder for image quality default, as the value depends on output format

CONFIG_FILE_PATH: ty.AnyStr = os.path.join(_CONFIG_FILE_DIR, _CONFIG_FILE_NAME)
DEFAULT_JPG_QUALITY = 95
DEFAULT_WEBP_QUALITY = 100

# TODO(v0.7): Remove [detect-adaptive] min-delta-hsv
CONFIG_MAP: ConfigDict = {
    "backend-opencv": {
        "max-decode-attempts": 5,
    },
    "backend-pyav": {
        "suppress-output": False,
        "threading-mode": "auto",
    },
    "detect-adaptive": {
        "frame-window": 2,
        "kernel-size": KernelSizeValue(-1),
        "luma-only": False,
        "min-content-val": RangeValue(15.0, min_val=0.0, max_val=255.0),
        "min-delta-hsv": RangeValue(15.0, min_val=0.0, max_val=255.0),
        "min-scene-len": TimecodeValue(0),
        "threshold": RangeValue(3.0, min_val=0.0, max_val=255.0),
        "weights": ScoreWeightsValue(ContentDetector.DEFAULT_COMPONENT_WEIGHTS),
    },
    "detect-content": {
        "filter-mode": FlashFilter.Mode.MERGE,
        "kernel-size": KernelSizeValue(-1),
        "luma-only": False,
        "min-scene-len": TimecodeValue(0),
        "threshold": RangeValue(27.0, min_val=0.0, max_val=255.0),
        "weights": ScoreWeightsValue(ContentDetector.DEFAULT_COMPONENT_WEIGHTS),
    },
    "detect-hash": {
        "min-scene-len": TimecodeValue(0),
        "lowpass": RangeValue(2, min_val=1, max_val=256),
        "size": RangeValue(16, min_val=1, max_val=256),
        "threshold": RangeValue(0.395, min_val=0.0, max_val=1.0),
    },
    "detect-hist": {
        "min-scene-len": TimecodeValue(0),
        "threshold": RangeValue(0.05, min_val=0.0, max_val=1.0),
        "bins": RangeValue(256, min_val=1, max_val=256),
    },
    "detect-threshold": {
        "add-last-scene": True,
        "fade-bias": RangeValue(0, min_val=-100.0, max_val=100.0),
        "min-scene-len": TimecodeValue(0),
        "threshold": RangeValue(12.0, min_val=0.0, max_val=255.0),
    },
    "load-scenes": {
        "start-col-name": "Start Frame",
    },
    "list-scenes": {
        "cut-format": TimecodeFormat.TIMECODE,
        "col-separator": EscapedChar(","),
        "display-cuts": True,
        "display-scenes": True,
        "filename": "$VIDEO_NAME-Scenes.csv",
        "output": None,
        "row-separator": EscapedString("\n"),
        "no-output-file": False,
        "quiet": False,
        "skip-cuts": False,
    },
    "global": {
        "backend": "opencv",
        "crop": CropValue(),
        "default-detector": "detect-adaptive",
        "downscale": 0,
        "downscale-method": Interpolation.LINEAR,
        "drop-short-scenes": False,
        "frame-skip": 0,
        "merge-last-scene": False,
        "min-scene-len": TimecodeValue("0.6s"),
        "output": None,
        "verbosity": "info",
    },
    "save-edl": {
        "filename": "$VIDEO_NAME.edl",
        "output": None,
        "reel": "AX",
        "title": "$VIDEO_NAME",
    },
    "save-html": {
        "filename": "$VIDEO_NAME-Scenes.html",
        "image-height": 0,
        "image-width": 0,
        "no-images": False,
        "show": False,
    },
    "save-images": {
        "compression": RangeValue(3, min_val=0, max_val=9),
        "filename": "$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER",
        "format": "jpeg",
        "frame-margin": 1,
        "height": 0,
        "num-images": 3,
        "output": None,
        "quality": RangeValue(_PLACEHOLDER, min_val=0, max_val=100),
        "scale": 1.0,
        "scale-method": Interpolation.LINEAR,
        "threading": True,
        "width": 0,
    },
    "save-otio": {
        "audio": True,
        "filename": "$VIDEO_NAME.otio",
        "name": "$VIDEO_NAME (PySceneDetect)",
        "output": None,
    },
    "save-qp": {
        "disable-shift": False,
        "filename": "$VIDEO_NAME.qp",
        "output": None,
    },
    "save-xml": {
        "format": XmlFormat.FCPX,
        "filename": "$VIDEO_NAME.xml",
        "output": None,
    },
    "split-video": {
        "args": DEFAULT_FFMPEG_ARGS,
        "copy": False,
        "filename": "$VIDEO_NAME-Scene-$SCENE_NUMBER",
        "high-quality": False,
        "mkvmerge": False,
        "output": None,
        "preset": "veryfast",
        "quiet": False,
        "rate-factor": RangeValue(22, min_val=0, max_val=100),
    },
}
"""Mapping of valid configuration file parameters and their default values or placeholders.
The types of these values are used when decoding the configuration file. Valid choices for
certain string options are stored in `CHOICE_MAP`."""

CHOICE_MAP: ty.Dict[str, ty.Dict[str, ty.List[str]]] = {
    "backend-pyav": {
        "threading_mode": [mode.lower() for mode in PYAV_THREADING_MODES],
    },
    "detect-content": {
        "filter-mode": [mode.name.lower() for mode in FlashFilter.Mode],
    },
    "global": {
        "backend": ["opencv", "pyav", "moviepy"],
        "default-detector": [
            "detect-adaptive",
            "detect-content",
            "detect-threshold",
            "detect-hash",
            "detect-hist",
        ],
        "downscale-method": [value.name.lower() for value in Interpolation],
        "verbosity": ["debug", "info", "warning", "error", "none"],
    },
    "list-scenes": {
        "cut-format": [value.name.lower() for value in TimecodeFormat],
    },
    "save-images": {
        "format": ["jpeg", "png", "webp"],
        "scale-method": [value.name.lower() for value in Interpolation],
    },
    "save-xml": {
        "format": [value.name.lower() for value in XmlFormat],
    },
    "split-video": {
        "preset": [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ],
    },
}
"""Mapping of string options which can only be of a particular set of values. We use a list instead
of a set to preserve order when generating error contexts. Values are case-insensitive, and must be
in lowercase in this map."""

DEPRECATED_COMMANDS: ty.Dict[str, str] = {"export-html": "save-html"}
"""Deprecated config file sections that have a 1:1 mapping to a new replacement."""


def _validate_structure(parser: ConfigParser) -> ty.Tuple[bool, ty.List[LogMessage]]:
    """Validates the layout of the section/option mapping. Returns a bool indicating if validation
    was successful, and a list of log messages for the init log."""
    logs: ty.List[LogMessage] = []
    success = True
    all_sections = set(parser.sections())
    for section in all_sections:
        section_name = section
        if section in DEPRECATED_COMMANDS:
            section = DEPRECATED_COMMANDS[section]
            logs.append(
                (
                    logging.WARNING,
                    f"WARNING: [{section_name}] is deprecated and will be removed!"
                    f"Use [{section}] instead.",
                )
            )
            # The parser already handled duplicate sections, but it doesn't know about deprecated
            # aliases. If there's a conflict, make sure we error out instead of warning.
            if section in all_sections:
                success = False
                logs.append(
                    (
                        logging.ERROR,
                        f"[{section_name}] conflicts with [{section}], only specify one.",
                    )
                )
                continue
        elif section not in CONFIG_MAP.keys():
            success = False
            logs.append((logging.ERROR, f"Unsupported config section: [{section_name}]"))
            continue
        for option_name, _ in parser.items(section_name):
            if option_name not in CONFIG_MAP[section].keys():
                success = False
                logs.append(
                    (
                        logging.ERROR,
                        f"Unsupported config option in [{section_name}]: [{option_name}]",
                    )
                )
    return (success, logs)


def _parse_config(parser: ConfigParser) -> ty.Tuple[ty.Optional[ConfigDict], ty.List[LogMessage]]:
    """Process the given configuration into a key-value mapping. Returns a tuple of the config
    dict itself (or None on failure), and a list of log messages during parsing."""
    (success, logs) = _validate_structure(parser)
    if not success:
        return (None, logs)
    config: ConfigDict = {}
    success = True
    # Re-map deprecated config sections to their replacements. Structure validation above should
    # ensure no conflicts between the two.
    for deprecated_command in DEPRECATED_COMMANDS:
        if deprecated_command in parser:
            replacement = DEPRECATED_COMMANDS[deprecated_command]
            parser[replacement] = parser[deprecated_command]
            del parser[deprecated_command]
    for command in CONFIG_MAP:
        config[command] = {}
        for option in CONFIG_MAP[command]:
            if command in parser and option in parser[command]:
                try:
                    value_type = None
                    if isinstance(CONFIG_MAP[command][option], bool):
                        value_type = "yes/no value"
                        config[command][option] = parser.getboolean(command, option)
                        continue
                    elif isinstance(CONFIG_MAP[command][option], int):
                        value_type = "integer"
                        config[command][option] = parser.getint(command, option)
                        continue
                    elif isinstance(CONFIG_MAP[command][option], float):
                        value_type = "number"
                        config[command][option] = parser.getfloat(command, option)
                        continue
                    elif isinstance(CONFIG_MAP[command][option], Enum):
                        config_value = (
                            parser.get(command, option).replace("\n", " ").strip().upper()
                        )
                        try:
                            parsed = CONFIG_MAP[command][option].__class__[config_value]
                            config[command][option] = parsed
                        except TypeError:
                            success = False
                            logs.append(
                                (
                                    logging.ERROR,
                                    "Invalid value for [%s] option %s': %s. Must be one of: %s."
                                    % (
                                        command,
                                        option,
                                        parser.get(command, option),
                                        ", ".join(
                                            str(choice) for choice in CHOICE_MAP[command][option]
                                        ),
                                    ),
                                )
                            )
                        continue

                except ValueError as _:
                    success = False
                    logs.append(
                        (
                            logging.ERROR,
                            "Invalid value for [%s] option '%s': %s is not a valid %s."
                            % (command, option, parser.get(command, option), value_type),
                        )
                    )
                    continue

                # Handle custom validation types.
                config_value = parser.get(command, option)
                default = CONFIG_MAP[command][option]
                option_type = type(default)
                if issubclass(option_type, ValidatedValue):
                    try:
                        config[command][option] = option_type.from_config(
                            config_value=config_value, default=default
                        )
                    except OptionParseFailure as ex:
                        success = False
                        logs.append(
                            (
                                logging.ERROR,
                                "Invalid value for [%s] option '%s':  %s\nError: %s"
                                % (command, option, config_value, ex.error),
                            )
                        )
                    continue

                # If we didn't process the value as a given type, handle it as a string. We also
                # replace newlines with spaces, and strip any remaining leading/trailing whitespace.
                if value_type is None:
                    config_value = parser.get(command, option).replace("\n", " ").strip()
                    if command in CHOICE_MAP and option in CHOICE_MAP[command]:
                        if config_value.lower() not in CHOICE_MAP[command][option]:
                            success = False
                            logs.append(
                                (
                                    logging.ERROR,
                                    "Invalid value for [%s] option '%s': %s. Must be one of: %s."
                                    % (
                                        command,
                                        option,
                                        parser.get(command, option),
                                        ", ".join(choice for choice in CHOICE_MAP[command][option]),
                                    ),
                                )
                            )
                            continue
                    config[command][option] = config_value
                    continue

    if not success:
        return (None, logs)
    return (config, logs)


class ConfigLoadFailure(Exception):
    """Raised when a user-specified configuration file fails to be loaded or validated."""

    def __init__(self, init_log: ty.Tuple[int, str], reason: ty.Optional[Exception] = None):
        super().__init__()
        self.init_log = init_log
        self.reason = reason


class ConfigRegistry:
    def __init__(self, path: ty.Optional[str] = None, throw_exception: bool = True):
        self._config: ConfigDict = {}  # Options set in the loaded config file.
        self._init_log: ty.List[ty.Tuple[int, str]] = []
        self._initialized = False

        try:
            self._load_from_disk(path)
            self._initialized = True

        except ConfigLoadFailure as ex:
            if throw_exception:
                raise
            # If we fail to load the user config file, ensure the object is flagged as
            # uninitialized, and log the error so it can be dealt with if necessary.
            self._init_log = ex.init_log
            if ex.reason is not None:
                self._init_log += [
                    (logging.ERROR, "Error: %s" % str(ex.reason).replace("\t", "  ")),
                ]
            self._initialized = False

    @property
    def config_dict(self) -> ConfigDict:
        """Current configuration options that are set for each command."""
        return self._config

    @property
    def initialized(self) -> bool:
        """True if the ConfigRegistry was constructed without errors, False otherwise."""
        return self._initialized

    def get_init_log(self):
        """Get initialization log. Consumes the log, so subsequent calls will return None."""
        init_log = self._init_log
        self._init_log = []
        return init_log

    def _log(self, log_level, log_str):
        self._init_log.append((log_level, log_str))

    def _load_from_disk(self, path=None):
        # Validate `path`, or if not provided, use CONFIG_FILE_PATH if it exists.
        if path:
            self._init_log.append((logging.INFO, "Loading config from file:\n  %s" % path))
            if not os.path.exists(path):
                self._init_log.append((logging.ERROR, "File not found: %s" % (path)))
                raise ConfigLoadFailure(self._init_log)
        else:
            # Gracefully handle the case where there isn't a user config file.
            if not os.path.exists(CONFIG_FILE_PATH):
                self._init_log.append((logging.DEBUG, "User config file not found."))
                return
            path = CONFIG_FILE_PATH
            self._init_log.append((logging.INFO, "Loading user config file:\n  %s" % path))
        # Try to load and parse the config file at `path`.
        config = ConfigParser()
        try:
            with open(path) as config_file:
                config_file_contents = config_file.read()
            config.read_string(config_file_contents, source=path)
        except (ConfigParserError, OSError) as ex:
            if __debug__:
                raise
            raise ConfigLoadFailure(self._init_log, reason=ex) from None
        # At this point the config file syntax is correct, but we need to still validate
        # the parsed options (i.e. that the options have valid values).
        (config, logs) = _parse_config(config)
        for verbosity, message in logs:
            self._init_log.append((verbosity, message))
        if config is None:
            raise ConfigLoadFailure(self._init_log)
        self._config = config

    def is_default(self, command: str, option: str) -> bool:
        """True if specified config option is unset (i.e. the default), False otherwise."""
        return not (command in self._config and option in self._config[command])

    def get_value(
        self,
        command: str,
        option: str,
        override: ty.Optional[ConfigValue] = None,
    ) -> ConfigValue:
        """Get the current setting or default value of the specified command option."""
        assert command in CONFIG_MAP and option in CONFIG_MAP[command]
        if override is not None:
            value = override
        elif command in self._config and option in self._config[command]:
            value = self._config[command][option]
        else:
            value = CONFIG_MAP[command][option]
        if isinstance(value, ValidatedValue):
            return value.value
        if isinstance(CONFIG_MAP[command][option], Enum) and isinstance(override, str):
            return CONFIG_MAP[command][option].__class__[value.upper().strip()]
        return value

    def get_help_string(
        self, command: str, option: str, show_default: ty.Optional[bool] = None
    ) -> str:
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
                value_str = "on" if self._config[command][option] else "off"
            else:
                value_str = str(self._config[command][option])
            return " [setting: %s]" % (value_str)
        if show_default is False or (
            show_default is None and is_flag and CONFIG_MAP[command][option] is False
        ):
            return ""
        return " [default: %s]" % (str(CONFIG_MAP[command][option]))
