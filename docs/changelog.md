
PySceneDetect Releases
==========================================================


### 0.5.3 (July 12, 2020) &nbsp;<span class="fa fa-tags"></span>

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
 * Variable framerate videos are not supported properly currently (#168), a warning may be added in the next release to indicate when a VFR video is detected, until this can be properly resolved ([#168](https://github.com/Breakthrough/PySceneDetect/issues/168))
 * Videos with multiple audio tracks may not work correctly, see [this comment on #179](https://github.com/Breakthrough/PySceneDetect/issues/179#issuecomment-685252441) for a workaround using `ffmpeg` or `mkvmerge`


### 0.5.2 (March 29, 2020)

 * [enhancement] `--min-duration` now accepts a timecode in addition to frame number ([#128](https://github.com/Breakthrough/PySceneDetect/pull/128), thanks @tonycpsu)
 * [feature] Add `--image-frame-margin` option to `save-images` command to ignore a number of frames at the start/end of a scene ([#129](https://github.com/Breakthrough/PySceneDetect/pull/129), thanks @tonycpsu)
 * [bugfix] `--min-scene-len` option was not respected by first scene ([#105](https://github.com/Breakthrough/PySceneDetect/issues/105), thanks @charlesvestal)
 * [bugfix] Splitting videos with an analyzed duration only splits within analyzed area ([#106](https://github.com/Breakthrough/PySceneDetect/issues/106), thanks @charlesvestal)
 * [bugfix] Improper start timecode applied to the `split-video` command when using `ffmpeg` ([#93](https://github.com/Breakthrough/PySceneDetect/issues/93), thanks @typoman)
 * [bugfix] Added links and filename sanitation to html output ([#139](https://github.com/Breakthrough/PySceneDetect/issues/139) and [#140](https://github.com/Breakthrough/PySceneDetect/issues/140), thanks @wsj018)
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


## 0.5 (August 31, 2018)

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


## 0.4 (January 14, 2017)

 * major release, includes integrated scene splitting via mkvmerge, changes meaning of `-o` / `--output` option
 * [feature] specifying `-o OUTPUT_FILE.mkv` will now automatically split the input video, generating a new video clip for each detected scene in sequence, starting with `OUTPUT_FILE-001.mkv`
 * [enhance] CSV file output is now specified with the `-co` / `--csv-output` option (*note, used to be `-o` in versions of PySceneDetect < 0.4*)


----------------------------------------------------------------


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


## 0.3-beta (January 8, 2016)

 * major release, includes improved detection algorithms and complete internal code refactor
 * [feature]  content-aware scene detection using HSV-colourspace based algorithm (use `-d content`)
 * [enhance]  added CLI flags to allow user changes to more algorithm properties
 * [internal] re-implemented threshold-based scene detection algorithm under new interface
 * [internal] major code refactor including standard detection algorithm interface and API
 * [internal] remove statistics mode until update to new detection mode interface


----------------------------------------------------------------


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


## 0.2-alpha (June 9, 2014)

 * [enhance] now provides discrete scene list (in addition to fades)
 * [feature] ability to output to file (-o / --output flag)


----------------------------------------------------------------


## 0.1-alpha (June 8, 2014)

 * first public release
 * [feature] threshold-based fade in/out detection

