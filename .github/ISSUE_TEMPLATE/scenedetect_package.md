---
name: Python API
about: Programmers using the `scenedetect` package.

---

**Description:**

Describe the issue (unexpected result, exception thrown, etc...) and any relevant output.

**Example:**

Include code samples that demonstrate the issue:

```python
from scenedetect import detect, ContentDetector, split_video_ffmpeg
scene_list = detect('my_video.mp4', ContentDetector())
split_video_ffmpeg('my_video.mp4', scene_list)
```

**Environment:**

Run `scenedetect version --all` and include the output. This will describe the environment/OS/platform and versions of dependencies you have installed.

**Media/Files:**

Attach or link to any files relevant to the issue, including videos (or YouTube links), scene files, stats files, and log output.
