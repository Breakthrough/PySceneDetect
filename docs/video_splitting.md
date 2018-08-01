

### <span class="fa fa-keyboard-o"></span>&nbsp; Enabling Video Splitting Support

PySceneDetect can use either ffmpeg or mkvmerge to split videos automatically.  If either of these tools are already installed on the system and available, they will be used.

You can download and install `mkvmerge` as part of the mkvtoolnix package from:
https://mkvtoolnix.download/downloads.html (Windows users should use the installer/setup, otherwise PySceneDetect may not be able to find mkvmerge.)

You can download `ffmpeg` from:
https://ffmpeg.org/download.html (Linux users should use a package manager instead, and Windows users may require additional steps to get PySceneDetect to detect ffmpeg - see below for more information.)

If PySceneDetect cannot find the respective tool installed on your system, you have three options:

  1. Place the tool in the same location that PySceneDetect is installed (e.g. copy and paste mkvmerge.exe into the same place scenedetect.exe is located).  This is the easiest solution for most users.

  2. Add the directory where you installed ffmpeg/mkvmerge to your system's PATH environment variable, ensuring that you can use the ffmpeg/mkvmerge command from any terminal/command prompt.  This is the best solution for advanced users.

  3. Place the tool in a location already in your system's PATH variable (e.g. C:/Windows).  This is not recommended, but may be the only solution on systems without administrative rights.

