
## PySceneDetect Features

### Current Features

 - output-suppression (quiet) mode for better automation with external scripts/programs
 - detects fade-in and fade-out based on user-defined threshold
 - exports list of scenes to .CSV file (both timecodes and frame numbers) (-o)
 - exports timecodes in mkvmerge format: HH:MM:SS.nnnnn, comma-separated

#### Available Scene Detection Methods:

 - threshold scene detection analyzes video for changes in average frame intensity/brightness
 - content-aware scene detection based on changes between frames in the HSV color space


----------------

## Version Roadmap

### Features in Development

 - statistics/analysis mode to export frame-by-frame video metrics (-s)
 - adaptive or user-defined bias for fade in/out interpolation
 - additional timecode formats

### Planned Features

 - export scenes in chapter/XML format
 - improve robustness of content-aware detection by combining with edge detection (similar to MATLAB-based scene ch
 - detector)
 - interactive/guided mode, eventually moving to a graphical interface
