#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""The ``scenedetect`` module comes with helper functions to simplify common use cases.
:func:`detect` can be used to perform scene detection on a video by path.  :func:`open_video`
can be used to open a video for a
:class:`SceneManager <scenedetect.scene_manager.SceneManager>`.
"""

import math
import queue
import threading
import typing as ty
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from string import Template

# OpenCV is a required package, but we don't have it as an explicit dependency since we
# need to support both opencv-python and opencv-python-headless. Include some additional
# context with the exception if this is the case.
try:
    import cv2
except ModuleNotFoundError as ex:
    raise ModuleNotFoundError(
        "OpenCV could not be found, try installing opencv-python:\n\npip install opencv-python",
        name="cv2",
    ) from ex
import numpy as np

from scenedetect.backends import (
    AVAILABLE_BACKENDS,
    VideoCaptureAdapter,
    VideoStreamAv,
    VideoStreamCv2,
    VideoStreamMoviePy,
)
from scenedetect.detectors import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
)
from scenedetect.frame_timecode import FrameTimecode

# Commonly used classes/functions exported under the `scenedetect` namespace for brevity.
from scenedetect.platform import (  # noqa: I001
    get_and_create_path,
    get_cv2_imwrite_params,
    init_logger,
    tqdm,
)
from scenedetect.scene_detector import SceneDetector
from scenedetect.scene_manager import Interpolation, SceneList, SceneManager, save_images
from scenedetect.stats_manager import StatsFileCorrupt, StatsManager
from scenedetect.video_manager import VideoManager  # [DEPRECATED] DO NOT USE.
from scenedetect.video_splitter import split_video_ffmpeg, split_video_mkvmerge
from scenedetect.video_stream import VideoOpenFailure, VideoStream

# Used for module identification and when printing version & about info
# (e.g. calling `scenedetect version` or `scenedetect about`).
__version__ = "0.6.5-dev1"

init_logger()
logger = getLogger("pyscenedetect")


def open_video(
    path: str,
    framerate: ty.Optional[float] = None,
    backend: str = "opencv",
    **kwargs,
) -> VideoStream:
    """Open a video at the given path. If `backend` is specified but not available on the current
    system, OpenCV (`VideoStreamCv2`) will be used as a fallback.

    Arguments:
        path: Path to video file to open.
        framerate: Overrides detected framerate if set.
        backend: Name of specific backend to use, if possible. See
            :data:`scenedetect.backends.AVAILABLE_BACKENDS` for backends available on the current
            system. If the backend fails to open the video, OpenCV will be used as a fallback.
        kwargs: Optional named arguments to pass to the specified `backend` constructor for
            overriding backend-specific options.

    Returns:
        Backend object created with the specified video path.

    Raises:
        :class:`VideoOpenFailure`: Constructing the VideoStream fails. If multiple backends have
            been attempted, the error from the first backend will be returned.
    """
    last_error: Exception = None
    # If `backend` is available, try to open the video at `path` using it.
    if backend in AVAILABLE_BACKENDS:
        backend_type = AVAILABLE_BACKENDS[backend]
        try:
            logger.debug("Opening video with %s...", backend_type.BACKEND_NAME)
            return backend_type(path, framerate, **kwargs)
        except VideoOpenFailure as ex:
            logger.warning("Failed to open video with %s: %s", backend_type.BACKEND_NAME, str(ex))
            if backend == VideoStreamCv2.BACKEND_NAME:
                raise
            last_error = ex
    else:
        logger.warning("Backend %s not available.", backend)
    # Fallback to OpenCV if `backend` is unavailable, or specified backend failed to open `path`.
    backend_type = VideoStreamCv2
    logger.warning("Trying another backend: %s", backend_type.BACKEND_NAME)
    try:
        return backend_type(path, framerate)
    except VideoOpenFailure as ex:
        logger.debug("Failed to open video: %s", str(ex))
        if last_error is None:
            last_error = ex
    # Propagate any exceptions raised from specified backend, instead of errors from the fallback.
    assert last_error is not None
    raise last_error


def detect(
    video_path: str,
    detector: SceneDetector,
    stats_file_path: ty.Optional[str] = None,
    show_progress: bool = False,
    start_time: ty.Optional[ty.Union[str, float, int]] = None,
    end_time: ty.Optional[ty.Union[str, float, int]] = None,
    start_in_scene: bool = False,
) -> SceneList:
    """Perform scene detection on a given video `path` using the specified `detector`.

    Arguments:
        video_path: Path to input video (absolute or relative to working directory).
        detector: A `SceneDetector` instance (see :mod:`scenedetect.detectors` for a full list
            of detectors).
        stats_file_path: Path to save per-frame metrics to for statistical analysis or to
            determine a better threshold value.
        show_progress: Show a progress bar with estimated time remaining. Default is False.
        start_time: Starting point in video, in the form of a timecode ``HH:MM:SS[.nnn]`` (`str`),
            number of seconds ``123.45`` (`float`), or number of frames ``200`` (`int`).
        end_time: Starting point in video, in the form of a timecode ``HH:MM:SS[.nnn]`` (`str`),
            number of seconds ``123.45`` (`float`), or number of frames ``200`` (`int`).
        start_in_scene: Assume the video begins in a scene. This means that when detecting
            fast cuts with `ContentDetector`, if no cuts are found, the resulting scene list
            will contain a single scene spanning the entire video (instead of no scenes).
            When detecting fades with `ThresholdDetector`, the beginning portion of the video
            will always be included until the first fade-out event is detected.

    Returns:
        List of scenes as pairs of (start, end) :class:`FrameTimecode` objects.

    Raises:
        :class:`VideoOpenFailure`: `video_path` could not be opened.
        :class:`StatsFileCorrupt`: `stats_file_path` is an invalid stats file
        ValueError: `start_time` or `end_time` are incorrectly formatted.
        TypeError: `start_time` or `end_time` are invalid types.
    """
    video = open_video(video_path)
    if start_time is not None:
        start_time = video.base_timecode + start_time
        video.seek(start_time)
    if end_time is not None:
        end_time = video.base_timecode + end_time
    # To reduce memory consumption when not required, we only add a StatsManager if we
    # need to save frame metrics to disk.
    scene_manager = SceneManager(StatsManager() if stats_file_path else None)
    scene_manager.add_detector(detector)
    scene_manager.detect_scenes(
        video=video,
        show_progress=show_progress,
        end_time=end_time,
    )
    if scene_manager.stats_manager is not None:
        scene_manager.stats_manager.save_to_csv(csv_file=stats_file_path)
    return scene_manager.get_scene_list(start_in_scene=start_in_scene)


# TODO: Just merge these variables into the extractor.
@dataclass
class ImageExtractorConfig:
    num_images: int = 3
    """Number of images to generate for each scene.  Minimum is 1."""
    frame_margin: int = 1
    """Number of frames to pad each scene around the beginning
            and end (e.g. moves the first/last image into the scene by N frames).
            Can set to 0, but will result in some video files failing to extract
            the very last frame."""
    image_extension: str = "jpg"
    """Type of image to save (must be one of 'jpg', 'png', or 'webp')."""
    encoder_param: int = 95
    """Quality/compression efficiency, based on type of image:
            'jpg' / 'webp':  Quality 0-100, higher is better quality.  100 is lossless for webp.
            'png': Compression from 1-9, where 9 achieves best filesize but is slower to encode."""
    image_name_template: str = "$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER"
    """Template to use for naming image files. Can use the template variables
            $VIDEO_NAME, $SCENE_NUMBER, $IMAGE_NUMBER, $TIMECODE, $FRAME_NUMBER, $TIMESTAMP_MS.
            Should not include an extension."""
    scale: ty.Optional[float] = None
    """Optional factor by which to rescale saved images. A scaling factor of 1 would
            not result in rescaling. A value < 1 results in a smaller saved image, while a
            value > 1 results in an image larger than the original. This value is ignored if
            either the height or width values are specified."""
    height: ty.Optional[int] = None
    """Optional value for the height of the saved images. Specifying both the height
            and width will resize images to an exact size, regardless of aspect ratio.
            Specifying only height will rescale the image to that number of pixels in height
            while preserving the aspect ratio."""
    width: ty.Optional[int] = None
    """Optional value for the width of the saved images. Specifying both the width
            and height will resize images to an exact size, regardless of aspect ratio.
            Specifying only width will rescale the image to that number of pixels wide
            while preserving the aspect ratio."""
    interpolation: Interpolation = Interpolation.CUBIC
    """Type of interpolation to use when resizing images."""


class ImageExtractor:
    def __init__(
        self,
        num_images: int = 3,
        frame_margin: int = 1,
        image_extension: str = "jpg",
        encoder_param: int = 95,
        image_name_template: str = "$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER",
        scale: ty.Optional[float] = None,
        height: ty.Optional[int] = None,
        width: ty.Optional[int] = None,
        interpolation: Interpolation = Interpolation.CUBIC,
    ):
        """Helper type to handle saving images for a set of scenes. This object is *not* thread-safe.

        Arguments:
            num_images: Number of images to generate for each scene.  Minimum is 1.
            frame_margin: Number of frames to pad each scene around the beginning
                and end (e.g. moves the first/last image into the scene by N frames).
                Can set to 0, but will result in some video files failing to extract
                the very last frame.
            image_extension: Type of image to save (must be one of 'jpg', 'png', or 'webp').
            encoder_param: Quality/compression efficiency, based on type of image:
                'jpg' / 'webp':  Quality 0-100, higher is better quality.  100 is lossless for webp.
                'png': Compression from 1-9, where 9 achieves best filesize but is slower to encode.
            image_name_template: Template to use for output filanames. Can use template variables
                $VIDEO_NAME, $SCENE_NUMBER, $IMAGE_NUMBER, $TIMECODE, $FRAME_NUMBER, $TIMESTAMP_MS.
                *NOTE*: Should not include the image extension (set `image_extension` instead).
            scale: Optional factor by which to rescale saved images. A scaling factor of 1 would
                not result in rescaling. A value < 1 results in a smaller saved image, while a
                value > 1 results in an image larger than the original. This value is ignored if
                either the height or width values are specified.
            height: Optional value for the height of the saved images. Specifying both the height
                and width will resize images to an exact size, regardless of aspect ratio.
                Specifying only height will rescale the image to that number of pixels in height
                while preserving the aspect ratio.
            width: Optional value for the width of the saved images. Specifying both the width
                and height will resize images to an exact size, regardless of aspect ratio.
                Specifying only width will rescale the image to that number of pixels wide
                while preserving the aspect ratio.
            interpolation: Type of interpolation to use when resizing images.
        """
        self._num_images = num_images
        self._frame_margin = frame_margin
        self._image_extension = image_extension
        self._encoder_param = encoder_param
        self._image_name_template = image_name_template
        self._scale = scale
        self._height = height
        self._width = width
        self._interpolation = interpolation

    def run(
        self,
        video: VideoStream,
        scene_list: SceneList,
        output_dir: ty.Optional[str] = None,
        show_progress=False,
    ) -> ty.Dict[int, ty.List[str]]:
        if not scene_list:
            return {}
        if self._num_images <= 0 or self._frame_margin < 0:
            raise ValueError()

        video.reset()

        # Setup flags and init progress bar if available.
        completed = True
        logger.info(
            f"Saving {self._num_images} images per scene [format={self._image_extension}] {output_dir if output_dir else ''} "
        )
        progress_bar = None
        if show_progress:
            progress_bar = tqdm(
                total=len(scene_list) * self._num_images, unit="images", dynamic_ncols=True
            )

        filename_template = Template(self._image_name_template)
        scene_num_format = "%0"
        scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + "d"
        image_num_format = "%0"
        image_num_format += str(math.floor(math.log(self._num_images, 10)) + 2) + "d"

        timecode_list = self.generate_timecode_list(scene_list)
        image_filenames = {i: [] for i in range(len(timecode_list))}
        logger.debug("Writing images with template %s", filename_template.template)

        MAX_QUEUED_ENCODE_FRAMES = 4
        MAX_QUEUED_SAVE_IMAGES = 4
        encode_queue = queue.Queue(MAX_QUEUED_ENCODE_FRAMES)
        save_queue = queue.Queue(MAX_QUEUED_SAVE_IMAGES)
        encode_thread = threading.Thread(
            target=self._image_encode_thread,
            args=(video, encode_queue, save_queue, self._image_extension),
            daemon=True,
        )
        save_thread = threading.Thread(
            target=self._save_files_thread,
            args=(save_queue, progress_bar),
            daemon=True,
        )
        encode_thread.start()
        save_thread.start()

        for i, scene_timecodes in enumerate(timecode_list):
            for j, image_timecode in enumerate(scene_timecodes):
                video.seek(image_timecode)
                frame_im = video.read()
                if frame_im is not None and frame_im is not False:
                    # TODO: Add extension to template.
                    # TODO: Allow NUM to be a valid suffix in addition to NUMBER.
                    file_path = "%s.%s" % (
                        filename_template.safe_substitute(
                            VIDEO_NAME=video.name,
                            SCENE_NUMBER=scene_num_format % (i + 1),
                            IMAGE_NUMBER=image_num_format % (j + 1),
                            FRAME_NUMBER=image_timecode.get_frames(),
                            TIMESTAMP_MS=int(image_timecode.get_seconds() * 1000),
                            TIMECODE=image_timecode.get_timecode().replace(":", ";"),
                        ),
                        self._image_extension,
                    )
                    image_filenames[i].append(file_path)
                    encode_queue.put((frame_im, get_and_create_path(file_path, output_dir)))
                else:
                    completed = False
                    break

        # *WARNING*: We do not handle errors or exceptions yet, and this can deadlock on errors!
        encode_queue.put((None, None))
        save_queue.put((None, None))
        encode_thread.join()
        save_thread.join()
        if progress_bar is not None:
            progress_bar.close()
        if not completed:
            logger.error("Could not generate all output images.")

        return image_filenames

    def _image_encode_thread(
        self,
        video: VideoStream,
        encode_queue: queue.Queue,
        save_queue: queue.Queue,
        image_extension: str,
    ):
        aspect_ratio = video.aspect_ratio
        if abs(aspect_ratio - 1.0) < 0.01:
            aspect_ratio = None
        # TODO: Validate that encoder_param is within the proper range.
        # Should be between 0 and 100 (inclusive) for jpg/webp, and 1-9 for png.
        imwrite_param = (
            [get_cv2_imwrite_params()[self._image_extension], self._encoder_param]
            if self._encoder_param is not None
            else []
        )
        while True:
            frame_im, dest_path = encode_queue.get()
            if frame_im is None:
                return
            frame_im = self.resize_image(
                frame_im,
                aspect_ratio,
            )
            (is_ok, encoded) = cv2.imencode(f".{image_extension}", frame_im, imwrite_param)
            if not is_ok:
                continue
            save_queue.put((encoded, dest_path))

    def _save_files_thread(self, save_queue: queue.Queue, progress_bar: tqdm):
        while True:
            encoded, dest_path = save_queue.get()
            if encoded is None:
                return
            if encoded is not False:
                encoded.tofile(Path(dest_path))
            if progress_bar is not None:
                progress_bar.update(1)

    def generate_timecode_list(self, scene_list: SceneList) -> ty.List[ty.Iterable[FrameTimecode]]:
        """Generates a list of timecodes for each scene in `scene_list` based on the current config
        parameters."""
        framerate = scene_list[0][0].framerate
        # TODO(v1.0): Split up into multiple sub-expressions so auto-formatter works correctly.
        return [
            (
                FrameTimecode(int(f), fps=framerate)
                for f in (
                    # middle frames
                    a[len(a) // 2]
                    if (0 < j < self._num_images - 1) or self._num_images == 1
                    # first frame
                    else min(a[0] + self._frame_margin, a[-1])
                    if j == 0
                    # last frame
                    else max(a[-1] - self._frame_margin, a[0])
                    # for each evenly-split array of frames in the scene list
                    for j, a in enumerate(np.array_split(r, self._num_images))
                )
            )
            for r in (
                # pad ranges to number of images
                r
                if 1 + r[-1] - r[0] >= self._num_images
                else list(r) + [r[-1]] * (self._num_images - len(r))
                # create range of frames in scene
                for r in (
                    range(
                        start.get_frames(),
                        start.get_frames()
                        + max(
                            1,  # guard against zero length scenes
                            end.get_frames() - start.get_frames(),
                        ),
                    )
                    # for each scene in scene list
                    for start, end in scene_list
                )
            )
        ]

    def resize_image(
        self,
        image: cv2.Mat,
        aspect_ratio: float,
    ) -> cv2.Mat:
        """Resizes the given `image` according to the current config parameters. `aspect_ratio` is
        used to correct for non-square pixels."""
        # TODO: Combine this resize with the ones below.
        if aspect_ratio is not None:
            image = cv2.resize(
                image, (0, 0), fx=aspect_ratio, fy=1.0, interpolation=self._interpolation.value
            )
        image_height = image.shape[0]
        image_width = image.shape[1]
        # Figure out what kind of resizing needs to be done
        if self._height or self._width:
            if self._height and not self._width:
                factor = self._height / float(image_height)
                width = int(factor * image_width)
            if self._width and not self._height:
                factor = width / float(image_width)
                height = int(factor * image_height)
            assert height > 0 and width > 0
            image = cv2.resize(image, (width, height), interpolation=self._interpolation.value)
        elif self._scale:
            image = cv2.resize(
                image,
                (0, 0),
                fx=self._scale,
                fy=self._scale,
                interpolation=self._interpolation.value,
            )
        return image
