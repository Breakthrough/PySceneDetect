
## <span class="fa fa-keyboard-o"></span>&nbsp; Video Splitting Support Requirements

PySceneDetect can use either `ffmpeg` or `mkvmerge` to split videos automatically.

By default, when specifying the `split-video` command, `ffmpeg` will be used to split the video.  If the `-c`/`--copy` option is also set (e.g. `split-video --copy`), `mkvmerge` will be used to split the video instead.


### FFmpeg

You can download `ffmpeg` from: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)

Note that Linux users should use a package manager (e.g. `sudo apt-get install ffmpeg`). Windows users may require additional steps in order for PySceneDetect to detect `ffmpeg` - see the section Manually Enabling `split-video` Support below for details.


### mkvmerge

You can download and install `mkvmerge` as part of the mkvtoolnix package from:
[https://mkvtoolnix.download/downloads.html](https://mkvtoolnix.download/downloads.html)

Note that Windows users should use the installer/setup, and Linux users should use their system package manager, otherwise PySceneDetect may not be able to find `mkvmerge`.  If this is the case, see the section below to enable support for the `split-video --copy` command manually.


## Manually Enabling `split-video` Support

If PySceneDetect cannot find the respective tool installed on your system, you have three options:

  1. Place the tool in the same location that PySceneDetect is installed (e.g. copy and paste mkvmerge.exe into the same place scenedetect.exe is located).  This is the easiest solution for most users.

  2. Add the directory where you installed ffmpeg/mkvmerge to your system's PATH environment variable, ensuring that you can use the ffmpeg/mkvmerge command from any terminal/command prompt.  This is the best solution for advanced users.

  3. Place the tool in a location already in your system's PATH variable (e.g. C:/Windows).  This is not recommended, but may be the only solution on systems without administrative rights.

