---
name: Bug or Issue Report
about: Submit a bug report or issue to help us fix and improve PySceneDetect.

---

**Bug/Issue Description:**
A clear and concise description of what the bug or issue is - in other words, what the *unexpected* behavior or output is.

**Required Information:**
Provide the following information to assist with reporting the bug:
1. Provide a full copy of the command line options you are using, for example:

`scenedetect -i some_video.mp4 -s some_video.stats.csv -o outdir detect-content --threshold 28 list-scenes save-images`

2. Add `-v debug -l BUG_REPORT.txt` to the beginning of the command, then re-run PySceneDetect and **attach the generated `BUG_REPORT.txt` file**.

**Expected Behavior:**
A clear and concise description of what you *expected* to happen.

**Computing Environment:**
 - OS: [e.g. Windows, Linux (Distro: Ubuntu, Mint, Fedora, etc...), OSX]
 - Python Version: [e.g. 3.6 or 3.6.6]
 - OpenCV Version: [e.g. 3.4.1]

**Additional Information:**
Add any other information you feel might be relevant to the bug/issue report but was not covered in one of the previous categories.

**Media [Videos/Images/Screenshots]:**
Provide any other information you can, including videos/media that can demonstrate the bug you are reporting (even YouTube links are fine). If applicable, add the output images from PySceneDetect, or any screenshots you feel are necessary to help explain your problem.

Remove this section if there is no media associated with the issue/bug report.
