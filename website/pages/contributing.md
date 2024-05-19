
## <span class="fa fa-bug"></span>&nbsp; Bug Reports

Bugs, issues, features, and improvements to PySceneDetect are handled through [the issue tracker on Github](https://github.com/Breakthrough/PySceneDetect/issues).  If you run into any bugs using PySceneDetect, please [create a new issue](https://github.com/Breakthrough/PySceneDetect/issues/new/choose).

Try to [find an existing issue](https://github.com/Breakthrough/PySceneDetect/issues?q=) before creating a new one, as there may be a workaround posted there.  Additional information is also helpful for existing reports.

## <span class="fa fa-cogs"></span>&nbsp; Contributing to Development

Development of PySceneDetect happens on [github.com/Breakthrough/PySceneDetect](https://github.com/Breakthrough/PySceneDetect).  Pull requests are accepted and encouraged.  Where possible, PRs should be submitted with a dedicated entry in [the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues?q=).  Issues and features are typically grouped into version milestones.

The following checklist covers the basics of pre-submission requirements:

 - Code passes all unit tests (run `pytest`)
 - Code is formatted (run `python -m yapf -i -r scenedetect/ tests/` to format in place)
 - Generally follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

Note that PySceneDetect is released under the BSD 3-Clause license, and submitted code should comply with this license (see [License & Copyright Information](copyright.md) for details).

## <span class="fa fa-cogs"></span>&nbsp; Features That Need Help

The following is a "wishlist" of features which PySceneDetect eventually should have, but does not currently due to lack of resources.  Anyone who is able to contribute in any capacity to these items is encouraged to do so by starting a dialogue by opening a new issue on Github as per above.

### Flash Suppression

Some detection methods struggle with bright flashes and fast camera movement.  The detection pipeline has some filters in place to deal with these cases, but there are still drawbacks.  We are actively seeking methods which can improve both performance and accuracy in these cases.

### Automatic Thresholding

The `detect-content` command requires a manual threshold to be set currently.  Methods to use peak detection to dynamically determine when scene cuts occur would allow for the program to work with a much wider amount of material without requiring manual tuning, but would require statistical analysis.

Ideally, this would be something like `-threshold=auto` as a default.

### Dissolve Detection

Depending on the length of the dissolve and parameters being used, detection accuracy for these types of cuts can vary widely.  A method to improve accuracy with minimal performance loss is an open problem.

### Advanced Strategies

Research into detection methods and performance are ongoing. All contributions in this regard are most welcome.

### GUI

A graphical user interface will be crucial for making PySceneDetect approchable by a wider audience.  There have been several suggested designs, but nothing concrete has been developed yet.  Any proposed solution for the GUI should work across Windows, Linux, and OSX.

### Localization

PySceneDetect currently is not localized for other languages.  Anyone who can help improve how localization can be approached for development material is encouraged to contribute in any way possible.  Whether it is the GUI program, the command line interface, or documentation, localization will allow PySceneDetect to be used by much more users in their native languages.