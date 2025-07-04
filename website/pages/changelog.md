
Releases
==========================================================

## PySceneDetect 0.6

### PySceneDetect 0.6.6 (March 9, 2025)

#### Release Notes

PySceneDetect v0.6.6 introduces new output formats, which improve compatibility with popular video editors (e.g. DaVinci Resolve).

#### Changelog

 - [feature] New `save-otio` command supports saving scenes in OTIO format [#497](https://github.com/Breakthrough/PySceneDetect/issues/497)
 - [feature] New `save-edl` command supports saving scenes in EDL format CMX 3600 [#495](https://github.com/Breakthrough/PySceneDetect/issues/495)
 - [bugfix] Fix incorrect help entries for short-form arguments which suggested invalid syntax [#493](https://github.com/Breakthrough/PySceneDetect/issues/493)
 - [bugfix] Fix crash when using `split-video` with `-m`/`--mkvmerge` option [#473](https://github.com/Breakthrough/PySceneDetect/issues/473)
 - [bugfix] Fix incorrect default filename template for `split-video` command with `-m`/`--mkvmerge` option
 - [bugfix] Fix inconsistent filenames when using `split_video_mkvmerge()`
 - [bugfix] Ensure auto-rotation is always enabled for `VideoStreamCv2` as workaround for (opencv#26795)[https://github.com/opencv/opencv/issues/26795]
 - [general] The `export-html` command is now deprecated, use `save-html` instead
 - [general] Updates to Windows distributions:
    - av 13.1.0 -> 14.2.0
    - click 8.1.7 -> 8.1.8
    - imageio-ffmpeg 0.5.1 -> 0.6.0
    - moviepy 2.1.1 -> 2.1.2
    - numpy 2.1.3 -> 2.2.3
    - opencv-python 4.10.0.84 -> 4.11.0.86
 - [general] Windows download URLs for standalone ZIP distribution no longer have `portable` suffix


### PySceneDetect 0.6.5 (November 24, 2024)

#### Release Notes

This release brings crop support, performance improvements to save-images, lots of bugfixes, and improved compatibility with MoviePy 2.0+.

#### Changelog

 - [feature] Add ability to crop input video before processing [#302](https://github.com/Breakthrough/PySceneDetect/issues/302) [#449](https://github.com/Breakthrough/PySceneDetect/issues/449)
     - [cli] Add `--crop` option to `scenedetect` command and config file to crop video frames before scene detection
     - [api] Add `crop` property to `SceneManager` to crop video frames before scene detection
 - [feature] Add ability to configure CSV separators for rows/columns in config file [#423](https://github.com/Breakthrough/PySceneDetect/issues/423)
 - [feature] Add new `--show` flag to `export-html` command to launch browser after processing [#442](https://github.com/Breakthrough/PySceneDetect/issues/442)
 - [improvement] Add new `threading` option to `save-images`/`save_images()` [#456](https://github.com/Breakthrough/PySceneDetect/issues/456)
    - Enabled by default, offloads image encoding and disk IO to separate threads
    - Improves performance by up to 50% in some cases
 - [improvement] The `export-html` command now implicitly invokes `save-images` with default parameters
    - The output of the `export-html` command will always use the result of the `save-images` command that *precedes* it
 - [improvement] `save_to_csv` now works with paths from `pathlib`
 - [api] The `save_to_csv` function now works correctly with paths from the `pathlib` module
 - [api] Add `col_separator` and `row_separator` args to `write_scene_list` function in `scenedetect.scene_manager`
 - [api] The MoviePy backend now works with MoviePy 2.0+
 - [bugfix] Fix `SyntaxWarning` due to incorrect escaping [#400](https://github.com/Breakthrough/PySceneDetect/issues/400)
 - [bugfix] Fix `ContentDetector` crash when using callbacks [#416](https://github.com/Breakthrough/PySceneDetect/issues/416) [#420](https://github.com/Breakthrough/PySceneDetect/issues/420)
 - [bugfix] Fix `save-images`/`save_images()` not working correctly with UTF-8 paths [#450](https://github.com/Breakthrough/PySceneDetect/issues/450)
 - [bugfix] Fix crash when using `save-images`/`save_images()` with OpenCV backend [#455](https://github.com/Breakthrough/PySceneDetect/issues/455)
 - [bugfix] Fix new detectors not working with `default-detector` config option
 - [general] Timecodes of the form `MM:SS[.nnn]` are now processed correctly [#443](https://github.com/Breakthrough/PySceneDetect/issues/443)
 - [general] Updates to Windows distributions:
    - The MoviePy backend is now included with Windows distributions
    - Python 3.9 -> Python 3.13
    - PyAV 10 -> 13.1.0
    - OpenCV 4.10.0.82 -> 4.10.0.84
    - Ffmpeg 6.0 -> 7.1

#### Python Distribution Changes

 * *v0.6.5.1* - Fix compatibility issues with PyAV 14+ [#466](https://github.com/Breakthrough/PySceneDetect/issues/466)
 * *v0.6.5.2* - Fix for `AttributeError: module 'cv2' has no attribute 'Mat'` [#468](https://github.com/Breakthrough/PySceneDetect/issues/466)


### 0.6.4 (June 10, 2024)

#### Release Notes

Includes new histogram and perceptual hash based detectors (thanks @wjs018 and @ash2703), adds flash filter to content detector, and includes various bugfixes. Below shows the scores of the new detectors normalized against `detect-content` for comparison on a difficult segment with 3 cuts:

<a href="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/v0.6.4-release/website/pages/img/0.6.4-score-comparison.png"><img src="https://raw.githubusercontent.com/Breakthrough/PySceneDetect/v0.6.4-release/website/pages/img/0.6.4-score-comparison.png" width="480" alt="comparison of new detector scores"/></a>

Feedback on the new detection methods and their default values is most welcome.  Thanks to everyone who contributed for their help and support!

#### Changelog

 - [feature] New detectors:
   - `detect-hist` / `HistogramDetector` [#295](https://github.com/Breakthrough/PySceneDetect/pull/295) [#53](https://github.com/Breakthrough/PySceneDetect/issues/53)
   - `detect-hash` / `HashDetector` [#290](https://github.com/Breakthrough/PySceneDetect/pull/290)
 - [feature] Add flash suppression filter for `detect-content` / `ContentDetector` (enabled by default) [#35](https://github.com/Breakthrough/PySceneDetect/pull/295) [#53](https://github.com/Breakthrough/PySceneDetect/issues/35)
    - Reduces number of cuts generated during strobing or flashing effects
    - Can be configured using `--filter-mode` option
    - `--filter-mode = merge` (new default) merges consecutive scenes shorter than `min-scene-len`
    - `--filter-mode = suppress` (previous default) disables generating new scenes until `min-scene-len` has passed
 - [feature] Add more templates for `save-images` filename customization: `$TIMECODE`, `$FRAME_NUMBER`, `$TIMESTAMP_MS` (thanks @Veldhoen0) [#395](https://github.com/Breakthrough/PySceneDetect/pull/395)
 - [bugfix] Remove extraneous console output when using `--drop-short-scenes`
 - [bugfix] Fix scene lengths being smaller than `min-scene-len` when using `detect-adaptive` / `AdaptiveDetector` with large values of `--frame-window`
 - [bugfix] Fix crash when decoded frames have incorrect resolution and log error instead [#319](https://github.com/Breakthrough/PySceneDetect/issues/319)
 - [bugfix] Update default ffmpeg stream mapping from `-map 0` to `-map 0:v:0 -map 0:a? -map 0:s?` [#392](https://github.com/Breakthrough/PySceneDetect/issues/392)


### 0.6.3 (March 9, 2024)

#### Release Notes

In addition to some perfromance improvements with the `load-scenes` command, this release of PySceneDetect includes a significant amount of bugfixes. Thanks to everyone who contributed to the release, including those who filed bug reports and helped with debugging!

**Program Changes:**

 - [bugfix] Fix crash for some WebM videos when using `save-images` with `--backend pyav` [#355](https://github.com/Breakthrough/PySceneDetect/issues/355)
 - [bugfix] Correct `--duration` and `--end` for presentation time when specified as frame numbers [#341](https://github.com/Breakthrough/PySceneDetect/issues/341)
 - [bugfix] Progress bar now has correct frame accounting when `--duration` or `--end` are set [#341](https://github.com/Breakthrough/PySceneDetect/issues/341)
 - [bugfix] Only allow `load-scenes` to be specified once, and disallow with other `detect-*` commands [#347](https://github.com/Breakthrough/PySceneDetect/issues/347)
 - [bugfix] Disallow `-s`/`--start` being larger than `-e`/`--end` for the `time` command
 - [bugfix] Fix `detect-adaptive` not respecting `--min-scene-len` for the first scene
 - [general] Comma-separated timecode list is now only printed when the `list-scenes` command is specified [#356](https://github.com/Breakthrough/PySceneDetect/issues/356)
 - [general] Several changes to `[list-scenes]` config file options:
   - Add `display-scenes` and `display-cuts` options to control output
   - Add `cut-format` to control formatting of cut points [#349](https://github.com/Breakthrough/PySceneDetect/issues/349)
      - Valid values: `frames`, `timecode`, `seconds`
 - [general] Increase progress bar indent to improve visibility and visual alignment
 - [improvement] The `s` suffix for setting timecode values in seconds is no longer required (values without decimal places are still interpreted as frame numbers)
 - [improvement] `load-scenes` now skips detection, generating output much faster [#347](https://github.com/Breakthrough/PySceneDetect/issues/347) (thanks @wjs018 for the initial implementation)

**API Changes:**

 - [bugfix] Fix `AttributeError` thrown when accessing `aspect_ratio` on certain videos using `VideoStreamAv` [#355](https://github.com/Breakthrough/PySceneDetect/issues/355)
 - [bugfix] Fix circular imports due to partially initialized module for some development environments [#350](https://github.com/Breakthrough/PySceneDetect/issues/350)
 - [bugfix] Fix `SceneManager.detect_scenes` warning when `duration` or `end_time` are specified as timecode strings [#346](https://github.com/Breakthrough/PySceneDetect/issues/346)
 - [bugfix] Ensure correct string conversion behavior for `FrameTimecode` when rounding is enabled [#354](https://github.com/Breakthrough/PySceneDetect/issues/354)
 - [bugfix] Fix `AdaptiveDetector` not respecting `min_scene_len` for the first scene
 - [feature] Add `output_dir` argument to `split_video_ffmpeg` and `split_video_mkvmerge` functions to set output directory [#298](https://github.com/Breakthrough/PySceneDetect/issues/298)
 - [feature] Add `formatter` argument to `split_video_ffmpeg` to allow formatting filenames via callback [#359](https://github.com/
 Breakthrough/PySceneDetect/issues/359)
 - [general] The `frame_img` argument to `SceneDetector.process_frame()` is now required
 - [general] Remove `TimecodeValue` from `scenedetect.frame_timecode` (use `typing.Union[int, float, str]`)
-  [general] Remove `MotionDetector` and `scenedetect.detectors.motion_detector` module (will be reintroduced after `SceneDetector` interface is stable)
 - [improvement] `scenedetect.stats_manager` module improvements:
   - The `StatsManager.register_metrics()` method no longer throws any exceptions
   - Add `StatsManager.metric_keys` property to query registered metric keys
   - Deprecate `FrameMetricRegistered` and `FrameMetricNotRegistered` exceptions (no longer used)
 - [improvement] When converting strings representing seconds to `FrameTimecode`, the `s` suffix is now optional, and whitespace is ignored (note that values without decimal places are still interpreted as frame numbers)
 - [improvement] The `VideoCaptureAdapter` in `scenedetect.backends.opencv` now attempts to report duration if known


### 0.6.2 (July 23, 2023)

#### Release Notes

Includes new [`load-scenes` command](https://www.scenedetect.com/docs/0.6.2/cli.html#load-scenes), ability to specify a default detector, PyAV 10 support, and several bugfixes. Minimum supported Python version is now **Python 3.7**.

**Command-Line Changes:**

 - [feature] Add [`load-scenes` command](https://www.scenedetect.com/docs/0.6.2/cli.html#load-scenes) to load cuts from `list-scenes` CSV output [#235](https://github.com/Breakthrough/PySceneDetect/issues/235)
 - [feature] Use `detect-adaptive` by default if a detector is not specified [#329](https://github.com/Breakthrough/PySceneDetect/issues/329)
   - Default detector can be set by [config file](https://www.scenedetect.com/docs/latest/cli/config_file.html) with the `default-detector` option under `[global]`
 - [bugfix] Fix `-d`/`--duration` and `-e`/`--end` options of `time` command consuming one extra frame [#307](https://github.com/Breakthrough/PySceneDetect/issues/307)
 - [bugfix] Fix incorrect end timecode for final scene when last frame of video is a new scene [#307](https://github.com/Breakthrough/PySceneDetect/issues/307)
 - [bugfix] Expand `$VIDEO_NAME` before creating output directory for `-f`/`--filename` option of `split-video`, now allows absolute paths
 - [general] Rename `ThresholdDetector` (`detect-threshold`) metric `delta_rgb` metric to `average_rgb`
 - [general] `-l`/`--logfile` always produces debug logs now
 - [general] Remove `-a`/`--all` flag from `scenedetect version` command, now prints all information by default (can still call `scenedetect` for version number alone)
 - [general] Add `-h`/`--help` options globally and for each command
 - [general] Remove `all` option from `scenedetect help` command (can now call `scenedetect help` for full reference)

**General:**

 - [feature] Add ability to specify method (floor/ceiling) when creating [`ThresholdDetector`](https://www.scenedetect.com/docs/0.6.2/api/detectors.html#scenedetect.detectors.threshold_detector.ThresholdDetector), allows fade to white detection [#143](https://github.com/Breakthrough/PySceneDetect/issues/143)
 - [general] Minimum supported Python version is now **Python 3.7**
 - [general] Add support for PyAV 10.0 [#292](https://github.com/Breakthrough/PySceneDetect/issues/292)
 - [general] Use platformdirs package instead of appdirs [#309](https://github.com/Breakthrough/PySceneDetect/issues/309)
 - [bugfix] Fix `end_time` always consuming one extra frame [#307](https://github.com/Breakthrough/PySceneDetect/issues/307)
 - [bugfix] Fix incorrect end timecode for last scene when `start_in_scene` is `True` or the final scene contains a single frame [#307](https://github.com/Breakthrough/PySceneDetect/issues/307)
 - [bugfix] Fix MoviePy read next frame [#320](https://github.com/Breakthrough/PySceneDetect/issues/320)
 - [bugfix] Template replacement when generating output now allows lower-case letters to be used as separators in addition to other characters
 - [api] Make some public functions/methods private (prefixed with `_`):
   - `get_aspect_ratio` function in `scenedetect.backends.opencv`
   - `mean_pixel_distance` and `estimated_kernel_size` functions in `scenedetect.detectors.content_detector`
   - `compute_frame_average` function in `scenedetect.detectors.threshold_detector`
   - `scenedetect.cli` and `scenedetect.thirdparty` modules
 - [api] Remove `compute_downscale_factor` in `scenedetect.video_stream` (use `scenedetect.scene_manager.compute_downscale_factor` instead)
 - [dist] Updated dependencies in Windows distributions: ffmpeg 6.0, PyAV 10, OpenCV 4.8, removed mkvmerge

#### Project Updates

 - Website and documentation is now hosted on Github Pages, documentation can be found at [scenedetect.com/docs](https://www.scenedetect.com/docs)
 - Windows and Linux builds are now done on Github Actions, add OSX builds as well
 - Build matrix has been updated to support Python 3.7 through 3.11 for all operating systems for Python distributions
 - Windows portable builds have been moved to Github Actions, signed builds/installer is still done on Appveyor
 - Windows distributions no longer include mkvmerge (can still [download for Windows here](https://mkvtoolnix.download/downloads.html#windows))


### 0.6.1 (November 28, 2022)

#### Release Notes

Includes [MoviePy support](https://github.com/Zulko/moviepy), edge detection capability for fast cuts, and several enhancements/bugfixes.

#### Changelog

**Command-Line Changes:**

 - [feature] Add `moviepy` backend wrapping the MoviePy package, uses `ffmpeg` binary on the system for video decoding
 - [feature] Edge detection can now be enabled with `detect-content` and `detect-adaptive` to improve accuracy in some cases, especially under lighting changes, see [new `-w`/`--weights` option](http://scenedetect.com/projects/Manual/en/latest/cli/detectors.html#detect-content) for more information
    - A good starting point is to place 100% weight on the change in a frame's hue, 50% on saturation change, 100% on luma (brightness) change, and 25% on change in edges, with a threshold of 32:
    `detect-adaptive -w 1.0 0.5 1.0 0.25`
    - Edge differences are typically larger than other components, so you may need to increase `-t`/`--threshold` higher when increasing the edge weight (the last component) with `detect-content, for example:
    `detect-content -w 1.0 0.5 1.0 0.25 -t 32`
    - May be enabled by default in the future once it has been more thoroughly tested, further improvements for `detect-content` are being investigated as well (e.g. motion compensation, flash suppression)
   - Short-form of `detect-content` option `--frame-window` has been changed from `-w` to `-f` to accommodate this change
 - [enhancement] Progress bar now displays number of detections while processing, no longer conflicts with log message output
 - [enhancement] When using ffmpeg to split videos, `-map 0` has been added to the default arguments so other audio tracks are also included when present ([#271](https://github.com/Breakthrough/PySceneDetect/issues/271))
 - [enhancement] Add `-a` flag to `version` command to print more information about versions of dependencies/tools being used
 - [enhancement] The resizing method used used for frame downscaling or resizing can now be set using [a config file](http://scenedetect.com/projects/Manual/en/latest/cli/config_file.html), see `[global]` option `downscale-method` and `[save-images]` option `scale-method`
 - [other] Linear interpolation is now used as the default downscaling method (previously was nearest neighbor) for improved edge detection accuracy
 - [other] Add `-c`/`--min-content-val` argument to `detect-adaptive`, deprecate `-d`/`--min-delta-hsv`

**General:**

 - [general] Recommend `detect-adaptive` over `detect-content`
 - [feature] Add new backend `VideoStreamMoviePy` using the MoviePy package`
 - [feature] Add edge detection to `ContentDetector` and `AdaptiveDetector` ([#35](https://github.com/Breakthrough/PySceneDetect/issues/35))
    - Add ability to specify content score weights of hue, saturation, luma, and edge differences between frames
    - Default remains as `1.0, 1.0, 1.0, 0.0` so there is no change in behavior
    - Kernel size used for improving edge overlap can also be customized
 - [feature] `AdaptiveDetector` no longer requires a `StatsManager` and can now be used with `frame_skip` ([#283](https://github.com/Breakthrough/PySceneDetect/issues/283))
 - [bugfix] Fix `scenedetect.detect()` throwing `TypeError` when specifying `stats_file_path`
 - [bugfix] Fix off-by-one error in end event timecode when `end_time` was set (reported end time was always one extra frame)
 - [bugfix] Fix a named argument that was incorrect ([#299](https://github.com/Breakthrough/PySceneDetect/issues/299))
 - [enhancement] Add optional `start_time`, `end_time`, and `start_in_scene` arguments to `scenedetect.detect()` ([#282](https://github.com/Breakthrough/PySceneDetect/issues/282))
 - [enhancement] Add `-map 0` option to default arguments of `split_video_ffmpeg` to include all audio tracks by default ([#271](https://github.com/Breakthrough/PySceneDetect/issues/271))
 - [docs] Add example for [using a callback](http://scenedetect.com/projects/Manual/en/v0.6.1/api/scene_manager.html#usage) ([#273](https://github.com/Breakthrough/PySceneDetect/issues/273))
 - [enhancement] Add new `VideoCaptureAdapter` to make existing `cv2.VideoCapture` objects compatible with a `SceneManager` ([#276](https://github.com/Breakthrough/PySceneDetect/issues/276))
    - Primary use case is for handling input devices/webcams and gstreamer pipes, [see updated examples](http://scenedetect.com/projects/Manual/en/latest/api/backends.html#devices-cameras-pipes)
    - Files, image sequences, and network streams/URLs should continue to use `VideoStreamCv2`
 - [api] The `SceneManager` methods `get_cut_list()` and `get_event_list()` are deprecated, along with the `base_timecode` argument
 - [api] The `base_timecode` argument of `get_scenes_from_cuts()` in `scenedetect.stats_manager` is deprecated (the signature of this function has been changed accordingly)
 - [api] Rename `AdaptiveDetector` constructor parameter `min_delta_hsv` to `min_content_val
 - [general] The default `crf` for `split_video_ffmpeg` has been changed from 21 to 22 to match command line default
 - [enhancement] Add `interpolation` property to `SceneManager` to allow setting method of frame downscaling, use linear interpolation by default (previously nearest neighbor)
 - [enhancement] Add `interpolation` argument to `save_images` to allow setting image resize method (default remains bicubic)

### 0.6 (May 29, 2022)

#### Release Notes

PySceneDetect v0.6 is a **major breaking change** including better performance, configuration file support, and a more ergonomic API.  The new **minimum Python version is now 3.6**. See the [Migration Guide](https://scenedetect.com/projects/Manual/en/latest/api/migration_guide.html) for information on how to port existing applications to the new API.  Most users will see performance improvements after updating, and changes to the command-line are not expected to break most workflows.

The main goals of v0.6 are reliability and performance. To achieve this required several breaking changes.  The video input API was refactored, and *many* technical debt items were addressed. This should help the eventual transition to the first planned stable release (v1.0) where the goal is an improved scene detection API.

Both the Windows installer and portable distributions now include signed executables. Many thanks to SignPath, AppVeyor, and AdvancedInstaller for their support.

#### Changelog

**Overview:**

 * Major performance improvements on multicore systems
 * [Configuration file support](http://scenedetect.com/projects/Manual/en/latest/cli/config_file.html) via command line option or user settings folder
 * Support for multiple video backends, PyAV is now supported in addition to OpenCV
 * Breaking API changes to `VideoManager` (replaced with `VideoStream`), `StatsManager`, and `save_images()`
    * See the [Migration Guide](https://scenedetect.com/projects/Manual/en/latest/api/migration_guide.html) for details on how to update from v0.5.x
    * A backwards compatibility layer has been added to prevent most applications from breaking, will be removed in a future release
 * Support for Python 2.7 has been dropped, minimum supported Python version is 3.6
 * Support for OpenCV 2.x has been dropped, minimum OpenCV version is 3.x
 * Windows binaries are now signed, thanks [SignPath.io](https://signpath.io/) (certificate by [SignPath Foundation](https://signpath.org/))

**Command-Line Changes:**

 * Configuration files are now supported, [see documentation for details](http://scenedetect.com/projects/Manual/en/latest/cli/config_file.html)
     * Can specify config file path with `-c`/`--config`, or create a `scenedetect.cfg` file in your user config folder
 * Frame numbers are now 1-based, aligning with most other tools (e.g. `ffmpeg`) and video editors ([#265](https://github.com/Breakthrough/PySceneDetect/issues/265))
 * Start/end *frame numbers* of adjacent scenes no longer overlap ([#264](https://github.com/Breakthrough/PySceneDetect/issues/265))
     * End/duration timecodes still include the frame's presentation time
 * Add `--merge-last-scene` option to merge last scene if shorter than `--min-scene-len`
 * Add `-b`/`--backend` option to use a specific video decoding backend
     * Supported backends are `opencv` and `pyav`
     * Run `scenedetect help` to see a list of backends available on the current system
     * Both backends are included with Windows builds
 * `split-video` command:
     * `-c`/`--copy` now uses `ffmpeg` instead of `mkvmerge` ([#77](https://github.com/Breakthrough/PySceneDetect/issues/77), [#236](https://github.com/Breakthrough/PySceneDetect/issues/236))
     * Add `-m`/`--mkvmerge` flag to use `mkvmerge` instead of `ffmpeg` ([#77](https://github.com/Breakthrough/PySceneDetect/issues/77))
     * Long name for `-a` has been changed to `--args` (from `--override-args`)
 * `detect-adaptive` command:
     * `--drop-short-scenes` now works properly with `detect-adaptive`
 * `detect-content` command:
     * Default threshold `-t`/`--threshold` lowered to 27 to be more sensitive to shot changes ([#246](https://github.com/Breakthrough/PySceneDetect/issues/246))
     * Add override for global `-m`/`--min-scene-len` option
 * `detect-threshold` command:
     * Remove `-p`/`--min-percent` and `-b`/`--block-size` options
     * Add override for global `-m`/`--min-scene-len` option
 * `save-images` command now works when `-i`/`--input` is an image sequences
 * Default backend (OpenCV) is more robust to video decoder failures
 * `-i`/`--input` may no longer be specified multiple times, if required use an external tool (e.g. `ffmpeg`, `mkvmerge`) to perform concatenation before processing
 * `-s`/`--stats` no longer loads existing statistics and will overwrite any existing files
 * `-l`/`--logfile` now respects `-o`/`--output`
 * `-v`/`--verbosity` now takes precedence over `-q`/`--quiet`

**API Changes:**

 * New `detect()` function performs scene detection on a video path, [see example here](http://scenedetect.com/projects/Manual/en/latest/api.html#quickstart)
 * New `open_video()` function to handle video input, [see example here](http://scenedetect.com/projects/Manual/en/latest/api.html#example)
 * `split_video_ffmpeg()` and `split_video_mkvmerge()` now take a single path as input
 * `save_images()` no longer accepts `downscale_factor`
    * Use `scale` or `height`/`width` arguments to resize images
 * New `VideoStream` replaces `VideoManager` ([#213](https://github.com/Breakthrough/PySceneDetect/issues/213))
    * Supports both OpenCV (`VideoStreamCv2`) and PyAV (`VideoStreamAv`)
    * Improves video seeking invariants, especially around defining what frames 0 and 1 mean for different time properties (`frame_number` is 1-based whereas `position` is 0-based to align with PTS)
    * See `test_time_invariants` in `tests/test_video_stream.py` as a reference of specific behaviours
 * Changes to `SceneManager`:
    * `detect_scenes()` now performs video decoding in a background thread, improving performance on most systems
    * `SceneManager` is now responsible for frame downscaling via the `downscale`/`auto_downscale` properties
    * `detect_scenes()` no longer shows a progress bar by default, set `show_progress=True` to restore the previous behaviour
    * `clear()` now clears detectors, as they may be stateful
    * `get_scene_list()` now returns an empty list if there are no detected cuts, specify `start_in_scene=True` for previous behavior (one scene spanning the entire input)
 * Changes to `StatsManager`:
    * `save_to_csv()` now accepts a path or an open file handle
    * `base_timecode` argument has been removed from `save_to_csv()`
    * `load_from_csv()` is now deprecated and will be removed in v1.0
 * Changes to `FrameTimecode`:
    * Use rounding instead of truncation when calculating frame numbers to fix incorrect round-trip conversions and improve accuracy ([#268](https://github.com/Breakthrough/PySceneDetect/issues/268))
    * Fix `previous_frame()` generating negative frame numbers in some cases
    * `FrameTimecode` objects can now perform arithmetic with formatted strings, e.g. `'HH:MM:SS.nnn'`
 * Merged constants `MAX_FPS_DELTA` and `MINIMUM_FRAMES_PER_SECOND_DELTA_FLOAT` in `scenedetect.frame_timecode` into new `MAX_FPS_DELTA` constant
 * `video_manager` parameter has been removed from the `AdaptiveDetector` constructor
 * `split_video_ffmpeg` and `split_video_mkvmerge` function arguments have been renamed and defaults updated:
    * `suppress_output` is now `show_output`, default is `False`
    * `hide_progress` is now `show_progress`, default is `False`
 * `block_size` argument has been removed from the `ThresholdDetector` constructor
 * `calculate_frame_score` method of `ContentDetector` has been renamed to `_calculate_frame_score`, use new module-level function of the same name instead
 * `get_aspect_ratio` has been removed from `scenedetect.platform` (use the `aspect_ratio` property of a `VideoStream` instead)
 * Backwards compatibility with v0.5 to avoid breaking most applications on release while still allowing performance improvements

#### Python Distribution Changes

 * *v0.6.0.3* - Fix missing package description
 * *v0.6.0.2* - Improve error messaging when OpenCV is not installed
 * *v0.6.0.1* - Fix original v0.6 release requiring `av` to run the `scenedetect` command

#### Known Issues

 * URL inputs are not supported by the `save-images` or `split-video` commands
 * Variable framerate videos (VFR) are not fully supported, and will yield incorrect timestamps ([#168](https://github.com/Breakthrough/PySceneDetect/issues/168))
 * The `detect-threshold` option `-l`/`--add-last-scene` cannot be disabled
 * Due to a switch from EXE to MSI for the Windows installer, you may have to uninstall older versions first before installing v0.6


----------------------------------------------------------------


## PySceneDetect 0.5

### 0.5.6.1 (October 11, 2021)

 * Fix crash when using `detect-content` or `detect-adaptive` with latest version of OpenCV (thanks @bilde2910)


### 0.5.6 (August 15, 2021)

#### Release Notes

 * **New detection algorithm**: `detect-adaptive` which works similar to `detect-content`, but with reduced false negatives during fast camera movement (thanks @scarwire and @wjs018)
 * Images generated by `save-images` can now be resized via the command line
 * Statsfiles now work properly with `detect-threshold`
 * Removed the `-p`/`--min-percent` option from `detect-threshold`
 * Add new option `-l`/`--luma-only` to `detect-content`/`detect-adaptive` to only consider brightness channel (useful for greyscale videos)

#### Changelog

 * [feature] New adaptive content detector algorithm `detect-adaptive` ([#153](https://github.com/Breakthrough/PySceneDetect/issues/153), thanks @scarwire and @wjs018)
 * [feature] Images generated with the `save-images` command (`scene_manager.save_images()` function in the Python API) can now be scaled or resized ([#160](https://github.com/Breakthrough/PySceneDetect/issues/160) and [PR #203](https://github.com/Breakthrough/PySceneDetect/pull/203), thanks @wjs018)
     * Images can be resized by a constant scaling factory using `-s`/`--scale` (e.g. `--scale 0.5` shrinks the height/width by half)
     * Images can be resized to a specified height (`-h`/`--height`) and/or width (`-w`/`--width`), in pixels; if only one is specified, the aspect ratio of the original video is kept
 * [api] Calling `seek()` on a `VideoManager` will now respect the end time if set
 * [api] The `split_video_` functions now return the exit code of invoking `ffmpeg` or `mkvmerge` ([#209](https://github.com/Breakthrough/PySceneDetect/issues/209), thanks  @AdrienLF)
 * [api] Removed the `min_percent` argument from `ThresholdDetector` as was not providing any performance benefit for the majority of use cases ([#178](https://github.com/Breakthrough/PySceneDetect/issues/178))
 * [bugfix] The `detect-threshold` command now works properly with a statsfile ([#211](https://github.com/Breakthrough/PySceneDetect/issues/211), thanks @jeremymeyers)
 * [bugfix] Fixed crash due to unhandled `TypeError` exception when using non-PyPI OpenCV packages from certain Linux distributions ([#220](https://github.com/Breakthrough/PySceneDetect/issues/220))
 * [bugfix] A warning is now displayed for videos which may not be decoded correctly, esp. VP9 ([#86](https://github.com/Breakthrough/PySceneDetect/issues/86), thanks @wjs018)
 * [api] A named logger is now used for both API and CLI logging instead of the root logger ([#205](https://github.com/Breakthrough/PySceneDetect/issues/205))

#### Known Issues

 * Variable framerate videos (VFR) are not fully supported, and will yield incorrect timestamps ([#168](https://github.com/Breakthrough/PySceneDetect/issues/168))
 * The `-l`/`--add-last-scene` option in `detect-threshold` cannot be disabled
 * Image sequences or URL inputs are not supported by the `save-images` or `split-video` commands (in v0.6 `save-images` works with image sequences)
 * Due to the use of truncation for frame number calculation, FrameTimecode objects may be off-by-one when constructed using a float value ([#268](https://github.com/Breakthrough/PySceneDetect/issues/268), fixed in v0.6)


### 0.5.5 (January 17, 2021)

#### Release Notes

 * One of the last major updates before transitioning to the new v0.6.x API
 * The `--min-scene-len`/`-m` option is now global rather than per-detector
 * There is a new global option `--drop-short-scenes` to go along with `-m`
 * Removed first row from statsfiles so it is a valid CSV file
 * The progress bar now correctly resizes when the terminal is resized
 * Image sequences and URLs are now supported for input via the CLI/API
 * Images exported using the `save-images` command are now resized to match the display aspect ratio
 * A new flag `-s`/`--skip-cuts` has been added to the `list-scenes` command to allow standardized processing
 * The functionality of `save-images` is now accessible via the Python API through the `save_images()` function in `scenedetect.scene_manager`
 * Under the `save-images` command, renamed `--image-frame-margin` to `--frame-margin`, added short option `-m`, and increased the default value from 0 to 1 due to instances of the last frame of a video being occasionally missed (set `-m 0` to restore original behaviour)

#### Changelog

 * [bugfix] Allow image sequences and URLs to be used as inputs ([#152](https://github.com/Breakthrough/PySceneDetect/issues/171) and [#188](https://github.com/Breakthrough/PySceneDetect/issues/188))
 * [bugfix] Pixel aspect ratio is now applied when using `save-images` ([#195](https://github.com/Breakthrough/PySceneDetect/issues/195))
 * [cli] Renamed `--image-frame-margin` to `--frame-margin` in `save-images` command, added short option `-m` as alias
 * [bugfix] Fix `save-images` command not saving the last frame by modifying seeking, as well as increasing default of `--frame-margin` from 0 to 1
 * [cli] Make `--min-scene-len` a global option rather than per-detector ([#131](https://github.com/Breakthrough/PySceneDetect/issues/131), thanks @tonycpsu)
 * [feature] Added `--drop-short-scenes` option to remove all scenes smaller than `--min-scene-len`, instead of merging them
 * [cli] Add `-s`/`--skip-cuts` option to `list-scenes` command to allow outputting a scene list CSV file as compliant with RFC 4180 ([#136](https://github.com/Breakthrough/PySceneDetect/issues/136))
 * [enhancement] Removed first row from statsfile to comply with RFC 4180, includes backwards compatibility so existing statsfiles can still be loaded ([#136](https://github.com/Breakthrough/PySceneDetect/issues/136))
 * [api] Add argument `include_cut_list` to `write_scene_list` method in `SceneManager` to support [#136](https://github.com/Breakthrough/PySceneDetect/issues/136)
 * [api] Removed unused argument base_timecode from `StatsManager.load_from_csv()` method
 * [api] Make the `base_timecode` argument optional on the `SceneManager` methods `get_scene_list()`, `get_cut_list()`, and `get_event_list()` ([#173](https://github.com/Breakthrough/PySceneDetect/issues/173))
 * [api] Support for live video stream callbacks by adding new `callback` argument to the `detect_scenes()` method of `SceneManager` ([#5](https://github.com/Breakthrough/PySceneDetect/issues/5), thanks @mhashim6)
 * [bugfix] Fix unhandled exception causing improper error message when a video fails to load on non-Windows platforms ([#192](https://github.com/Breakthrough/PySceneDetect/issues/192))
 * [enhancement] Enabled dynamic resizing for progress bar ([#193](https://github.com/Breakthrough/PySceneDetect/issues/193))
 * [enhancement] Always output version number via logger to assist with debugging ([#171](https://github.com/Breakthrough/PySceneDetect/issues/171))
 * [bugfix] Resolve RuntimeWarning when running as module ([#181](https://github.com/Breakthrough/PySceneDetect/issues/181))
 * [api] Add `save_images()` function to `scenedetect.scene_manager` module which exposes the same functionality as the CLI `save-images` command ([#88](https://github.com/Breakthrough/PySceneDetect/issues/88))
 * [api] Removed `close_captures()` and `release_captures()` functions from `scenedetect.video_manager` module

#### Known Issues

 * Certain non-PyPI OpenCV packages may cause a crash with the message `TypeError: isinstance() arg 2 must be a type or tuple of types` - as a workaround, install the Python OpenCV package by running `pip install scenedetect[opencv]` ([#220](https://github.com/Breakthrough/PySceneDetect/issues/220))
 * Image sequences or URL inputs are not supported by the `save-images` or `split-video` commands
 * Variable framerate videos (VFR) are not fully supported, and will yield incorrect timestamps ([#168](https://github.com/Breakthrough/PySceneDetect/issues/168))


### 0.5.4 (September 14, 2020)

#### Release Notes

 * Improved performance when using `time` and `save-images` commands
 * Improved performance of `detect-threshold` when using a small minimum percent
 * Fix crash when using `detect-threshold` with a statsfile
 * Fix crash when using `save-images` command under Python 2.7
 * Support for Python 3.3 and 3.4 has been deprecated (see below)

#### Changelog

 * [bugfix] fix `detect-threshold` crash when using statsfile ([#122](https://github.com/Breakthrough/PySceneDetect/issues/122))
 * [bugfix] fix `save-images` command under Python 2.7 ([#174](https://github.com/Breakthrough/PySceneDetect/issues/174), thanks @santiagodemierre)
 * [bugfix] gracefully exit and show link to FAQ when number of scenes is too large to split with mkvmerge on Windows (see [#164](https://github.com/Breakthrough/PySceneDetect/issues/164, thanks @alexboydray)
 * [enhancement] Improved seeking performance, greatly improves performance of the `time` and `save-images` commands ([#98](https://github.com/Breakthrough/PySceneDetect/issues/98) and [PR #163](https://github.com/Breakthrough/PySceneDetect/pull/163) - thanks @obroomhall)
 * [enhancement] improve `detect-threshold` performance when min-percent is less than 50%
 * [bugfix] Fixed issue where video loading would fail silently due to multiple audio tracks ([#179](https://github.com/Breakthrough/PySceneDetect/issues/179))
 * [general] Made `tqdm` a regular requirement and not an extra ([#180](https://github.com/Breakthrough/PySceneDetect/issues/180))
 * [general] Support for Python 3.3 and 3.4 has been deprecated. Newer builds may still work on these Python versions, but future releases are not tested against these versions. This decision was made as part of [#180](https://github.com/Breakthrough/PySceneDetect/issues/180)

#### Known Issues

 * Variable framerate videos are not supported properly currently (#168), a warning may be added in the next release to indicate when a VFR video is detected, until this can be properly resolved ([#168](https://github.com/Breakthrough/PySceneDetect/issues/168))


### 0.5.3 (July 12, 2020)

#### Release Notes

 * Resolved long-standing bug where `split-video` command would duplicate certain frames at the beginning/end of the output ([#93](https://github.com/Breakthrough/PySceneDetect/issues/93))
 * This was determined to be caused by copying (instead of re-encoding) the audio track, causing extra frames to be brought in when the audio samples did not line up on a frame boundary (thank you @joshcoales for your assistance)
 * Default behavior is to now re-encode audio tracks using the `aac` codec when using `split-video` (it can be overridden in both the command line and Python interface)
 * Improved timestamp accuracy when using `split-video` command to further reduce instances of duplicated or off-by-one frame issues
 * Fixed application crash when using the `-l`/`--logfile` argument

#### Changelog

 * [bugfix] Changed default audio codec from 'copy' to 'aac' when splitting scenes with `ffmpeg` to reduce frequency of frames from next scene showing up at the end of the current one when split using `ffmpeg` (see [#93](https://github.com/Breakthrough/PySceneDetect/issues/93), [#159](https://github.com/Breakthrough/PySceneDetect/issues/159), and [PR #166](https://github.com/Breakthrough/PySceneDetect/pull/166) - thank you everyone for your assistance, especially joshcoales, amvscenes, jelias, and typoman). If this still occurs, please provide any information you can by [filing a new issue on Github](https://github.com/Breakthrough/PySceneDetect/issues/new/choose).
  * [enhancement] `video_splitter` module now has completed documentation
  * [bugfix] improve timestamp accuracy using the `split-video` command due to timecode formatting
  * [bugfix] fix crash when supplying `-l`/`--logfile` argument (see [#169](https://github.com/Breakthrough/PySceneDetect/issues/169), thanks @typoman)

#### Known Issues

 * Seeking through long videos is inefficient, causing the `time` and `save-images` command to take a long time to run.  This will be resolved in the next release (see [#98](https://github.com/Breakthrough/PySceneDetect/issues/98))
 * The `save-images` command causes PySceneDetect to crash under Python 2.7 (see [#174](https://github.com/Breakthrough/PySceneDetect/issues/174))
 * Using `detect-threshold` with a statsfile causes PySceneDetect to crash (see [#122](https://github.com/Breakthrough/PySceneDetect/issues/122))
 * Variable framerate videos are not supported properly currently (#168), a warning may be added in the next release to indicate when a VFR video is detected, until this can be properly resolved ([#168](https://github.com/Breakthrough/PySceneDetect/issues/168))
 * Videos with multiple audio tracks may not work correctly, see [this comment on #179](https://github.com/Breakthrough/PySceneDetect/issues/179#issuecomment-685252441) for a workaround using `ffmpeg` or `mkvmerge`


### 0.5.2 (March 29, 2020)

 * [enhancement] `--min-duration` now accepts a timecode in addition to frame number ([#128](https://github.com/Breakthrough/PySceneDetect/pull/128), thanks @tonycpsu)
 * [feature] Add `--image-frame-margin` option to `save-images` command to ignore a number of frames at the start/end of a scene ([#129](https://github.com/Breakthrough/PySceneDetect/pull/129), thanks @tonycpsu)
 * [bugfix] `--min-scene-len` option was not respected by first scene ([#105](https://github.com/Breakthrough/PySceneDetect/issues/105), thanks @charlesvestal)
 * [bugfix] Splitting videos with an analyzed duration only splits within analyzed area ([#106](https://github.com/Breakthrough/PySceneDetect/issues/106), thanks @charlesvestal)
 * [bugfix] Improper start timecode applied to the `split-video` command when using `ffmpeg` ([#93](https://github.com/Breakthrough/PySceneDetect/issues/93), thanks @typoman)
 * [bugfix] Added links and filename sanitation to html output ([#139](https://github.com/Breakthrough/PySceneDetect/issues/139) and [#140](https://github.com/Breakthrough/PySceneDetect/issues/140), thanks @wjs018)
 * [bugfix] UnboundLocalError in `detect_scenes` when `frame_skip` is larger than 0 ([#126](https://github.com/Breakthrough/PySceneDetect/issues/126), thanks @twostarxx)


### 0.5.1.1 (August 3, 2019)

 * minor re-release of v0.5.1 which updates the setup.py file to return OpenCV as an optional dependency
 * to install from pip now with all dependencies: `pip install scenedetect[opencv,progress_bar]`
 * to install only PySceneDetect: `pip install scenedetect` (separate OpenCV installation required)
 * the release notes of v0.5.1 have been modified to include the prior command
 * no change to PySceneDetect program version
 * [feature] add `get_duration` method to VideoManager ([#109](https://github.com/Breakthrough/PySceneDetect/issues/109), thanks @arianaa30)


### 0.5.1 (July 20, 2019)

 * [feature] Add new `export-html` command to the CLI (thanks [@wjs018](https://github.com/Breakthrough/PySceneDetect/pull/104))
 * [bugfix] VideoManager read function failed on multiple videos (thanks [@ivan23kor](https://github.com/Breakthrough/PySceneDetect/pull/107))
 * [bugfix] Fix crash when no scenes are detected ([#79](https://github.com/Breakthrough/PySceneDetect/issues/79), thanks @raj6996)
 * [bugfix] Fixed OpenCV not getting installed due to missing dependency ([#73](https://github.com/Breakthrough/PySceneDetect/issues/73))
 * [enhance] When no scenes are detected, the whole video is now returned instead of nothing (thanks [@piercus](https://github.com/Breakthrough/PySceneDetect/pull/89))
 * Removed Windows installer due to binary packages now being available, and to streamline the release process (see [#102](https://github.com/Breakthrough/PySceneDetect/issues/102) for more information).  When you type `pip install scenedetect[opencv,progress_bar]`, all dependencies will be installed.


### 0.5 (August 31, 2018)

 * **major** release, includes stable Python API with examples and updated documentation
 * numerous changes to command-line interface with addition of sub-commands (see [the new manual](http://manual.scenedetect.com) for updated usage information)
 * [feature] videos are now split using `ffmpeg` by default, resulting in frame-perfect cuts (can still use `mkvmerge` by specifying the `-c`/`--copy` argument to the `split-video` command)
 * [enhance] image filename numbers are now consistent with those of split video scenes (PR #39, thanks [@e271828-](https://github.com/Breakthrough/PySceneDetect/pull/39))
 * [enhance] 5-10% improvement in processing performance due to reduced memory copy operations (PR #40, thanks [@elcombato](https://github.com/Breakthrough/PySceneDetect/pull/40))
 * [enhance] updated exception handling to raise proper standard exceptions (PR #37, thanks [@talkain](https://github.com/Breakthrough/PySceneDetect/pull/37))
 * several fixes to the documentation, including improper dates and outdated CLI arguments (PR #26 and #, thanks [@elcombato](https://github.com/Breakthrough/PySceneDetect/pull/26), and [@colelawrence](https://github.com/Breakthrough/PySceneDetect/pull/33))
 * *numerous* other PRs and issues/bug reports that have been fixed - there are too many to list individually here, so I want to extend a big thank you to **everyone** who contributed to making this release better
 * [enhance] add Sphinx-generated API documentation (available at: http://manual.scenedetect.com)
 * [project] move from BSD 2-clause to 3-clause license


----------------------------------------------------------------


## PySceneDetect 0.4

### 0.4 (January 14, 2017)

 * major release, includes integrated scene splitting via mkvmerge, changes meaning of `-o` / `--output` option
 * [feature] specifying `-o OUTPUT_FILE.mkv` will now automatically split the input video, generating a new video clip for each detected scene in sequence, starting with `OUTPUT_FILE-001.mkv`
 * [enhance] CSV file output is now specified with the `-co` / `--csv-output` option (*note, used to be `-o` in versions of PySceneDetect < 0.4*)


----------------------------------------------------------------


## PySceneDetect 0.3-beta

### 0.3.6 (January 12, 2017)

 * [enhance]  performance improvement when using `--frameskip` option (thanks [@marcelluzs](https://github.com/marcelluzs))
 * [internal] moved application state and shared objects to a consistent interface (the `SceneManager` object) to greatly reduce the number of required arguments for certain API functions
 * [enhance]  added installer for Windows builds (64-bit only currently)


### 0.3.5 (August 2, 2016)

 * [enhance]  initial release of portable build for Windows (64-bit only), including all dependencies
 * [bugfix]   fix unrelated exception thrown when video could not be loaded (thanks [@marcelluzs](https://github.com/marcelluzs))
 * [internal] fix variable name typo in API documentation


### 0.3.4 (February 8, 2016)

 * [enhance] add scene length, in seconds, to output file (`-o`) for easier integration with `ffmpeg`/`libav`
 * [enhance] improved performance of content detection mode by caching intermediate HSV frames in memory (approx. 2x faster)
 * [enhance] show timecode values in terminal when using extended output (`-l`)
 * [feature] add fade bias option (`-fb` / `--fade-bias`) to command line (threshold mode only)


### 0.3.3 (January 27, 2016)

 * [bugfix]   output scenes are now correctly written to specified output file when using -o flag (fixes #11)
 * [bugfix]   fix indexing exception when using multiple scene detectors and outputting statistics
 * [internal] distribute package on PyPI, version move from beta to stable
 * [internal] add function to convert frame number to formatted timecode
 * [internal] move file and statistic output to Python `csv` module


### 0.3.2-beta (January 26, 2016)

 * [feature] added `-si` / `--save-images` flag to enable saving the first and last frames of each detected scene as an image, saved in the current working directory with the original video filename as the output prefix
 * [feature] added command line options for setting start and end times for processing (`-st` and `-et`)
 * [feature] added command line option to specify maximum duration to process (`-dt`, overrides `-et`)


### 0.3.1-beta (January 23, 2016)

 * [feature] added downscaling/subsampling option (`-df` / `--downscale-factor`) to improve performance on higher resolution videos
 * [feature] added frameskip option (`-fs` / `--frame-skip`) to improve performance on high framerate videos, at expense of frame accuracy and possible inaccurate scene cut prediction
 * [enhance]  added setup.py to allow for one-line installation (just run `python setup.py install` after downloading and extracting PySceneDetect)
 * [internal] additional API functions to remove requirement on passing OpenCV video objects, and allow just a file path instead


### 0.3-beta (January 8, 2016)

 * major release, includes improved detection algorithms and complete internal code refactor
 * [feature]  content-aware scene detection using HSV-colourspace based algorithm (use `-d content`)
 * [enhance]  added CLI flags to allow user changes to more algorithm properties
 * [internal] re-implemented threshold-based scene detection algorithm under new interface
 * [internal] major code refactor including standard detection algorithm interface and API
 * [internal] remove statistics mode until update to new detection mode interface


----------------------------------------------------------------


## PySceneDetect 0.2-alpha

### 0.2.4-alpha (December 22, 2015)
 * [bugfix] updated OpenCV compatibility with self-reported version on some Linux distributions


### 0.2.3-alpha (August 7, 2015)
 * [bugfix]  updated PySceneDetect to work with latest OpenCV module (ver > 3.0)
 * [bugfix]  added compatibility/legacy code for older versions of OpenCV
 * [feature] statsfile generation includes expanded frame metrics


### 0.2.2-alpha (November 25, 2014)

 * [feature] added statistics mode for generating frame-by-frame analysis (-s / --statsfile flag)
 * [bugfix]  fixed improper timecode conversion


### 0.2.1-alpha (November 16, 2014)

 * [enhance] proper timecode format (HH:MM:SS.nnnnn)
 * [enhance] one-line of CSV timecodes added for easy splitting with external tool


### 0.2-alpha (June 9, 2014)

 * [enhance] now provides discrete scene list (in addition to fades)
 * [feature] ability to output to file (-o / --output flag)


----------------------------------------------------------------


## PySceneDetect 0.1-alpha

### 0.1-alpha (June 8, 2014)

 * first public release
 * [feature] threshold-based fade in/out detection


----------------------------------------------------------------


Development
==========================================================

## PySceneDetect 0.7 (In Development)

### Release Notes

PySceneDetect is a major breaking release which overhauls how timestamps are handled throughout the API. This allows PySceneDetect to properly process variable framerate (VFR) videos. A significant amount of technical debt has been addressed, including removal of deprecated or overly complicated APIs.

Although there have been minimal changes to most API examples, there are several breaking changes. Applications written for the 0.6 API *may* require modification to work with the new API.

### CLI Changes

### CLI Changes

- [feature] [WIP] New `save-xml` command supports saving scenes in Final Cut Pro format [#156](https://github.com/Breakthrough/PySceneDetect/issues/156)
- [refactor] Remove deprecated `-d`/`--min-delta-hsv` option from `detect-adaptive` command


### API Changes

#### Breaking

> Note: Imports that break when upgrading to 0.7 can usually be resolved by importing from `scenedetect` directly, rather than a submodule. The package structure has changed significantly in 0.7.

 * Replace `frame_num` parameter (`int`) with `timecode` (`FrameTimecode`) in `SceneDetector` interface (#168)[https://github.com/Breakthrough/PySceneDetect/issues/168]:
      * The detector interface: `SceneDetector.process_frame()` and `SceneDetector.post_process()`
      * Statistics: `StatsManager.get_metrics()`, `StatsManager.set_metrics()`, and `StatsManager.metrics_exist()`
 * Move existing functionality to new submodules:
      * `scenedetect.scene_detector` moved to `scenedetect.detector`
      * `scenedetect.frame_timecode` moved to `scenedetect.common`
      * Output functionality from `scenedetect.scene_manager` moved to `scenedetect.output` [#463](https://github.com/Breakthrough/PySceneDetect/issues/463)
      * `scenedetect.video_splitter` moved to `scenedetect.output.video` [#463](https://github.com/Breakthrough/PySceneDetect/issues/463)
 * Remove deprecated module `scenedetect.video_manager`, use [the `scenedetect.open_video()` function](https://www.scenedetect.com/docs/head/api.html#scenedetect.open_video) instead
 * Remove deprecated parameter `base_timecode` from various functions, there is no need to provide it
 * Remove deprecated parameter `video_manager` from various functions, use `video` parameter instead
 * `FrameTimecode` fields `frame_num` and `framerate` are now read-only properties, construct a new `FrameTimecode` to change them
 * Remove `FrameTimecode.previous_frame()` method
 * Remove `SceneDetector.is_processing_required()` method, already had no effect in v0.6 as part of deprecation
 * `SceneDetector` instances can now assume they always have frame data to process when `process_frame` is called
 * Remove deprecated `SparseSceneDetector` interface
 * Remove deprecated `SceneManager.get_event_list()` method
 * Remove deprecated `AdaptiveDetector.get_content_val()` method (the same information can be obtained using a `StatsManager`)
 * Remove deprecated `AdaptiveDetector` constructor argument `min_delta_hsv` (use `min_content_val` instead)
 * Remove `advance` parameter from `VideoStream.read()` (was always set to `True`, callers should handle caching frames now if required)

 #### General

 * Deprecated functionality preserved from v0.6 now uses the `warnings` module
 * Add properties to access `frame_num`, `framerate`, and `seconds` from `FrameTimecode` instead of getter methods
 * Add new `Timecode` type to represent frame timings in terms of the video's source timebase
