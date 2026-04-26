

## <span class="fa fa-question-circle"></span>&nbsp; Frequently Asked Questions

#### How can I fix `ImportError: No module named cv2`?

As of PySceneDetect 0.7, the OpenCV dependency is bundled with the install. The standard `scenedetect` package depends on `opencv-python`:

```md
pip install scenedetect
```

For server environments without GUI libraries, install the headless variant instead, which depends on `opencv-python-headless`:

```md
pip install scenedetect-headless
```

Both packages ship the same `scenedetect` Python module — you only need one.

#### How can I enable video splitting support?

Video splitting is performed by `ffmpeg` ([https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)) or `mkvmerge` (https://mkvtoolnix.download/downloads.html) depending on which command line arguments are used. Ensure the tool is available and somewhere in your system's PATH folder.

#### How can I fix the error `Cannot split video due to too many scenes`?

This error occurs on Windows platforms specifically when the number of detected scenes is too large.  This is because PySceneDetect internally invokes other commands, such as those used for the `split-video` command.

You can get around this issue by simply invoking those tools manually, using a smaller sub-set of scenes (or splitting the scene list into multiple parts).  You can obtain a comma-separated list of timecodes by using the `list-scenes` command.

See [Issue #164](https://github.com/Breakthrough/PySceneDetect/issues/164) for details, or if you have any further questions.

#### How can I fix the error `Failed to read any frames from video file`?

Unfortunately, the underlying library used to perform video I/O was unable to open the file. Try using a different backend by installing PyAV (`pip install av`) and see if the problem persists.

This can also happen due to videos having multiple audio tracks (as per [#179](https://github.com/Breakthrough/PySceneDetect/issues/179)).  If the PyAV backend does not succeed in processing the video, as a workaround you can remove the audio track using either `ffmpeg` or `mkvmerge`:

```md
ffmpeg -i input.mp4 -c copy -an output.mp4
```

Or:

```md
mkvmerge -o output.mkv input.mp4
```
