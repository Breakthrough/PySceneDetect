
# Obtaining PySceneDetect

PySceneDetect is completely free software, and can be downloaded from the links below.  See the (license and copyright information](copyright.md) page for details.  PySceneDetect is written in a portable manner, and works cross-platform wherever a Python interpreter and OpenCV can run.  If you have problems running PySceneDetect, ensure that you have all the required dependencies listed in the System Requirements section below.


## Download

### Source (All Platforms - Windows, Linux, Mac)

[**Click here**](https://github.com/Breakthrough/PySceneDetect/releases) to download the latest release of PySceneDetect.  The current stable version is `v0.3-beta`.

Once you've downloaded the source files, extract them to a location of your choice.  You can run PySceneDetect locally from that folder (by calling `scenedetect.py`), or follow the instructions in the Installation section below so you can run `scenedetect` anywhere.


## System Requirements

Currently, binaries are not provided for PySceneDetect, so you will need:

 - [Python 2 / 3](https://www.python.org/) (tested on 2.7.X, untested but should work on 3.X)
 - OpenCV Python Module (usually found in Linux package repos as `python-opencv`, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://sourceforge.net/projects/numpy/)

To ensure you have all the requirements, open a `python` interpreter, and ensure you can `import numpy` and `import cv2` without any errors.  You can download a test video and view the expected output [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests) (see the end of the Usage section below for details).


## Installation

Go to the folder you extracted PySceneDetect to, and run the following command (may require root):

```rst
python setup.py install
```

Once complete, PySceneDetect should be installed, and you should be able to run the `scenedetect` command.  To test it out, try calling:

```rst
scenedetect --version
```

To get familiar with PySceneDetect, try running `scenedetect --help`, or continue onwards to the [Getting Started: Basic Usage](examples/usage.md) section.  If you encounter any runtime errors while running PySceneDetect, ensure that you have all the required dependencies listed in the System Requirements section above (again, you should be able to `import numpy` and `import cv2`).  PySceneDetect is still beta software, so feel free to [report any bugs or share some feature requests/ideas](contributing.md) and help make PySceneDetect even better.

