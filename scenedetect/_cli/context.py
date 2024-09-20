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
"""Context of which command-line options and config settings the user provided."""

import logging
import os
import typing as ty

import click

import scenedetect  # Required to access __version__
from scenedetect import AVAILABLE_BACKENDS, open_video
from scenedetect._cli.config import (
    CHOICE_MAP,
    ConfigLoadFailure,
    ConfigRegistry,
)
from scenedetect.detectors import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
)
from scenedetect.frame_timecode import MAX_FPS_DELTA, FrameTimecode
from scenedetect.platform import init_logger
from scenedetect.scene_detector import FlashFilter, SceneDetector
from scenedetect.scene_manager import Interpolation, SceneManager
from scenedetect.stats_manager import StatsManager
from scenedetect.video_splitter import is_ffmpeg_available, is_mkvmerge_available
from scenedetect.video_stream import FrameRateUnavailable, VideoOpenFailure, VideoStream

logger = logging.getLogger("pyscenedetect")

USER_CONFIG = ConfigRegistry(throw_exception=False)

SceneList = ty.List[ty.Tuple[FrameTimecode, FrameTimecode]]

CutList = ty.List[FrameTimecode]


def parse_timecode(
    value: ty.Optional[str], frame_rate: float, correct_pts: bool = False
) -> FrameTimecode:
    """Parses a user input string into a FrameTimecode assuming the given framerate.

    If value is None, None will be returned instead of processing the value.

    Raises:
        click.BadParameter
    """
    if value is None:
        return None
    try:
        if correct_pts and value.isdigit():
            value = int(value)
            if value >= 1:
                value -= 1
        return FrameTimecode(timecode=value, fps=frame_rate)
    except ValueError as ex:
        raise click.BadParameter(
            "timecode must be in seconds (100.0), frames (100), or HH:MM:SS"
        ) from ex


def check_split_video_requirements(use_mkvmerge: bool) -> None:
    """Validates that the proper tool is available on the system to perform the
    `split-video` command.

    Arguments:
        use_mkvmerge: True if mkvmerge (-m), False otherwise.

    Raises: click.BadParameter if the proper video splitting tool cannot be found.
    """

    if (use_mkvmerge and not is_mkvmerge_available()) or not is_ffmpeg_available():
        error_strs = [
            "{EXTERN_TOOL} is required for split-video{EXTRA_ARGS}.".format(
                EXTERN_TOOL="mkvmerge" if use_mkvmerge else "ffmpeg",
                EXTRA_ARGS=" when mkvmerge (-m) is set" if use_mkvmerge else "",
            )
        ]
        error_strs += ["Ensure the program is available on your system and try again."]
        if not use_mkvmerge and is_mkvmerge_available():
            error_strs += ["You can specify mkvmerge (-m) to use mkvmerge for splitting."]
        elif use_mkvmerge and is_ffmpeg_available():
            error_strs += ["You can specify copy (-c) to use ffmpeg stream copying."]
        error_str = "\n".join(error_strs)
        raise click.BadParameter(error_str, param_hint="split-video")


class AppState:
    def __init__(self):
        self.video_stream: VideoStream = None
        self.scene_manager: SceneManager = None
        self.stats_manager: StatsManager = None
        self.output: str = None
        self.quiet_mode: bool = None
        self.stats_file_path: str = None
        self.drop_short_scenes: bool = None
        self.merge_last_scene: bool = None
        self.min_scene_len: FrameTimecode = None
        self.frame_skip: int = None
        self.default_detector: ty.Tuple[ty.Type[SceneDetector], ty.Dict[str, ty.Any]] = None
        self.start_time: FrameTimecode = None  # time -s/--start
        self.end_time: FrameTimecode = None  # time -e/--end
        self.duration: FrameTimecode = None  # time -d/--duration
        self.load_scenes_input: str = None  # load-scenes -i/--input
        self.load_scenes_column_name: str = None  # load-scenes -c/--start-col-name
        self.save_images: bool = False  # True if the save-images command was specified
        # Result of save-images function output stored for use by export-html
        self.save_images_result: ty.Any = (None, None)


class CliContext:
    """The state of the application representing what video will be processed, how, and what to do
    with the result. This includes handling all input options via command line and config file.
    Once the CLI creates a context, it is executed by passing it to the
    `scenedetect._cli.controller.run_scenedetect` function.
    """

    def __init__(self):
        # State:
        self.config: ConfigRegistry = USER_CONFIG
        self.quiet_mode: bool = None
        self.scene_manager: SceneManager = None
        self.stats_manager: StatsManager = None
        self.save_images: bool = False  # True if the save-images command was specified
        self.save_images_result: ty.Any = (None, None)  # Result of save-images used by export-html

        # Input:
        self.video_stream: VideoStream = None
        self.load_scenes_input: str = None  # load-scenes -i/--input
        self.load_scenes_column_name: str = None  # load-scenes -c/--start-col-name
        self.start_time: FrameTimecode = None  # time -s/--start
        self.end_time: FrameTimecode = None  # time -e/--end
        self.duration: FrameTimecode = None  # time -d/--duration
        self.frame_skip: int = None

        # Options:
        self.drop_short_scenes: bool = None
        self.merge_last_scene: bool = None
        self.min_scene_len: FrameTimecode = None
        self.default_detector: ty.Tuple[ty.Type[SceneDetector], ty.Dict[str, ty.Any]] = None
        self.output_dir: str = None
        self.stats_file_path: str = None

        # Output Commands (e.g. split-video, save-images):
        # Commands to run after the detection pipeline. Stored as (callback, args) and invoked with
        # the results of the detection pipeline by the controller.
        self.commands: ty.List[ty.Tuple[ty.Callable, ty.Dict[str, ty.Any]]] = []

    def add_command(self, command: ty.Callable, command_args: dict):
        """Add `command` to the processing pipeline. Will be invoked after processing the input
        the `context`, the resulting `scenes` and `cuts`, and `command_args`."""
        self.commands.append((command, command_args))

    #
    # Command Handlers
    #

    def handle_options(
        self,
        input_path: ty.AnyStr,
        output: ty.Optional[ty.AnyStr],
        framerate: float,
        stats_file: ty.Optional[ty.AnyStr],
        downscale: ty.Optional[int],
        frame_skip: int,
        min_scene_len: str,
        drop_short_scenes: bool,
        merge_last_scene: bool,
        backend: ty.Optional[str],
        quiet: bool,
        logfile: ty.Optional[ty.AnyStr],
        config: ty.Optional[ty.AnyStr],
        stats: ty.Optional[ty.AnyStr],
        verbosity: ty.Optional[str],
    ):
        """Parse all global options/arguments passed to the main scenedetect command,
        before other sub-commands (e.g. this function processes the [options] when calling
        `scenedetect [options] [commands [command options]]`).

        Raises:
            click.BadParameter: One of the given options/parameters is invalid.
            click.Abort: Fatal initialization failure.
        """

        # TODO(v1.0): Make the stats value optional (e.g. allow -s only), and allow use of
        # $VIDEO_NAME macro in the name.  Default to $VIDEO_NAME.csv.

        # The `scenedetect` command was just started, let's initialize logging and try to load any
        # config files that were specified.
        try:
            init_failure = not self.config.initialized
            init_log = self.config.get_init_log()
            quiet = not init_failure and quiet
            self._initialize_logging(quiet=quiet, verbosity=verbosity, logfile=logfile)

            # Configuration file was specified via CLI argument -c/--config.
            if config and not init_failure:
                self.config = ConfigRegistry(config)
                init_log += self.config.get_init_log()
                # Re-initialize logger with the correct verbosity.
                if verbosity is None and not self.config.is_default("global", "verbosity"):
                    verbosity_str = self.config.get_value("global", "verbosity")
                    assert verbosity_str in CHOICE_MAP["global"]["verbosity"]
                    self.quiet_mode = False
                    self._initialize_logging(verbosity=verbosity_str, logfile=logfile)

        except ConfigLoadFailure as ex:
            init_failure = True
            init_log += ex.init_log
            if ex.reason is not None:
                init_log += [(logging.ERROR, "Error: %s" % str(ex.reason).replace("\t", "  "))]
        finally:
            # Make sure we print the version number even on any kind of init failure.
            logger.info("PySceneDetect %s", scenedetect.__version__)
            for log_level, log_str in init_log:
                logger.log(log_level, log_str)
            if init_failure:
                logger.critical("Error processing configuration file.")
                raise click.Abort()

        if self.config.config_dict:
            logger.debug("Current configuration:\n%s", str(self.config.config_dict))

        logger.debug("Parsing program options.")
        if stats is not None and frame_skip:
            error_strs = [
                "Unable to detect scenes with stats file if frame skip is not 0.",
                "  Either remove the -fs/--frame-skip option, or the -s/--stats file.\n",
            ]
            logger.error("\n".join(error_strs))
            raise click.BadParameter(
                "Combining the -s/--stats and -fs/--frame-skip options is not supported.",
                param_hint="frame skip + stats file",
            )

        # Handle the case where -i/--input was not specified (e.g. for the `help` command).
        if input_path is None:
            return

        # Have to load the input video to obtain a time base before parsing timecodes.
        self._open_video_stream(
            input_path=input_path,
            framerate=framerate,
            backend=self.config.get_value("global", "backend", backend, ignore_default=True),
        )

        self.output_dir = output if output else self.config.get_value("global", "output")
        if self.output_dir:
            logger.info("Output directory set:\n  %s", self.output_dir)

        self.min_scene_len = parse_timecode(
            min_scene_len
            if min_scene_len is not None
            else self.config.get_value("global", "min-scene-len"),
            self.video_stream.frame_rate,
        )
        self.drop_short_scenes = drop_short_scenes or self.config.get_value(
            "global", "drop-short-scenes"
        )
        self.merge_last_scene = merge_last_scene or self.config.get_value(
            "global", "merge-last-scene"
        )
        self.frame_skip = self.config.get_value("global", "frame-skip", frame_skip)

        # Create StatsManager if --stats is specified.
        if stats_file:
            self.stats_file_path = stats_file
            self.stats_manager = StatsManager()

        # Initialize default detector with values in the config file.
        default_detector = self.config.get_value("global", "default-detector")
        if default_detector == "detect-adaptive":
            self.default_detector = (AdaptiveDetector, self.get_detect_adaptive_params())
        elif default_detector == "detect-content":
            self.default_detector = (ContentDetector, self.get_detect_content_params())
        elif default_detector == "detect-hash":
            self.default_detector = (HashDetector, self.get_detect_hash_params())
        elif default_detector == "detect-hist":
            self.default_detector = (HistogramDetector, self.get_detect_hist_params())
        elif default_detector == "detect-threshold":
            self.default_detector = (ThresholdDetector, self.get_detect_threshold_params())
        else:
            raise click.BadParameter("Unknown detector type!", param_hint="default-detector")

        logger.debug("Initializing SceneManager.")
        scene_manager = SceneManager(self.stats_manager)

        if downscale is None and self.config.is_default("global", "downscale"):
            scene_manager.auto_downscale = True
        else:
            scene_manager.auto_downscale = False
            downscale = self.config.get_value("global", "downscale", downscale)
            try:
                scene_manager.downscale = downscale
            except ValueError as ex:
                logger.debug(str(ex))
                raise click.BadParameter(str(ex), param_hint="downscale factor") from None
        scene_manager.interpolation = Interpolation[
            self.config.get_value("global", "downscale-method").upper()
        ]
        self.scene_manager = scene_manager

    def get_detect_content_params(
        self,
        threshold: ty.Optional[float] = None,
        luma_only: bool = None,
        min_scene_len: ty.Optional[str] = None,
        weights: ty.Optional[ty.Tuple[float, float, float, float]] = None,
        kernel_size: ty.Optional[int] = None,
        filter_mode: ty.Optional[str] = None,
    ) -> ty.Dict[str, ty.Any]:
        """Handle detect-content command options and return args to construct one with."""
        self.ensure_input_open()

        if self.drop_short_scenes:
            min_scene_len = 0
        else:
            if min_scene_len is None:
                if self.config.is_default("detect-content", "min-scene-len"):
                    min_scene_len = self.min_scene_len.frame_num
                else:
                    min_scene_len = self.config.get_value("detect-content", "min-scene-len")
            min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate).frame_num

        if weights is not None:
            try:
                weights = ContentDetector.Components(*weights)
            except ValueError as ex:
                logger.debug(str(ex))
                raise click.BadParameter(str(ex), param_hint="weights") from None

        return {
            "weights": self.config.get_value("detect-content", "weights", weights),
            "kernel_size": self.config.get_value("detect-content", "kernel-size", kernel_size),
            "luma_only": luma_only or self.config.get_value("detect-content", "luma-only"),
            "min_scene_len": min_scene_len,
            "threshold": self.config.get_value("detect-content", "threshold", threshold),
            "filter_mode": FlashFilter.Mode[
                self.config.get_value("detect-content", "filter-mode", filter_mode).upper()
            ],
        }

    def get_detect_adaptive_params(
        self,
        threshold: ty.Optional[float] = None,
        min_content_val: ty.Optional[float] = None,
        frame_window: ty.Optional[int] = None,
        luma_only: bool = None,
        min_scene_len: ty.Optional[str] = None,
        weights: ty.Optional[ty.Tuple[float, float, float, float]] = None,
        kernel_size: ty.Optional[int] = None,
        min_delta_hsv: ty.Optional[float] = None,
    ) -> ty.Dict[str, ty.Any]:
        """Handle detect-adaptive command options and return args to construct one with."""
        self.ensure_input_open()

        # TODO(v0.7): Remove these branches when removing -d/--min-delta-hsv.
        if min_delta_hsv is not None:
            logger.error("-d/--min-delta-hsv is deprecated, use -c/--min-content-val instead.")
            if min_content_val is None:
                min_content_val = min_delta_hsv
        # Handle case where deprecated min-delta-hsv is set, and use it to set min-content-val.
        if not self.config.is_default("detect-adaptive", "min-delta-hsv"):
            logger.error(
                "[detect-adaptive] config file option `min-delta-hsv` is deprecated"
                ", use `min-delta-hsv` instead."
            )
            if self.config.is_default("detect-adaptive", "min-content-val"):
                self.config.config_dict["detect-adaptive"]["min-content-val"] = (
                    self.config.config_dict["detect-adaptive"]["min-deleta-hsv"]
                )

        if self.drop_short_scenes:
            min_scene_len = 0
        else:
            if min_scene_len is None:
                if self.config.is_default("detect-adaptive", "min-scene-len"):
                    min_scene_len = self.min_scene_len.frame_num
                else:
                    min_scene_len = self.config.get_value("detect-adaptive", "min-scene-len")
            min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate).frame_num

        if weights is not None:
            try:
                weights = ContentDetector.Components(*weights)
            except ValueError as ex:
                logger.debug(str(ex))
                raise click.BadParameter(str(ex), param_hint="weights") from None
        return {
            "adaptive_threshold": self.config.get_value("detect-adaptive", "threshold", threshold),
            "weights": self.config.get_value("detect-adaptive", "weights", weights),
            "kernel_size": self.config.get_value("detect-adaptive", "kernel-size", kernel_size),
            "luma_only": luma_only or self.config.get_value("detect-adaptive", "luma-only"),
            "min_content_val": self.config.get_value(
                "detect-adaptive", "min-content-val", min_content_val
            ),
            "min_scene_len": min_scene_len,
            "window_width": self.config.get_value("detect-adaptive", "frame-window", frame_window),
        }

    def get_detect_threshold_params(
        self,
        threshold: ty.Optional[float] = None,
        fade_bias: ty.Optional[float] = None,
        add_last_scene: bool = None,
        min_scene_len: ty.Optional[str] = None,
    ) -> ty.Dict[str, ty.Any]:
        """Handle detect-threshold command options and return args to construct one with."""
        self.ensure_input_open()

        if self.drop_short_scenes:
            min_scene_len = 0
        else:
            if min_scene_len is None:
                if self.config.is_default("detect-threshold", "min-scene-len"):
                    min_scene_len = self.min_scene_len.frame_num
                else:
                    min_scene_len = self.config.get_value("detect-threshold", "min-scene-len")
            min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate).frame_num
        # TODO(v1.0): add_last_scene cannot be disabled right now.
        return {
            "add_final_scene": add_last_scene
            or self.config.get_value("detect-threshold", "add-last-scene"),
            "fade_bias": self.config.get_value("detect-threshold", "fade-bias", fade_bias),
            "min_scene_len": min_scene_len,
            "threshold": self.config.get_value("detect-threshold", "threshold", threshold),
        }

    def handle_load_scenes(self, input: ty.AnyStr, start_col_name: ty.Optional[str]):
        """Handle `load-scenes` command options."""
        self.ensure_input_open()
        if self.scene_manager.get_num_detectors() > 0:
            raise click.ClickException("The load-scenes command cannot be used with detectors.")
        if self.load_scenes_input:
            raise click.ClickException("The load-scenes command must only be specified once.")
        input = os.path.abspath(input)
        if not os.path.exists(input):
            raise click.BadParameter(
                f"Could not load scenes, file does not exist: {input}", param_hint="-i/--input"
            )
        self.load_scenes_input = input
        self.load_scenes_column_name = self.config.get_value(
            "load-scenes", "start-col-name", start_col_name
        )

    def get_detect_hist_params(
        self,
        threshold: ty.Optional[float] = None,
        bins: ty.Optional[int] = None,
        min_scene_len: ty.Optional[str] = None,
    ) -> ty.Dict[str, ty.Any]:
        """Handle detect-hist command options and return args to construct one with."""
        self.ensure_input_open()
        if self.drop_short_scenes:
            min_scene_len = 0
        else:
            if min_scene_len is None:
                if self.config.is_default("detect-hist", "min-scene-len"):
                    min_scene_len = self.min_scene_len.frame_num
                else:
                    min_scene_len = self.config.get_value("detect-hist", "min-scene-len")
            min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate).frame_num
        return {
            "bins": self.config.get_value("detect-hist", "bins", bins),
            "min_scene_len": min_scene_len,
            "threshold": self.config.get_value("detect-hist", "threshold", threshold),
        }

    def get_detect_hash_params(
        self,
        threshold: ty.Optional[float] = None,
        size: ty.Optional[int] = None,
        lowpass: ty.Optional[int] = None,
        min_scene_len: ty.Optional[str] = None,
    ) -> ty.Dict[str, ty.Any]:
        """Handle detect-hash command options and return args to construct one with."""
        self.ensure_input_open()
        if self.drop_short_scenes:
            min_scene_len = 0
        else:
            if min_scene_len is None:
                if self.config.is_default("detect-hash", "min-scene-len"):
                    min_scene_len = self.min_scene_len.frame_num
                else:
                    min_scene_len = self.config.get_value("detect-hash", "min-scene-len")
            min_scene_len = parse_timecode(min_scene_len, self.video_stream.frame_rate).frame_num
        return {
            "lowpass": self.config.get_value("detect-hash", "lowpass", lowpass),
            "min_scene_len": min_scene_len,
            "size": self.config.get_value("detect-hash", "size", size),
            "threshold": self.config.get_value("detect-hash", "threshold", threshold),
        }

    def handle_time(self, start, duration, end):
        """Handle `time` command options."""
        self.ensure_input_open()
        if duration is not None and end is not None:
            raise click.BadParameter(
                "Only one of --duration/-d or --end/-e can be specified, not both.",
                param_hint="time",
            )
        logger.debug(
            "Setting video time:\n    start: %s, duration: %s, end: %s", start, duration, end
        )
        # *NOTE*: The Python API uses 0-based frame indices, but the CLI uses 1-based indices to
        # match the default start number used by `ffmpeg` when saving frames as images. As such,
        # we must correct start time if set as frames. See the test_cli_time* tests for for details.
        self.start_time = parse_timecode(start, self.video_stream.frame_rate, correct_pts=True)
        self.end_time = parse_timecode(end, self.video_stream.frame_rate)
        self.duration = parse_timecode(duration, self.video_stream.frame_rate)
        if self.start_time and self.end_time and (self.start_time + 1) > self.end_time:
            raise click.BadParameter("-e/--end time must be greater than -s/--start")

    #
    # Private Methods
    #

    def _initialize_logging(
        self,
        quiet: ty.Optional[bool] = None,
        verbosity: ty.Optional[str] = None,
        logfile: ty.Optional[ty.AnyStr] = None,
    ):
        """Setup logging based on CLI args and user configuration settings."""
        if quiet is not None:
            self.quiet_mode = bool(quiet)
        curr_verbosity = logging.INFO
        # Convert verbosity into it's log level enum, and override quiet mode if set.
        if verbosity is not None:
            assert verbosity in CHOICE_MAP["global"]["verbosity"]
            if verbosity.lower() == "none":
                self.quiet_mode = True
                verbosity = "info"
            else:
                # Override quiet mode if verbosity is set.
                self.quiet_mode = False
            curr_verbosity = getattr(logging, verbosity.upper())
        else:
            verbosity_str = USER_CONFIG.get_value("global", "verbosity")
            assert verbosity_str in CHOICE_MAP["global"]["verbosity"]
            if verbosity_str.lower() == "none":
                self.quiet_mode = True
            else:
                curr_verbosity = getattr(logging, verbosity_str.upper())
                # Override quiet mode if verbosity is set.
                if not USER_CONFIG.is_default("global", "verbosity"):
                    self.quiet_mode = False
        # Initialize logger with the set CLI args / user configuration.
        init_logger(log_level=curr_verbosity, show_stdout=not self.quiet_mode, log_file=logfile)

    def add_detector(self, detector):
        """Add Detector: Adds a detection algorithm to the CliContext's SceneManager."""
        if self.load_scenes_input:
            raise click.ClickException("The load-scenes command cannot be used with detectors.")
        self.ensure_input_open()
        self.scene_manager.add_detector(detector)

    def ensure_input_open(self):
        """Ensure self.video_stream was initialized (i.e. -i/--input was specified),
        otherwise raises an exception. Should only be used from commands that require an
        input video to process the options (e.g. those that require a timecode).

        Raises:
            click.BadParameter: self.video_stream was not initialized.
        """
        # TODO: Do we still need to do this for each command?  Originally this was added for the
        # help command to function correctly.
        if self.video_stream is None:
            raise click.ClickException("No input video (-i/--input) was specified.")

    def _open_video_stream(
        self, input_path: ty.AnyStr, framerate: ty.Optional[float], backend: ty.Optional[str]
    ):
        if "%" in input_path and backend != "opencv":
            raise click.BadParameter(
                "The OpenCV backend (`--backend opencv`) must be used to process image sequences.",
                param_hint="-i/--input",
            )
        if framerate is not None and framerate < MAX_FPS_DELTA:
            raise click.BadParameter("Invalid framerate specified!", param_hint="-f/--framerate")
        try:
            if backend is None:
                backend = self.config.get_value("global", "backend")
            else:
                if backend not in AVAILABLE_BACKENDS:
                    raise click.BadParameter(
                        "Specified backend %s is not available on this system!" % backend,
                        param_hint="-b/--backend",
                    )
            # Open the video with the specified backend, loading any required config settings.
            if backend == "pyav":
                self.video_stream = open_video(
                    path=input_path,
                    framerate=framerate,
                    backend=backend,
                    threading_mode=self.config.get_value("backend-pyav", "threading-mode"),
                    suppress_output=self.config.get_value("backend-pyav", "suppress-output"),
                )
            elif backend == "opencv":
                self.video_stream = open_video(
                    path=input_path,
                    framerate=framerate,
                    backend=backend,
                    max_decode_attempts=self.config.get_value(
                        "backend-opencv", "max-decode-attempts"
                    ),
                )
            # Handle backends without any config options.
            else:
                self.video_stream = open_video(
                    path=input_path,
                    framerate=framerate,
                    backend=backend,
                )
            logger.debug("Video opened using backend %s", type(self.video_stream).__name__)
        except FrameRateUnavailable as ex:
            raise click.BadParameter(
                "Failed to obtain framerate for input video. Manually specify framerate with the"
                " -f/--framerate option, or try re-encoding the file.",
                param_hint="-i/--input",
            ) from ex
        except VideoOpenFailure as ex:
            raise click.BadParameter(
                "Failed to open input video%s: %s"
                % (" using %s backend" % backend if backend else "", str(ex)),
                param_hint="-i/--input",
            ) from ex
        except OSError as ex:
            raise click.BadParameter(
                "Input error:\n\n\t%s\n" % str(ex), param_hint="-i/--input"
            ) from None

    def _on_duplicate_command(self, command: str) -> None:
        """Called when a command is duplicated to stop parsing and raise an error.

        Arguments:
            command: Command that was duplicated for error context.

        Raises:
            click.BadParameter
        """
        error_strs = []
        error_strs.append("Error: Command %s specified multiple times." % command)
        error_strs.append("The %s command may appear only one time.")

        logger.error("\n".join(error_strs))
        raise click.BadParameter(
            "\n  Command %s may only be specified once." % command,
            param_hint="%s command" % command,
        )
