# Frequently Asked Questions

## Installation and Setup

### How do I fix `ImportError: No module named cv2`?

Since PySceneDetect 0.7, OpenCV is installed automatically. Install the standard package:

```bash
pip install scenedetect
```

For servers or containers without GUI libraries, install the headless package instead:

```bash
pip install scenedetect-headless
```

Both packages provide the same `scenedetect` Python module. Install only one of them.

If your project needs a different OpenCV package (such as `opencv-contrib-python`), install the exact same version that `scenedetect` installed so both packages share identical `cv2` files:

```bash
pip install scenedetect
pip install "opencv-contrib-python==$(pip show opencv-python | grep ^Version | cut -d' ' -f2)"
```

Mixing different versions of OpenCV packages can break your `cv2` install. First-class support for choosing an OpenCV variant is tracked in [Issue #558](https://github.com/Breakthrough/PySceneDetect/issues/558).

### How do I enable video splitting?

PySceneDetect uses `ffmpeg` or `mkvmerge` to split videos:

- Download `ffmpeg` from [the FFmpeg website](https://ffmpeg.org/download.html).
- Download `mkvmerge` as part of [MKVToolNix](https://mkvtoolnix.download/downloads.html).

Make sure the executable is on your system `PATH` or in the same folder as `scenedetect`. Windows installers and Docker images already include both tools.

## Detection and Splitting

### How do I tune the detection threshold?

Generate a per-frame stats file with `-s` / `--stats`:

```bash
scenedetect -i video.mp4 -s video.stats.csv detect-adaptive
```

Open `video.stats.csv` in a spreadsheet tool and inspect the metric column for your detector (`adaptive_ratio` for `detect-adaptive`, `content_val` for `detect-content`, or `average_rgb` for `detect-threshold`).

- Lower the threshold (`-t`) if PySceneDetect misses real cuts.
- Raise the threshold (`-t`) if PySceneDetect reports too many false cuts.

See [Detection Parameters](cli.md#detection-parameters) for a full walkthrough and [Benchmarks](benchmarks.md) for parameter sweep results across datasets.

### Does PySceneDetect support variable frame rate (VFR) videos?

Yes. Both the default OpenCV backend and the PyAV backend support VFR videos using presentation timestamps (PTS) instead of assuming a constant frame rate.

For difficult VFR files, use the PyAV backend (`pip install av`, then pass `-b pyav`), which reads native PTS timestamps directly from the video container. The MoviePy backend does not support VFR video. See [Video Backends](/docs/latest/cli/backends.html) for details.

### Should I use stream copy or re-encoding when splitting video?

- **Default re-encoding (`split-video`)**: uses `ffmpeg` to re-encode each clip. Cuts are frame-accurate, and you can adjust quality with `-hq` / `--high-quality`, `-crf`, or `-p` / `--preset`.
- **Stream copy (`split-video --copy` or `split-video --mkvmerge`)**: copies the compressed video and audio streams without re-encoding. This is much faster and preserves original quality, but splits can only happen on keyframes, so clip start and end times may shift slightly.

## Troubleshooting

### How do I fix `Cannot split video due to too many scenes`?

On Windows, passing hundreds of scene timecodes to an external command can exceed the operating system's command-line length limit.

To work around this limit, export the scene list with `list-scenes` and split the video in smaller batches using `ffmpeg` or `mkvmerge` directly. See [Issue #164](https://github.com/Breakthrough/PySceneDetect/issues/164) for details.

### How do I fix `Failed to read any frames from video file`?

The active video backend could not decode the file. Install PyAV (`pip install av`) and run PySceneDetect with `-b pyav` to test another backend.

Videos with multiple audio tracks can also cause decode failures in OpenCV (see [Issue #179](https://github.com/Breakthrough/PySceneDetect/issues/179)). If switching to PyAV does not help, remove the audio tracks into a temporary file before running detection:

```bash
ffmpeg -i input.mp4 -c copy -an output.mp4
```

Or with `mkvmerge`:

```bash
mkvmerge -o output.mkv input.mp4
```
