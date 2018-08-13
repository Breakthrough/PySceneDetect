
# Obtaining PySceneDetect

PySceneDetect is completely free software, and can be downloaded from the links below.  See the [license and copyright information](copyright.md) page for details.  If you have trouble running PySceneDetect, ensure that you have all the required dependencies listed in the [Installing Dependencies](#installing-dependencies) section below.


## Download

### Windows Standalone (64-bit Only) &nbsp; <span class="wy-text-neutral"><span class="fa fa-windows"></span></span>

<div class="important">
<h3 class="wy-text-neutral"><span class="fa fa-forward wy-text-info"></span> Latest Release: <b class="wy-text-neutral">v0.4</b> <i>[OLD]</i></h3>
<h4 class="wy-text-neutral"><span class="fa fa-calendar wy-text-info"></span>&nbsp; Release Date:&nbsp; <b>January 14, 2017</b></h4>
<a href="https://github.com/Breakthrough/PySceneDetect/releases/download/v0.4/PySceneDetect-0.4-win64.msi" class="btn btn-success" style="margin-bottom:8px;" role="button"><span class="fa fa-download"></span>&nbsp; <b>Installer</b>&nbsp;&nbsp;(recommended)</a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="https://github.com/Breakthrough/PySceneDetect/releases/download/v0.4/PySceneDetect-0.4-win64-portable.zip" class="btn btn-success" style="margin-bottom:8px;" role="button"><span class="fa fa-download"></span>&nbsp; <b>Portable</b>&nbsp;&nbsp;.zip</a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="../examples/usage/" class="btn btn-danger" style="margin-bottom:8px;" role="button"><span class="fa fa-book"></span>&nbsp; <b>Getting Started</b></a>
</div>

The Windows distribution of PySceneDetect is bundled with all required dependencies.  After installation, you can call PySceneDetect from any terminal/command prompt by typing `scenedetect`.  Open a new command prompt (`cmd.exe`) and try running `scenedetect --version` to verify that everything was installed correctly.  If using the portable distribution, you need to run the command from the location of the extracted files, where the `scenedetect.exe` executable is.


### Python Installer (All Platforms, Requires Python) &nbsp; <span class="wy-text-neutral"><span class="fa fa-windows"></span> &nbsp; <span class="fa fa-linux"></span> &nbsp; <span class="fa fa-apple"></span></span></h3>

<div class="important">
<h3 class="wy-text-neutral"><span class="fa fa-forward wy-text-info"></span> Latest Release: <b class="wy-text-neutral">v0.5-beta-1</b></h3>
<h4 class="wy-text-neutral"><span class="fa fa-calendar wy-text-info"></span>&nbsp; Release Date:&nbsp; <b>August 6, 2018</b></h4>
<a href="https://github.com/Breakthrough/PySceneDetect/archive/v0.5-beta-1.zip" class="btn btn-info" style="margin-bottom:8px;" role="button"><span class="fa fa-download"></span>&nbsp; <b>Source</b>&nbsp;&nbsp;.zip</a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="https://github.com/Breakthrough/PySceneDetect/archive/v0.5-beta-1.tar.gz" class="btn btn-info" style="margin-bottom:8px;" role="button"><span class="fa fa-download"></span>&nbsp; <b>Source</b>&nbsp;&nbsp;.tar.gz</a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="#installation" class="btn btn-warning" style="margin-bottom:8px;" role="button"><span class="fa fa-gear"></span>&nbsp; <b>Installation</b></a> &nbsp;&nbsp;&nbsp;&nbsp; <a href="../examples/usage/" class="btn btn-danger" style="margin-bottom:8px;" role="button"><span class="fa fa-book"></span>&nbsp; <b>Getting Started</b></a>
</div>

Once you've downloaded the source archive, extract it to a location of your choice, and make sure you have the appropriate [system requirements](#installing-dependencies) installed before continuing.  PySceneDetect can be installed by running the following command in the location of the extracted files:

```md
sudo python setup.py install
```

After installation, you can call PySceneDetect from any terminal/command prompt by typing `scenedetect` (try running `scenedetect version`, or `scenedetect --version` in v0.4 and prior, to verify that everything was installed correctly).


------------------------------------------------


## Installation

Start by downloading the latest release of PySceneDetect and extracting it to a location of your choice.  Then, follow the instructions below under [Installing Dependencies](#installing-dependencies) to ensure you have all the system requirements.  Finally, run the commands in [Installing PySceneDetect](#installing-pyscenedetect) to install the program, allowing you to run the `scenedetect` command from any terminal/command prompt.

Note that if you are using a Windows distribution (i.e. you used the installer, or downloaded the portable .zip version), you do not need to install any dependencies on your computer, they are bundled with PySceneDetect.


### Installing Dependencies

PySceneDetect requires [Python 2 or 3](https://www.python.org/) and the following third-party software:

 - [OpenCV](http://opencv.org/) (compatible with both 2.X or 3.X), and the OpenCV `cv2` Python module
 - [Numpy](http://sourceforge.net/projects/numpy/), Python module
 - [tqdm](https://github.com/tqdm/tqdm), optional. Used to show progress bar and estimated time remaining (can usually install via `pip install tqdm`).

For video splitting support, you also need:

 - [ffmpeg](https://ffmpeg.org/download.html), part of mkvtoolnix, command-line tool, required to split video files in precise/high-quality mode (`split-video` or `split-video -h/--high-quality`)
 - [mkvmerge](https://mkvtoolnix.download/), part of mkvtoolnix, command-line tool, required to split video files in copy mode (`split-video -c/--copy`)

The `ffmpeg` and/or `mkvmerge` command must be available system wide (e.g. in a directory in PATH, so it can be used from any terminal/console by typing the command), or alternatively, placed in the same directory where PySceneDetect is installed.

You can [click here](http://breakthrough.github.io/Installing-OpenCV/) for a quick guide (OpenCV + Numpy on Windows & Linux) on installing the latest versions of OpenCV/Numpy on [Windows (using pre-built binaries)](http://breakthrough.github.io/Installing-OpenCV/#installing-on-windows-pre-built-binaries) and [Linux (compiling from source)](http://breakthrough.github.io/Installing-OpenCV/#installing-on-linux-compiling-from-source).  If the Python module that comes with OpenCV on Windows is incompatible with your system architecture or Python version, [see this page](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv) to obtain a pre-compiled (unofficial) module.

Note that some Linux package managers still provide older, dated builds of OpenCV (pre-3.0).  PySceneDetect is compatible with both versions, but if you want to ensure you have the latest version, it's recommended that you [build and install OpenCV from source](http://breakthrough.github.io/Installing-OpenCV/#installing-on-linux-compiling-from-source) on Linux.
  
To ensure you have all the requirements installed, open a `python` interpreter, and ensure you can run `import numpy` and `import cv2` without any errors.  For video splitting support, also and ensure you can run the `ffmpeg` and/or `mkvmerge` from a terminal/console.

Once this is done, you're ready to install PySceneDetect.


### Installing PySceneDetect

Go to the folder you extracted the PySceneDetect source code to, and run the following command (may require root):

```md
python setup.py install
```

Once finished, PySceneDetect will be installed, and you should be able to run the `scenedetect` command.  To verify that everything was installed properly, try calling the following command:

```md
scenedetect version
```

To get familiar with PySceneDetect, try running `scenedetect help`, or continue onwards to the [Getting Started: Basic Usage](examples/usage.md) section.  If you encounter any runtime errors while running PySceneDetect, ensure that you have all the required dependencies listed in the System Requirements section above (again, you should be able to `import numpy` and `import cv2`).  If you encounter any issues or want to make a feature request, feel free to [report any bugs or share some feature requests/ideas](contributing.md) on the [issue tracker](https://github.com/Breakthrough/PySceneDetect/issues) and help make PySceneDetect even better.

