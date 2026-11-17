# Download

PySceneDetect is completely free software, and can be downloaded from the links below. See the [license and copyright information](copyright.md) page for details. If you have trouble running PySceneDetect, ensure that you have all the required dependencies listed in the [Dependencies](#dependencies) section below.

PySceneDetect requires at least Python 3.10 or higher.

## Install via pip

Standard install (recommended):

```bash
pip install --upgrade scenedetect
```

Headless install (servers, no GUI libs):

```bash
pip install --upgrade scenedetect-headless
```

PySceneDetect is available via `pip` as two packages:

- [`scenedetect`](https://pypi.org/project/scenedetect/): full install with the CLI, depends on `opencv-python`
- [`scenedetect-headless`](https://pypi.org/project/scenedetect-headless/): full install with the CLI, depends on `opencv-python-headless` (servers/containers without GUI libraries)

Both provide the same `scenedetect` Python module -- install only one of them.

## Windows Build (64-bit Only)

<div class="download-card">
  <div class="download-card-header">
    <span class="download-card-title">
      <svg class="download-os-icon" aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M2 3.75 10.75 2.5v8.75H2V3.75Zm9.75-1.4L22 1v10.25H11.75V2.35ZM2 12.75h8.75v8.75L2 20.25v-7.5Zm9.75 0H22V23l-10.25-1.35v-8.9Z"/>
      </svg>
      <span>Windows 64-bit &middot; <strong>v0.7.3</strong></span>
    </span>
    <span class="download-card-date">November 8, 2026</span>
  </div>
  <div class="download-btn-grid">
    <a class="download-btn download-btn-primary" href="https://github.com/Breakthrough/PySceneDetect/releases/download/v0.7.3/PySceneDetect-0.7.3-win64.msi">
      <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 3v12m0 0-4-4m4 4 4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>
      </svg>
      <span>Installer <code>.msi</code></span>
      <span class="download-badge">Recommended</span>
    </a>
    <a class="download-btn download-btn-secondary" href="https://github.com/Breakthrough/PySceneDetect/releases/download/v0.7.3/PySceneDetect-0.7.3-win64.zip">
      <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 8v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8m18 0-2.4-4.2A2 2 0 0 0 16.86 3H7.14a2 2 0 0 0-1.74 1.01L3 8m18 0H3m7 4h4"/>
      </svg>
      <span>Portable <code>.zip</code></span>
    </a>
  </div>
</div>

The installer is recommended for most users. Windows builds include `ffmpeg` and `mkvmerge` out of the box -- see [Getting Started](cli.md) after installing.

## Docker Image

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

The `latest` tag (the default when no tag is given) points to the most recent recommended build, the `main` tag tracks the development branch, and version tags (e.g. `0.7.3`) point to specific releases. `podman` can be used in place of `docker` in the commands above.

## Post Installation

After installation, you can call PySceneDetect from any terminal/command prompt by typing `scenedetect` (try running `scenedetect --help`, or `scenedetect version`). If you encounter any runtime errors while running PySceneDetect, ensure that you have all the required dependencies listed in the [Dependencies](#dependencies) section below (you should be able to `import numpy` and `import cv2`). If you encounter any issues or want to make a feature request, feel free to [report any bugs or share some feature requests/ideas](contributing.md) on the [issue tracker](https://github.com/Breakthrough/PySceneDetect/issues) and help make PySceneDetect even better.

## Dependencies

### Python Packages

PySceneDetect requires [Python 3](https://www.python.org/) and the following packages, all of which the `scenedetect` and `scenedetect-headless` packages install automatically:

- [OpenCV](https://opencv.org/): `pip install opencv-python` (any `opencv-python*` variant works)
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

The `ffmpeg` and/or `mkvmerge` command must be available system wide (e.g. in a directory in `PATH`, so it can be used from any terminal/console by typing the command), or alternatively, placed in the same directory where PySceneDetect is installed. On Windows this is usually `C:\PythonXY\Scripts`, where `XY` is your Python version. For more information, [see the CLI documentation](cli.md).

### Building OpenCV from Source

If you have installed OpenCV using `pip`, you will need to uninstall it before installing a different version of OpenCV, or building and installing it from source.

You can [click here](https://breakthrough.github.io/Installing-OpenCV/) for a quick guide (OpenCV + Numpy on Windows & Linux) on installing OpenCV/Numpy on [Windows (using pre-built binaries)](https://breakthrough.github.io/Installing-OpenCV/#installing-on-windows-pre-built-binaries) and [Linux (compiling from source)](https://breakthrough.github.io/Installing-OpenCV/#installing-on-linux-compiling-from-source). If the Python module that comes with OpenCV on Windows is incompatible with your system architecture or Python version, [see this page](http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv) to obtain a pre-compiled (unofficial) module.

To ensure you have all the requirements installed, open a `python` interpreter, and ensure you can run `import numpy` and `import cv2` without any errors.

## Code Signing Policy

This program uses free code signing provided by [SignPath.io](https://signpath.io?utm_source=foundation&utm_medium=website&utm_campaign=PySceneDetect), and a free code signing certificate by the [SignPath Foundation](https://signpath.org?utm_source=foundation&utm_medium=website&utm_campaign=PySceneDetect)
