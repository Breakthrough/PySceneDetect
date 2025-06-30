#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Implements :func:`save_images` functionality."""

import logging
import math
import queue
import sys
import threading
import typing as ty
from pathlib import Path
from string import Template

import cv2
import numpy as np

from scenedetect.common import (
    FrameTimecode,
    Interpolation,
    SceneList,
)
from scenedetect.platform import get_and_create_path, get_cv2_imwrite_params, tqdm
from scenedetect.video_stream import VideoStream

logger = logging.getLogger("pyscenedetect")


def _scale_image(
    image: np.ndarray,
    aspect_ratio: float,
    height: ty.Optional[int],
    width: ty.Optional[int],
    scale: ty.Optional[float],
    interpolation: Interpolation,
) -> np.ndarray:
    # TODO: Combine this resize with the ones below.
    if aspect_ratio is not None:
        image = cv2.resize(
            image, (0, 0), fx=aspect_ratio, fy=1.0, interpolation=interpolation.value
        )
    image_height = image.shape[0]
    image_width = image.shape[1]

    # Figure out what kind of resizing needs to be done
    if height or width:
        if height and not width:
            factor = height / float(image_height)
            width = int(factor * image_width)
        if width and not height:
            factor = width / float(image_width)
            height = int(factor * image_height)
        assert height > 0 and width > 0
        image = cv2.resize(image, (width, height), interpolation=interpolation.value)
    elif scale:
        image = cv2.resize(image, (0, 0), fx=scale, fy=scale, interpolation=interpolation.value)
    return image


class _ImageExtractor:
    def __init__(
        self,
        num_images: int = 3,
        frame_margin: int = 1,
        image_extension: str = "jpg",
        imwrite_param: ty.Dict[str, ty.Union[int, None]] = None,
        image_name_template: str = "$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER",
        scale: ty.Optional[float] = None,
        height: ty.Optional[int] = None,
        width: ty.Optional[int] = None,
        interpolation: Interpolation = Interpolation.CUBIC,
    ):
        """Multi-threaded implementation of save-images functionality. Uses background threads to
        handle image encoding and saving images to disk to improve parallelism.

        This object is thread-safe.

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
        self._image_name_template = image_name_template
        self._scale = scale
        self._height = height
        self._width = width
        self._interpolation = interpolation
        self._imwrite_param = imwrite_param if imwrite_param else {}

    def run(
        self,
        video: VideoStream,
        scene_list: SceneList,
        output_dir: ty.Optional[str] = None,
        show_progress=False,
    ) -> ty.Dict[int, ty.List[str]]:
        """Run image extraction on `video` using the current parameters. Thread-safe.

        Arguments:
            video: The video to process.
            scene_list: The scenes detected in the video.
            output_dir: Directory to write files to.
            show_progress: If `true` and tqdm is available, shows a progress bar.
        """
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

        timecode_list = self.generate_timecode_list(scene_list)
        image_filenames = {i: [] for i in range(len(timecode_list))}

        filename_template = Template(self._image_name_template)
        logger.debug("Writing images with template %s", filename_template.template)
        scene_num_format = "%0"
        scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + "d"
        image_num_format = "%0"
        image_num_format += str(math.floor(math.log(self._num_images, 10)) + 2) + "d"

        def format_filename(scene_number: int, image_number: int, image_timecode: FrameTimecode):
            return "%s.%s" % (
                filename_template.safe_substitute(
                    VIDEO_NAME=video.name,
                    SCENE_NUMBER=scene_num_format % (scene_number + 1),
                    IMAGE_NUMBER=image_num_format % (image_number + 1),
                    FRAME_NUMBER=image_timecode.frame_num,
                    TIMESTAMP_MS=int(image_timecode.seconds * 1000),
                    TIMECODE=image_timecode.get_timecode().replace(":", ";"),
                ),
                self._image_extension,
            )

        MAX_QUEUED_ENCODE_FRAMES = 4
        MAX_QUEUED_SAVE_IMAGES = 4
        encode_queue = queue.Queue(MAX_QUEUED_ENCODE_FRAMES)
        save_queue = queue.Queue(MAX_QUEUED_SAVE_IMAGES)
        error_queue = queue.Queue(2)  # Queue size must be the same as the # of worker threads!

        def check_error_queue():
            try:
                return error_queue.get(block=False)
            except queue.Empty:
                pass
            return None

        def launch_thread(callable, *args, **kwargs):
            def capture_errors(callable, *args, **kwargs):
                try:
                    return callable(*args, **kwargs)
                # Errors we capture in `error_queue` will be re-raised by this thread.
                except:  # noqa: E722
                    error_queue.put(sys.exc_info())
                return None

            thread = threading.Thread(
                target=capture_errors,
                args=(
                    callable,
                    *args,
                ),
                kwargs=kwargs,
                daemon=True,
            )
            thread.start()
            return thread

        def checked_put(work_queue: queue.Queue, item: ty.Any):
            error = None
            while True:
                try:
                    work_queue.put(item, timeout=0.1)
                    return
                except queue.Full:
                    error = check_error_queue()
                    if error is not None:
                        break
                    continue
            raise error[1].with_traceback(error[2])

        encode_thread = launch_thread(
            self.image_encode_thread,
            video,
            encode_queue,
            save_queue,
        )
        save_thread = launch_thread(self.image_save_thread, save_queue, progress_bar)

        for i, scene_timecodes in enumerate(timecode_list):
            for j, timecode in enumerate(scene_timecodes):
                video.seek(timecode)
                frame_im = video.read()
                if frame_im is not None and frame_im is not False:
                    file_path = format_filename(i, j, timecode)
                    image_filenames[i].append(file_path)
                    checked_put(
                        encode_queue, (frame_im, get_and_create_path(file_path, output_dir))
                    )
                else:
                    completed = False
                    break

        checked_put(encode_queue, (None, None))
        encode_thread.join()
        checked_put(save_queue, (None, None))
        save_thread.join()

        error = check_error_queue()
        if error is not None:
            raise error[1].with_traceback(error[2])

        if progress_bar is not None:
            progress_bar.close()
        if not completed:
            logger.error("Could not generate all output images.")

        return image_filenames

    def image_encode_thread(
        self,
        video: VideoStream,
        encode_queue: queue.Queue,
        save_queue: queue.Queue,
    ):
        aspect_ratio = video.aspect_ratio
        if abs(aspect_ratio - 1.0) < 0.01:
            aspect_ratio = None
        # TODO: Validate that encoder_param is within the proper range.
        # Should be between 0 and 100 (inclusive) for jpg/webp, and 1-9 for png.
        while True:
            frame_im, dest_path = encode_queue.get()
            if frame_im is None:
                return
            frame_im = self.resize_image(
                frame_im,
                aspect_ratio,
            )
            (is_ok, encoded) = cv2.imencode(
                f".{self._image_extension}", frame_im, self._imwrite_param
            )
            if not is_ok:
                continue
            save_queue.put((encoded, dest_path))

    def image_save_thread(self, save_queue: queue.Queue, progress_bar: tqdm):
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
        framerate = scene_list[0][0]._framerate
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
                        start.frame_num,
                        start.frame_num
                        + max(
                            1,  # guard against zero length scenes
                            end.frame_num - start.frame_num,
                        ),
                    )
                    # for each scene in scene list
                    for start, end in scene_list
                )
            )
        ]

    def resize_image(
        self,
        image: np.ndarray,
        aspect_ratio: float,
    ) -> np.ndarray:
        return _scale_image(
            image, aspect_ratio, self._height, self._width, self._scale, self._interpolation
        )


def save_images(
    scene_list: SceneList,
    video: VideoStream,
    num_images: int = 3,
    frame_margin: int = 1,
    image_extension: str = "jpg",
    encoder_param: int = 95,
    image_name_template: str = "$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER",
    output_dir: ty.Optional[str] = None,
    show_progress: ty.Optional[bool] = False,
    scale: ty.Optional[float] = None,
    height: ty.Optional[int] = None,
    width: ty.Optional[int] = None,
    interpolation: Interpolation = Interpolation.CUBIC,
    threading: bool = True,
) -> ty.Dict[int, ty.List[str]]:
    """Save a set number of images from each scene, given a list of scenes
    and the associated video/frame source.

    Arguments:
        scene_list: A list of scenes (pairs of FrameTimecode objects) returned
            from calling a SceneManager's detect_scenes() method.
        video: A VideoStream object corresponding to the scene list.
            Note that the video will be closed/re-opened and seeked through.
        num_images: Number of images to generate for each scene.  Minimum is 1.
        frame_margin: Number of frames to pad each scene around the beginning
            and end (e.g. moves the first/last image into the scene by N frames).
            Can set to 0, but will result in some video files failing to extract
            the very last frame.
        image_extension: Type of image to save (must be one of 'jpg', 'png', or 'webp').
        encoder_param: Quality/compression efficiency, based on type of image:
            'jpg' / 'webp':  Quality 0-100, higher is better quality.  100 is lossless for webp.
            'png': Compression from 1-9, where 9 achieves best filesize but is slower to encode.
        image_name_template: Template to use for naming image files. Can use the template variables
            $VIDEO_NAME, $SCENE_NUMBER, $IMAGE_NUMBER, $TIMECODE, $FRAME_NUMBER, $TIMESTAMP_MS.
            Should not include an extension.
        output_dir: Directory to output the images into.  If not set, the output
            is created in the working directory.
        show_progress: If True, shows a progress bar if tqdm is installed.
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
        threading: Offload image encoding and disk IO to background threads to improve performance.

    Returns:
        Dictionary of the format { scene_num : [image_paths] }, where scene_num is the
        number of the scene in scene_list (starting from 1), and image_paths is a list of
        the paths to the newly saved/created images.

    Raises:
        ValueError: Raised if any arguments are invalid or out of range (e.g.
        if num_images is negative).
    """

    if not scene_list:
        return {}
    if num_images <= 0 or frame_margin < 0:
        raise ValueError()

    # TODO: Validate that encoder_param is within the proper range.
    # Should be between 0 and 100 (inclusive) for jpg/webp, and 1-9 for png.
    imwrite_param = (
        [get_cv2_imwrite_params()[image_extension], encoder_param]
        if encoder_param is not None
        else []
    )
    video.reset()

    if threading:
        extractor = _ImageExtractor(
            num_images,
            frame_margin,
            image_extension,
            imwrite_param,
            image_name_template,
            scale,
            height,
            width,
            interpolation,
        )
        return extractor.run(video, scene_list, output_dir, show_progress)

    # Setup flags and init progress bar if available.
    completed = True
    logger.info(
        f"Saving {num_images} images per scene [format={image_extension}] {output_dir if output_dir else ''} "
    )
    progress_bar = None
    if show_progress:
        progress_bar = tqdm(total=len(scene_list) * num_images, unit="images", dynamic_ncols=True)

    filename_template = Template(image_name_template)

    scene_num_format = "%0"
    scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + "d"
    image_num_format = "%0"
    image_num_format += str(math.floor(math.log(num_images, 10)) + 2) + "d"

    framerate = scene_list[0][0]._framerate

    # TODO(v1.0): Split up into multiple sub-expressions so auto-formatter works correctly.
    timecode_list = [
        [
            FrameTimecode(int(f), fps=framerate)
            for f in (
                # middle frames
                a[len(a) // 2]
                if (0 < j < num_images - 1) or num_images == 1
                # first frame
                else min(a[0] + frame_margin, a[-1])
                if j == 0
                # last frame
                else max(a[-1] - frame_margin, a[0])
                # for each evenly-split array of frames in the scene list
                for j, a in enumerate(np.array_split(r, num_images))
            )
        ]
        for i, r in enumerate(
            [
                # pad ranges to number of images
                r if 1 + r[-1] - r[0] >= num_images else list(r) + [r[-1]] * (num_images - len(r))
                # create range of frames in scene
                for r in (
                    range(
                        start.frame_num,
                        start.frame_num
                        + max(
                            1,  # guard against zero length scenes
                            end.frame_num - start.frame_num,
                        ),
                    )
                    # for each scene in scene list
                    for start, end in scene_list
                )
            ]
        )
    ]

    image_filenames = {i: [] for i in range(len(timecode_list))}
    aspect_ratio = video.aspect_ratio
    if abs(aspect_ratio - 1.0) < 0.01:
        aspect_ratio = None

    logger.debug("Writing images with template %s", filename_template.template)
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
                        FRAME_NUMBER=image_timecode.frame_num,
                        TIMESTAMP_MS=int(image_timecode.seconds * 1000),
                        TIMECODE=image_timecode.get_timecode().replace(":", ";"),
                    ),
                    image_extension,
                )
                image_filenames[i].append(file_path)
                # TODO: Combine this resize with the ones below.
                if aspect_ratio is not None:
                    frame_im = cv2.resize(
                        frame_im, (0, 0), fx=aspect_ratio, fy=1.0, interpolation=interpolation.value
                    )
                frame_height = frame_im.shape[0]
                frame_width = frame_im.shape[1]

                # Figure out what kind of resizing needs to be done
                if height or width:
                    if height and not width:
                        factor = height / float(frame_height)
                        width = int(factor * frame_width)
                    if width and not height:
                        factor = width / float(frame_width)
                        height = int(factor * frame_height)
                    assert height > 0 and width > 0
                    frame_im = cv2.resize(
                        frame_im, (width, height), interpolation=interpolation.value
                    )
                elif scale:
                    frame_im = cv2.resize(
                        frame_im, (0, 0), fx=scale, fy=scale, interpolation=interpolation.value
                    )
                path = Path(get_and_create_path(file_path, output_dir))
                (is_ok, encoded) = cv2.imencode(f".{image_extension}", frame_im, imwrite_param)
                if is_ok:
                    encoded.tofile(path)
                else:
                    logger.error(f"Failed to encode image for {file_path}")
            #
            else:
                completed = False
                break
            if progress_bar is not None:
                progress_bar.update(1)

    if progress_bar is not None:
        progress_bar.close()

    if not completed:
        logger.error("Could not generate all output images.")

    return image_filenames
