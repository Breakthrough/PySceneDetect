

## <span class="fa fa-question-circle"></span>&nbsp; Frequently Asked Questions

#### How can I fix `ImportError: No module named cv2`?

You need to install OpenCV for PySceneDetect to properly work.  If you're using `pip`, you can install it as follows:

```md
pip install scenedetect[opencv]
```

Note that you may need to use a different/older version depending on your Python version.  You can also use the headless package if you're running a server:


```md
pip install scenedetect[opencv-headless]
```

Unlike calling `pip install opencv-python`, the above commands will download and install the correct OpenCV version based on the Python version you are running.


#### How can I enable video splitting support?

To enable video splitting support, you will also need to have `mkvmerge` or `ffmpeg` installed on your system. See the documentation on [Video Splitting Support](https://pyscenedetect.readthedocs.io/en/latest/examples/video-splitting/) after installation for details.


