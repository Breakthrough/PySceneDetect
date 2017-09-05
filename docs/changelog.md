
PySceneDetect Changelog
==========================================================

## 0.5 (In Development)

 * under development currently, release planned for late 2017, can be tested via latest Github commit (warning, may be unstable)
 * major release, includes stable Python API with examples and updated documentation
 * [enhance] image filename numbers are now consistent with those of split video scenes (thanks [@e271828-](https://github.com/e271828-))
 * [enhance] 5-10% improvement in processing performance due to reduced memory copy operations (thanks [@elcombato](https://github.com/elcombato))
 * [internal] updated exception handling to raise proper standard exceptions (thanks [@talkain](https://github.com/talkain))
 * several fixes to the documentation, including improper dates and outdated CLI arguments (thanks [@elcombato](https://github.com/elcombato) and [@colelawrence](https://github.com/colelawrence))


## 0.4 (January 14, 2017) &nbsp;<span class="fa fa-tags"></span>

 * major release, includes integrated scene splitting via mkvmerge, changes meaning of `-o` / `--output` option
 * [feature] specifying `-o OUTPUT_FILE.mkv` will now automatically split the input video, generating a new video clip for each detected scene in sequence, starting with `OUTPUT_FILE-001.mkv`
 * [enhance] CSV file output is now specified with the `-co` / `--csv-output` option (*note, used to be `-o` in versions of PySceneDetect < 0.4*)


### 0.3.6 (January 12, 2017)

 * [enhance]  speed improvement when using `--frameskip` option
 * [internal] moved application state and shared objects to a consistent interface (the `SceneManager` object) to greatly reduce the number of required arguments for certain API functions
 * [enhance]  added installer for Windows builds (64-bit only currently)


### 0.3.5 (August 2, 2016)

 * [enhance]  initial release of portable build for Windows (64-bit only), including all dependencies
 * [bugfix]   fix unrelated exception thrown when video could not be loaded
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

