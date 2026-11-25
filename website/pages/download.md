# Download

PySceneDetect is free, open-source software released under the BSD 3-Clause License (see [License & Copyright](copyright.md)). If you have trouble running PySceneDetect, verify that you have the packages listed under [Dependencies](#dependencies).

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

The `.msi` installer is recommended for most Windows users. Both Windows builds bundle `ffmpeg`. To use `split-video -m`, install MKVToolNix. After installing, see the [Command-Line Interface](cli.md) guide to get started.

## Install with pip, uv, or pipx

Installing from PyPI requires Python 3.10 or newer.

Standard install with `pip` (CLI and Python API):

```bash
pip install --upgrade scenedetect
```

Headless install (for servers and containers without GUI libraries):

```bash
pip install --upgrade scenedetect-headless
```

Install with `uv` or `pipx`:

```bash
# uv (isolated CLI tool)
uv tool install scenedetect

# uv (add to a Python project)
uv add scenedetect

# pipx (isolated CLI tool)
pipx install scenedetect
```

PySceneDetect is published on PyPI as two packages, both including the CLI and the `scenedetect` Python module:

- [`scenedetect`](https://pypi.org/project/scenedetect/): depends on `opencv-python`.
- [`scenedetect-headless`](https://pypi.org/project/scenedetect-headless/): depends on `opencv-python-headless`.

Install only one of them.

## Docker Image

Official container images are published on GitHub Container Registry at [ghcr.io/breakthrough/pyscenedetect](https://github.com/Breakthrough/PySceneDetect/pkgs/container/pyscenedetect). Each image includes the CLI, all optional video backends (PyAV and MoviePy), `ffmpeg`, and `mkvmerge`:

```bash
docker pull ghcr.io/breakthrough/pyscenedetect
docker run --rm ghcr.io/breakthrough/pyscenedetect version
```

To process videos, mount the folder that holds them into the container. The container runs as a non-root user, so output files keep normal permissions:

```bash
docker run --rm -v "$(pwd):/files" ghcr.io/breakthrough/pyscenedetect \
    -i /files/video.mp4 detect-adaptive split-video -o /files
```

The `latest` tag points to the most recent stable release, `main` tracks the development branch, and version tags (such as `0.7.3`) point to specific releases. You can also replace `docker` with `podman` in the commands above.

## Post-Installation Check

After installing, open a terminal and run `scenedetect version` or `scenedetect --help`. If you see an import error, verify that `import numpy` and `import cv2` work in Python and review [Dependencies](#dependencies).

If you find a bug or want to suggest a feature, open an issue on [the issue tracker](https://github.com/Breakthrough/PySceneDetect/issues) or see [Contributing & Support](contributing.md).

## Dependencies

### Python packages

The `scenedetect` and `scenedetect-headless` packages install these dependencies automatically:

- [OpenCV](https://opencv.org/): `pip install opencv-python` (or `opencv-python-headless` with `scenedetect-headless`)
- [NumPy](https://numpy.org/): `pip install numpy`
- [Click](https://click.palletsprojects.com): `pip install click` (used by the CLI)
- [tqdm](https://github.com/tqdm/tqdm): `pip install tqdm` (displays progress bars)
- [platformdirs](https://github.com/tox-dev/platformdirs): `pip install platformdirs` (used by the CLI)

Optional video backend packages:

- [PyAV](https://pyav.org/): `pip install av` (or `pip install "scenedetect[pyav]"`)
- [MoviePy](https://zulko.github.io/moviepy/): `pip install moviepy` (or `pip install "scenedetect[moviepy]"`)

### Video splitting tools

To split videos into clips, install at least one of these tools (`ffmpeg` is bundled in the Windows builds; the Docker image has both):

- [FFmpeg](https://ffmpeg.org/download.html): splits videos with re-encoding (`split-video`) or stream copy (`split-video -c` / `--copy`).
- [MKVToolNix](https://mkvtoolnix.download/downloads.html) (`mkvmerge`): splits videos in stream-copy mode (`split-video -m` / `--mkvmerge`).

See [Video Splitting Requirements](cli.md#video-splitting-requirements) for installation and `PATH` setup steps.

### Building OpenCV from source

If you installed OpenCV with `pip`, uninstall it before installing a different OpenCV build or compiling from source. See the [Installing OpenCV guide](https://breakthrough.github.io/Installing-OpenCV/) for steps on Windows and Linux.

To verify your setup, open a Python prompt and run `import numpy` and `import cv2`.

## Code Signing Policy

This program uses free code signing provided by [SignPath.io](https://signpath.io?utm_source=foundation&utm_medium=website&utm_campaign=PySceneDetect), and a free code signing certificate by the [SignPath Foundation](https://signpath.org?utm_source=foundation&utm_medium=website&utm_campaign=PySceneDetect).
