
## <span class="fa fa-bug"></span>&nbsp; Bug Reports

Bugs, issues, features, and improvements to PySceneDetect are handled through [the issue tracker on Github](https://github.com/Breakthrough/PySceneDetect/issues).  If you run into any bugs using PySceneDetect, please [create a new issue](https://github.com/Breakthrough/PySceneDetect/issues/new).  Provide as much detail as you can - include an example that clearly demonstrates the problem (if possible), and make sure to include any/all relevant program output or error messages.

When submitting bug reports, please provide debug logs by adding `-l BUG_REPORT.txt` to your `scenedetect` command, and attach the generated `BUG_REPORT.txt` file.

Before opening a new issue, please do [search for any existing issues](https://github.com/Breakthrough/PySceneDetect/issues?q=) (both open and closed) which might report similar issues/bugs to avoid creating duplicate entries.  If you do find a duplicate report, feel free to add any additional information you feel may be relevant.

## <span class="fa fa-cogs"></span>&nbsp; Contributing to Development

The development of PySceneDetect is done on the Github Repo, guided by [the feature roadmap](features.md).  Code you wish to submit should be attached to a dedicated entry in [the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues?q=) (with the appropriate tags for bugfixes, new features, enhancements, etc...), and allows for easier communication regarding development structure.  Feel free to create a new entry if required, as some planned features or bugs/issues may not yet exist in the tracker.

All submitted code should be linted with pylint, and follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) as closely as possible.  Also, ensure that you search through [all existing issues](https://github.com/Breakthrough/PySceneDetect/issues?q=) (both open and closed) beforehand to avoid creating duplicate entries.

Note that PySceneDetect is released under the BSD 3-Clause license, and submitted code should comply with this license (see [License & Copyright Information](copyright.md) for details).

## <span class="fa fa-cogs"></span>&nbsp; Features That Need Help

The following is a "wishlist" of features which PySceneDetect eventually should have, but does not currently due to lack of resources.  Anyone who is able to contribute in any capacity to these items is encouraged to do so by starting a dialogue by opening a new issue on Github as per above.

### GUI

A graphical user interface will be crucial for making PySceneDetect approchable by a wider audience.  There have been several suggested designs, but nothing concrete has been developed yet.  Any proposed solution for the GUI should work across Windows, Linux, and OSX.

### Localization

PySceneDetect currently is not localized for other languages.  Anyone who can help improve how localization can be approached for development material is encouraged to contribute in any way possible.  Whether it is the GUI program, the command line interface, or documentation, localization will allow PySceneDetect to be used by much more users in their native languages.

### Automatic Threshold / Peak Detection

The `detect-content` command requires a manual threshold to be set currently.  Methods to use peak detection to dynamically determine when scene cuts occur would allow for the program to work with a much wider amount of material without requiring manual tuning, but would require statistical analysis.

Ideally, this would be something like `-threshold=auto` as a default.

### Advanced Detection Strategies

Research into advanced scene detection for content detection would be most useful, perhaps in terms of histogram analysis or edge detection.  This could be integrated into the existing `detect-content` command, or be a separate command.  The real blocker here is achieving reasonable performance utilizing the current software architecture.

There are many open issues on the issue tracker that contain reference implementations contributed by various community members.  There are already several concepts which are proven to be viable candidates for production, but still require some degree optimization.
