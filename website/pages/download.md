
# Download

PySceneDetect is completely free software, and can be downloaded from the links below.  See the [license and copyright information](copyright.md) page for details.  If you have trouble running PySceneDetect, ensure that you have all the required dependencies listed in the [Dependencies](#dependencies) section below.

PySceneDetect requires at least Python 3.10 or higher.


## Install via pip &nbsp; <span class="wy-text-neutral"><span class="fa fa-windows"></span> &nbsp; <span class="fa fa-linux"></span> &nbsp; <span class="fa fa-apple"></span></span>

<div class="important">
<h4 class="wy-text-neutral"><span class="fa fa-angle-double-down wy-text-info"></span> Standard install (recommended):</h4>
<pre class="command"><code class="nohighlight">pip install --upgrade scenedetect</code></pre>
<h4 class="wy-text-neutral"><span class="fa fa-angle-down wy-text-info"></span> Headless install (servers, no GUI libs):</h4>
<pre class="command"><code class="nohighlight">pip install --upgrade scenedetect-headless</code></pre>
</div>

PySceneDetect is available via `pip` as two packages:

 - [`scenedetect`](https://pypi.org/project/scenedetect/): full install with the CLI, depends on `opencv-python`
 - [`scenedetect-headless`](https://pypi.org/project/scenedetect-headless/): full install with the CLI, depends on `opencv-python-headless` (servers/containers without GUI libraries)

Both provide the same `scenedetect` Python module -- install only one of them.

## Windows Build (64-bit Only) &nbsp; <span class="wy-text-neutral"><span class="fa fa-windows"></span></span>

<div class="important">
<h3 class="wy-text-neutral"><span class="fa fa-forward wy-text-info"></span> Latest Release: <b class="wy-text-neutral">v0.7.1</b></h3>
<h4 class="wy-text-neutral"><span class="fa fa-calendar wy-text-info"></span>&nbsp; Release Date:&nbsp; <b>July 21, 2026</b></h4>
<a href="https://github.com/Breakthrough/PySceneDetect/releases/download/v0.7.1/PySceneDetect-0.7.1-win64.msi" class="btn btn-info" style="margin-bottom:8px;" role="button"><span class="fa fa-download"></span>&nbsp; <b>Installer</b>&nbsp;&nbsp;(recommended)</a> &nbsp;&nbsp;&nbsp;&nbsp;
<a href="https://github.com/Breakthrough/PySceneDetect/releases/download/v0.7.1/PySceneDetect-0.7.1-win64.zip" class="btn btn-info" style="margin-bottom:8px;" role="button"><span class="fa fa-download"></span>&nbsp; <b>Portable .zip</b></a> &nbsp;&nbsp;&nbsp;&nbsp;
<a href="../cli/" class="btn btn-success" style="margin-bottom:8px;" role="button"><span class="fa fa-book"></span>&nbsp; <b>Getting Started</b></a>
</div>

## Docker Image &nbsp; <span class="wy-text-neutral"><span class="fa fa-ship"></span></span>

Official container images are published at [ghcr.io/breakthrough/pyscenedetect](https://github.com/breakthrough/PySceneDetect/pkgs/container/pyscenedetect). The image includes the full CLI, all optional backends (PyAV, MoviePy), and the external tools used for video splitting (`ffmpeg`, `mkvmerge`) -- no other setup is required:

```bash
docker pull ghcr.io/breakthrough/pyscenedetect
docker run --rm ghcr.io/breakthrough/pyscenedetect version
```

To process videos, mount the folder containing them into the container (the image runs as a non-root user, so output files are written with regular permissions):

```bash
docker run --rm -v "$(pwd):/files" ghcr.io/breakthrough/pyscenedetect \
    -i /files/video.mp4 detect-adaptive split-video -o /files
```

The `latest` tag (the default when no tag is given) points to the most recent recommended build, the `main` tag tracks the development branch, and version tags (e.g. `0.7.1`) point to specific releases. `podman` can be used in place of `docker` in the commands above.

## Post Installation

After installation, you can call PySceneDetect from any terminal/command prompt by typing `scenedetect` (try running `scenedetect --help`, or `scenedetect version`). If you encounter any runtime errors while running PySceneDetect, ensure that you have all the required dependencies listed in the System Requirements section above (you should be able to `import numpy` and `import cv2`).  If you encounter any issues or want to make a feature request, feel free to [report any bugs or share some feature requests/ideas](contributing.md) on the [issue tracker](https://github.com/Breakthrough/PySceneDetect/issues) and help make PySceneDetect even better.


## Dependencies

### Python Packages

PySceneDetect requires [Python 3](https://www.python.org/) and the following packages, all of which the `scenedetect` and `scenedetect-headless` packages install automatically:

 - [OpenCV](http://opencv.org/): `pip install opencv-python` (any `opencv-python*` variant works)
 - [Numpy](https://numpy.org/): `pip install numpy`
 - [Click](https://click.palletsprojects.com): `pip install click` (command-line interface only)
 - [tqdm](https://github.com/tqdm/tqdm): `pip install tqdm` (optional, enables progress bars)
 - [platformdirs](https://github.com/tox-dev/platformdirs): `pip install platformdirs` (command-line interface only)

Optional packages:

 - [PyAV](https://pyav.org/): `pip install av`

### Video Splitting Tools

For video splitting support, you need to have one of the following tools available (included in Windows builds):

 - [ffmpeg](https://ffmpeg.org/download.html), required to split video files (`split-video` or `split-video -c/--copy`)
 - [mkvmerge](https://mkvtoolnix.download/), part of mkvtoolnix, command-line tool, required to split video files in stream copy mode (`split-video -c/--copy` only)

The `ffmpeg` and/or `mkvmerge` command must be available system wide (e.g. in a directory in `PATH`, so it can be used from any terminal/console by typing the command), or alternatively, placed in the same directory where PySceneDetect is installed.  On Windows this is usually `C:\PythonXY\Scripts`, where `XY` is your Python version. For more information, [see the CLI documentation](cli.md).

### Building OpenCV from Source

If you have installed OpenCV using `pip`, you will need to uninstall it before installing a different version of OpenCV, or building and installing it from source.

You can [click here](http://breakthrough.github.io/Installing-OpenCV/) for a quick guide (OpenCV + Numpy on Windows & Linux) on installing OpenCV/Numpy on [Windows (using pre-built binaries)](http://breakthrough.github.io/Installing-OpenCV/#installing-on-windows-pre-built-binaries) and [Linux (compiling from source)](http://breakthrough.github.io/Installing-OpenCV/#installing-on-linux-compiling-from-source).  If the Python module that comes with OpenCV on Windows is incompatible with your system architecture or Python version, [see this page](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv) to obtain a pre-compiled (unofficial) module.

To ensure you have all the requirements installed, open a `python` interpreter, and ensure you can run `import numpy` and `import cv2` without any errors.


## Code Signing Policy

This program uses free code signing provided by [SignPath.io](https://signpath.io?utm_source=foundation&utm_medium=website&utm_campaign=PySceneDetect), and a free code signing certificate by the [SignPath Foundation](https://signpath.org?utm_source=foundation&utm_medium=website&utm_campaign=PySceneDetect)
