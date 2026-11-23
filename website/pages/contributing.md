# Contributing & Support

## Reporting Bugs

Report bugs and request features on [the PySceneDetect issue tracker on GitHub](https://github.com/Breakthrough/PySceneDetect/issues). Before [opening a new issue](https://github.com/Breakthrough/PySceneDetect/issues/new/choose), search [existing issues](https://github.com/Breakthrough/PySceneDetect/issues?q=) to check for known fixes or workarounds. Adding reproduction details to an existing report is also helpful.

## Contributing Code

PySceneDetect development takes place at [github.com/Breakthrough/PySceneDetect](https://github.com/Breakthrough/PySceneDetect). Pull requests are welcome. When possible, link each pull request to an entry on [the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues?q=).

Before submitting a pull request, check that your changes meet these requirements:

- All unit tests pass (`pytest`).
- Linting and formatting checks pass (`ruff check` and `ruff format`).
- New public APIs include type hints and docstrings with `Arguments:` / `Returns:` sections.

When working on repository branches, use a descriptive prefix matching the change: `feature/<name>`, `issue/<num>-<desc>`, `fix/<name>`, `docs/<name>`, or `website/<name>` for website updates.

PySceneDetect is released under the BSD 3-Clause License, and all submitted code must comply with this license (see [License & Copyright](copyright.md)).

## Features That Need Help

These areas are open for community contributions. Open an issue on GitHub to discuss an approach before writing a large change.

### Flash suppression

Bright flashes and fast camera movement can still trigger false cuts in some videos. Contributions that improve both accuracy and speed for these cases are welcome.

### Automatic thresholding

`detect-content` currently requires a fixed threshold. Peak-detection methods that estimate a threshold automatically (for example, `--threshold=auto`) would reduce manual tuning across diverse videos.

### Dissolve detection

Detection accuracy on slow dissolves varies with transition length and detector settings. Better dissolve detection with low performance overhead remains an open problem.

### New detectors

Research and prototypes for faster or more accurate detectors are always welcome.

### Graphical user interface (GUI)

A cross-platform GUI for Windows, Linux, and macOS would make PySceneDetect easier for non-technical users. No official GUI has been built yet.

### Localization

PySceneDetect is currently available only in English. Contributions to support localization in the CLI, documentation, or a future GUI will help more people use PySceneDetect in their own language.

## Project Support and Credits

PySceneDetect is built and distributed with help from the tools, services, and contributors below. Listing these services gives credit for their support and does not imply endorsement.

### Tools and services

- [GitHub](https://github.com/): Git hosting, website hosting, code review, issue tracking, and CI builds.
- [AppVeyor](https://www.appveyor.com/): Windows portable and MSI builds.
- [Advanced Installer](https://www.advancedinstaller.com/): Windows MSI installer packaging.
- [SignPath](https://signpath.io/): free code signing for Windows builds.

### Community contributions

Thank you to everyone who has submitted bug reports, feature requests, documentation fixes, and pull requests. You can view the contributor list on [the GitHub contributors page](https://github.com/Breakthrough/PySceneDetect/graphs/contributors).

### Donations

PySceneDetect does not accept monetary donations. The best ways to support the project are reporting bugs, improving docs, and contributing code. If you can offer tools, hosting, or testing resources that help development, open an issue on GitHub or reach out through [bcastell.com/contact](https://bcastell.com/contact/).
