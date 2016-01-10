
# Obtaining PySceneDetect

PySceneDetect is written in a portable manner, and works cross-platform wherever a Python interpreter and OpenCV can run.

## Requirements

Currently, binaries are not provided for PySceneDetect, so you will need:

 - [Python 2 / 3](https://www.python.org/) (tested on 2.7.X, untested but should work on 3.X)
 - OpenCV Python Module (usually found in Linux package repos as `python-opencv`, Windows users can find [prebuilt binaries for Python 2.7 here](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv))
 - [Numpy](http://sourceforge.net/projects/numpy/)

To ensure you have all the requirements, open a `python` interpreter, and ensure you can `import numpy` and `import cv2` without any errors.  You can download a test video and view the expected output [from the resources branch](https://github.com/Breakthrough/PySceneDetect/tree/resources/tests) (see the end of the Usage section below for details).


## Download

### Source (All Platforms - Windows, Linux, Mac)

The latest version of PySceneDetect (`v0.3-beta`) can be [**downloaded here**](https://github.com/Breakthrough/PySceneDetect/releases) (from the Github releases page).

### Binaries (Windows 32/64-bit)

Currently, binaries are not provided, but are being planned for the future (likely using PyInstaller).
