
PySceneDetect Changelog
==========================================================


### 0.4-beta-dev [in development]
 * [enhance]  added configuration file to support more options and cleanup/remove some command-line arguments
 * [feature]  user-selectable fade bias when using threshold-based detection
 * [internal] preperation for automated splitting via integration with supported tools (ffmpeg, avconv, mkvmerge)
 * [internal] framework for edge-detection and dissolve/fade based scene cut algorithms for future versions


### 0.3-beta

 * major release, includes improved detection algorithms and complete internal code refactor
 * [feature]  content-aware scene detection using HSV-colourspace based algorithm (use `-d content`)
 * [enhance]  added CLI flags to allow user changes to more algorithm properties
 * [internal] re-implemented threshold-based scene detection algorithm under new interface
 * [internal] major code refactor including standard detection algorithm interface and API


### 0.2.4-alpha
 * [bugfix] updated OpenCV compatibility with self-reported version on some Linux distributions


### 0.2.3-alpha
 * [bugfix]  updated PySceneDetect to work with latest OpenCV module (ver > 3.0)
 * [bugfix]  added compatibility/legacy code for older versions of OpenCV
 * [feature] statsfile generation includes expanded frame metrics


### 0.2.2-alpha

 * [feature] added statistics mode for generating frame-by-frame analysis (-s / --statsfile flag)
 * [bugfix]  fixed improper timecode conversion


### 0.2.1-alpha

 * [enhance] proper timecode format (HH:MM:SS.nnnnn)
 * [enhance] one-line of CSV timecodes added for easy splitting with external tool


### 0.2-alpha

 * [enhance] now provides discrete scene list (in addition to fades)
 * [feature] ability to output to file (-o / --output flag)


### 0.1-alpha

 * initial release
 * [feature] threshold-based fade in/out detection


PySceneDetect Changelog
==========================================================


### 0.3-alpha-dev [in development]

 * preperation for beta release (incl. content-aware analysis and major code refactor)
 * [wip] content-aware scene detection
 * [wip] thumbnail generation support


### 0.2.4-alpha
 * [bugfix] updated OpenCV compatibility with self-reported version on some Linux distributions


### 0.2.3-alpha
 * [bugfix]  updated PySceneDetect to work with latest OpenCV module (ver > 3.0)
 * [bugfix]  added compatibility/legacy code for older versions of OpenCV
 * [feature] statsfile generation includes expanded frame metrics


### 0.2.2-alpha

 * [feature] added statistics mode for generating frame-by-frame analysis (-s / --statsfile flag)
 * [bugfix]  fixed improper timecode conversion


### 0.2.1-alpha

 * [enhance] proper timecode format (HH:MM:SS.nnnnn)
 * [enhance] one-line of CSV timecodes added for easy splitting with external tool


### 0.2-alpha

 * [enhance] now provides discrete scene list (in addition to fades)
 * [feature] ability to output to file (-o / --output flag)


### 0.1-alpha

 * initial release
 * [feature] threshold-based fade in/out detection
