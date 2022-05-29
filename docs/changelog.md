
PySceneDetect Releases
==========================================================

## PySceneDetect 0.6

### 0.6 (TBD)

#### Release Notes

PySceneDetect v0.6 is a **major breaking change** including better performance, configuration file support, and a more ergonomic API.  The new **minimum Python version is now 3.6**. See the [Migration Guide](https://manual.scenedetect.com/en/v0.6/api/migration_guide.html) for information on how to port existing applications to the new API.  Most users will see performance improvements after updating, and changes to the command-line are not expected to break most workflows.

The main goals of v0.6 are reliability and performance. To achieve this required several breaking changes.  The video input API was refactored, and *many* technical debt items were addressed. This should help the eventual transition to the first planned stable release (v1.0) where the goal is an improved scene detection API.

Both the Windows installer and portable distributions now include signed executables. Many thanks to SignPath, AppVeyor, and AdvancedInstaller for their support.

#### Changelog

**Overview:**

 * Major performance improvements on multicore systems
 * [Configuration file support](http://scenedetect.com/projects/Manual/en/v0.6/cli/config_file.html) via command line option or user settings folder
 * Support for multiple video backends, PyAV is now supported in addition to OpenCV
 * Breaking API changes to `VideoManager` (replaced with `VideoStream`), `StatsManager`, and `save_images()`
    * See the [Migration Guide](https://manual.scenedetect.com/en/v0.6/api/migration_guide.html) for details on how to update from v0.5.x
    * A backwards compatibility layer has been added to prevent most applications from breaking, will be removed in a future release
 * Support for Python 2.7 has been dropped, minimum supported Python version is 3.6
 * Support for OpenCV 2.x has been dropped, minimum OpenCV version is 3.x
 * Windows binaries are now signed, thanks [SignPath.io](https://signpath.io/) (certificate by [SignPath Foundation](https://signpath.org/))

**Command-Line Changes:**

 * Configuration files are now supported, [see documentation for details](http://scenedetect.com/projects/Manual/en/v0.6/cli/config_file.html)
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

 * New `detect()` function performs scene detection on a video path, [see example here](http://manual.scenedetect.com/en/v0.6/api.html#quickstart)
 * New `open_video()` function to handle video input, [see example here](http://manual.scenedetect.com/en/v0.6/api.html#example)
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

#### Known Issues

 * URL inputs are not supported by the `save-images` or `split-video` commands
 * Variable framerate videos (VFR) are not fully supported, and will yield incorrect timestamps ([#168](https://github.com/Breakthrough/PySceneDetect/issues/168))
 * The `detect-threshold` option `-l`/`--add-last-scene` cannot be disabled


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
 * [enhancement] Always ouptut version number via logger to assist with debugging ([#171](https://github.com/Breakthrough/PySceneDetect/issues/171))
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
 * Default behavior is to now re-encode audio tracks using the `aac` codec when using `split-video` (it can be overriden in both the command line and Python interface)
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
