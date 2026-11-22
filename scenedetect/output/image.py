#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2025 Brandon Castellano <http://www.bcastell.com>.
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
from fractions import Fraction
from pathlib import Path
from string import Template

import cv2
import numpy as np

from scenedetect.common import (
    FramePosition,
    Interpolation,
    SceneList,
    Timecode,
    TimecodeLike,
    parse_frame_or_time,
)
from scenedetect.platform import StrPath, get_and_create_path, get_cv2_imwrite_params, tqdm
from scenedetect.video_stream import VideoStream

logger = logging.getLogger("pyscenedetect")


def _get_num_images(
    scene_list: SceneList,
    num_images: int | None,
    interval: TimecodeLike | None,
    min_images: int,
    max_images: int | None,
) -> list[int]:
    """Get the number of images to generate for each scene in `scene_list`.

    If `interval` is set, each scene gets ``floor(scene length / interval) + 1`` images, clamped
    to [`min_images`, `max_images`]. Otherwise, each scene gets `num_images`.
    """
    if interval is None:
        assert num_images is not None
        return [num_images] * len(scene_list)
    parsed_interval = parse_frame_or_time(interval)
    result = []
    for start, end in scene_list:
        duration = end - start
        scene_length = duration.frames if isinstance(parsed_interval, int) else duration.elapsed
        num_intervals = scene_length // parsed_interval
        scene_images = max(num_intervals + 1, min_images)
        if max_images is not None:
            scene_images = min(scene_images, max_images)
        result.append(scene_images)
    return result


def _generate_timecode_list(
    scene_list: SceneList,
    num_images_per_scene: list[int],
    frame_margin: TimecodeLike,
    frame_rate: Fraction,
) -> list[list[Timecode]]:
    """Generate per-scene image targets using timestamps and frame-rate estimates.

    `num_images_per_scene` is the number of images to generate for each scene in `scene_list`.
    `frame_margin` accepts any :data:`TimecodeLike` value (e.g. ``int`` frames, ``float``
    seconds, or ``str`` such as ``"0.1s"``).
    Frame-count margins and the final-frame clamp use ``frame_rate`` and are
    approximate for VFR sources.
    """
    # TODO: Define VFR sampling and padding semantics. Handle any frame-count
    # margins during extraction without FPS conversion.
    parsed_margin = parse_frame_or_time(frame_margin)
    margin_secs = parsed_margin / frame_rate if isinstance(parsed_margin, int) else parsed_margin
    frame_secs = 1 / frame_rate
    result = []
    for (start, end), num_images in zip(scene_list, num_images_per_scene, strict=True):
        duration_secs = (end - start).elapsed
        if duration_secs <= 0:
            result.append([start.timecode] * num_images)
            continue
        segment_secs = duration_secs / num_images
        # Estimate the final frame time using the frame rate, without going before scene start.
        last_frame_secs = max(end.timecode.seconds - frame_secs, start.timecode.seconds)
        timecodes = []
        for j in range(num_images):
            seg_start = start.timecode.seconds + j * segment_secs
            seg_end = start.timecode.seconds + (j + 1) * segment_secs
            if num_images == 1:
                t = start.timecode.seconds + duration_secs / 2
            elif j == 0:
                t = min(seg_start + margin_secs, seg_end)
            elif j == num_images - 1:
                t = max(last_frame_secs - margin_secs, seg_start)
            else:
                t = (seg_start + seg_end) / 2
            t = min(t, last_frame_secs)
            timecodes.append(Timecode(pts=t.numerator, time_base=Fraction(1, t.denominator)))
        result.append(timecodes)
    return result


def _describe_num_images(
    num_images: int | None, interval: TimecodeLike | None, total_images: int
) -> str:
    if interval is None:
        return f"{num_images} images per scene"
    return f"{total_images} images (interval: {interval})"


def _scale_image(
    image: np.ndarray,
    aspect_ratio: float | None,
    height: int | None,
    width: int | None,
    scale: float | None,
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
        elif width and not height:
            factor = width / float(image_width)
            height = int(factor * image_height)
        assert height is not None
        assert width is not None
        assert height > 0 and width > 0
        image = cv2.resize(image, (width, height), interpolation=interpolation.value)
    elif scale:
        image = cv2.resize(image, (0, 0), fx=scale, fy=scale, interpolation=interpolation.value)
    return image


class _ImageExtractor:
    def __init__(
        self,
        num_images: int | None = 3,
        frame_margin: TimecodeLike = 1,
        image_extension: str = "jpg",
        imwrite_param: list[int] | None = None,
        image_name_template: str = "$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER",
        scale: float | None = None,
        height: int | None = None,
        width: int | None = None,
        interpolation: Interpolation = Interpolation.CUBIC,
        interval: TimecodeLike | None = None,
        min_images: int = 1,
        max_images: int | None = None,
    ):
        """Multi-threaded implementation of save-images functionality. Uses background threads to
        handle image encoding and saving images to disk to improve parallelism.

        This object is thread-safe.

        Arguments:
            num_images: Number of images to generate for each scene.  Minimum is 1. Must be None
                if `interval` is set.
            frame_margin: Padding around the beginning and end of each scene used when
                selecting which frames to extract. Accepts an int (frames), float (seconds),
                or str (e.g. ``"0.1s"``, ``"00:00:00.100"``). Can be 0, but some video files
                may then fail to extract the very last frame.
                Frame-count margins use the video's frame rate and are approximate for VFR.
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
            interval: If set, generate one image per `interval` of each scene's length instead of
                `num_images`, see :func:`save_images`.
            min_images: Minimum number of images to generate for each scene with `interval`.
            max_images: Maximum number of images to generate for each scene with `interval`.
        """
        self._num_images = num_images
        self._interval = interval
        self._min_images = min_images
        self._max_images = max_images
        self._frame_margin = frame_margin
        self._image_extension = image_extension
        self._image_name_template = image_name_template
        self._scale = scale
        self._height = height
        self._width = width
        self._interpolation = interpolation
        self._imwrite_param: list[int] = imwrite_param if imwrite_param is not None else []

    def run(
        self,
        video: VideoStream,
        scene_list: SceneList,
        output_dir: StrPath | None = None,
        show_progress=False,
    ) -> dict[int, list[str]]:
        """Run image extraction on `video` using the current parameters. Thread-safe.

        Arguments:
            video: The video to process.
            scene_list: The scenes detected in the video.
            output_dir: Directory to write files to.
            show_progress: If `true` and tqdm is available, shows a progress bar.
        """
        timecode_list = self.generate_timecode_list(scene_list, video.frame_rate)
        total_images = sum(len(timecodes) for timecodes in timecode_list)
        max_scene_images = max(len(timecodes) for timecodes in timecode_list)

        # Setup flags and init progress bar if available.
        completed = True
        logger.info(
            f"Saving {_describe_num_images(self._num_images, self._interval, total_images)}"
            f" [format={self._image_extension}] {output_dir if output_dir else ''} "
        )
        progress_bar = None
        if show_progress:
            progress_bar = tqdm(total=total_images, unit="images", dynamic_ncols=True)

        image_filenames = {i: [] for i in range(len(timecode_list))}

        filename_template = Template(self._image_name_template)
        logger.debug("Writing images with template %s", filename_template.template)
        scene_num_format = "%0"
        scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + "d"
        image_num_format = "%0"
        image_num_format += str(math.floor(math.log(max_scene_images, 10)) + 2) + "d"

        def format_filename(scene_number: int, image_number: int, position: FramePosition):
            return "{}.{}".format(
                filename_template.safe_substitute(
                    VIDEO_NAME=video.name,
                    SCENE_NUMBER=scene_num_format % (scene_number + 1),
                    IMAGE_NUMBER=image_num_format % (image_number + 1),
                    FRAME_NUMBER=position.frame_number,
                    TIMESTAMP_MS=int(position.timecode.seconds * 1000),
                    TIMECODE=position.timecode.get_timecode().replace(":", ";"),
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
                if isinstance(frame_im, np.ndarray):
                    position = video.position
                    assert position is not None
                    file_path = format_filename(i, j, position)
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

    def generate_timecode_list(
        self, scene_list: SceneList, frame_rate: Fraction
    ) -> list[list[Timecode]]:
        """Generates a list of timecodes for each scene in `scene_list` based on the current config
        parameters.

        Uses scene timestamps to calculate image extraction targets.
        """
        num_images_per_scene = _get_num_images(
            scene_list, self._num_images, self._interval, self._min_images, self._max_images
        )
        return _generate_timecode_list(
            scene_list, num_images_per_scene, self._frame_margin, frame_rate
        )

    def resize_image(
        self,
        image: np.ndarray,
        aspect_ratio: float | None,
    ) -> np.ndarray:
        return _scale_image(
            image, aspect_ratio, self._height, self._width, self._scale, self._interpolation
        )


def save_images(
    scene_list: SceneList,
    video: VideoStream,
    num_images: int | None = None,
    frame_margin: TimecodeLike = 1,
    image_extension: str = "jpg",
    encoder_param: int = 95,
    image_name_template: str = "$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER",
    output_dir: StrPath | None = None,
    show_progress: bool | None = False,
    scale: float | None = None,
    height: int | None = None,
    width: int | None = None,
    interpolation: Interpolation = Interpolation.CUBIC,
    threading: bool = True,
    interval: TimecodeLike | None = None,
    min_images: int = 1,
    max_images: int | None = None,
) -> dict[int, list[str]]:
    """Save a set number of images from each scene, given a list of scenes
    and the associated video/frame source.

    Arguments:
        scene_list: A list of scenes (pairs of FramePosition objects) returned
            from calling a SceneManager's detect_scenes() method.
        video: A VideoStream object corresponding to the scene list.
            Note that the video will be closed/re-opened and seeked through.
        num_images: Number of images to generate for each scene.  Minimum is 1. Defaults to 3
            if `interval` is not set. Cannot be used with `interval`.
        frame_margin: Padding around the beginning and end of each scene used when
            selecting which frames to extract. Accepts an int (frames), float (seconds),
            or str (e.g. ``"0.1s"``, ``"00:00:00.100"``). Can be 0, but some video files
            may then fail to extract the very last frame.
            Frame-count margins use the video's frame rate and are approximate for VFR.
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
        interval: If set, the number of images for each scene depends on its length instead of
            being `num_images`: each scene gets ``floor(scene length / interval) + 1`` images,
            spread over the scene the same way. Accepts the same values as `frame_margin`.
            Cannot be used with `num_images`.
        min_images: Minimum number of images to generate for each scene with `interval`.
            Minimum is 1. Can only be set with `interval`.
        max_images: Maximum number of images to generate for each scene with `interval`, or
            None for no limit. Can only be set with `interval`.

    Returns:
        Dictionary of the format ``{scene_num: [image_paths]}``, where ``scene_num`` is the
        number of the scene in scene_list (starting from 1), and image_paths is a list of
        the paths to the newly saved/created images.

    Raises:
        ValueError: Raised if any arguments are invalid or out of range (e.g.
            if `num_images` is negative).
    """

    if not scene_list:
        return {}
    if interval is not None:
        if num_images is not None:
            raise ValueError("num_images and interval cannot both be set")
        if parse_frame_or_time(interval) <= 0:
            raise ValueError("interval must be greater than 0")
        if min_images <= 0:
            raise ValueError("min_images must be greater than 0")
        if max_images is not None and max_images < min_images:
            raise ValueError("max_images must be greater than or equal to min_images")
    else:
        if min_images != 1 or max_images is not None:
            raise ValueError("min_images and max_images can only be used with interval")
        if num_images is None:
            num_images = 3
    if num_images is not None and num_images <= 0:
        raise ValueError("num_images must be greater than 0")
    if isinstance(frame_margin, (int, float)) and frame_margin < 0:
        raise ValueError("frame_margin must be non-negative")

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
            interval,
            min_images,
            max_images,
        )
        return extractor.run(video, scene_list, output_dir, bool(show_progress))

    timecode_list = _generate_timecode_list(
        scene_list,
        _get_num_images(scene_list, num_images, interval, min_images, max_images),
        frame_margin,
        video.frame_rate,
    )
    total_images = sum(len(timecodes) for timecodes in timecode_list)
    max_scene_images = max(len(timecodes) for timecodes in timecode_list)

    # Setup flags and init progress bar if available.
    completed = True
    logger.info(
        f"Saving {_describe_num_images(num_images, interval, total_images)}"
        f" [format={image_extension}] {output_dir if output_dir else ''} "
    )
    progress_bar = None
    if show_progress:
        progress_bar = tqdm(total=total_images, unit="images", dynamic_ncols=True)

    filename_template = Template(image_name_template)

    scene_num_format = "%0"
    scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + "d"
    image_num_format = "%0"
    image_num_format += str(math.floor(math.log(max_scene_images, 10)) + 2) + "d"

    image_filenames = {i: [] for i in range(len(timecode_list))}
    aspect_ratio = video.aspect_ratio
    if abs(aspect_ratio - 1.0) < 0.01:
        aspect_ratio = None

    logger.debug("Writing images with template %s", filename_template.template)
    for i, scene_timecodes in enumerate(timecode_list):
        for j, image_timecode in enumerate(scene_timecodes):
            video.seek(image_timecode)
            frame_im = video.read()
            if isinstance(frame_im, np.ndarray):
                position = video.position
                assert position is not None
                # TODO: Add extension to template.
                # TODO: Allow NUM to be a valid suffix in addition to NUMBER.
                file_path = "{}.{}".format(
                    filename_template.safe_substitute(
                        VIDEO_NAME=video.name,
                        SCENE_NUMBER=scene_num_format % (i + 1),
                        IMAGE_NUMBER=image_num_format % (j + 1),
                        FRAME_NUMBER=position.frame_number,
                        TIMESTAMP_MS=int(position.timecode.seconds * 1000),
                        TIMECODE=position.timecode.get_timecode().replace(":", ";"),
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
                    elif width and not height:
                        factor = width / float(frame_width)
                        height = int(factor * frame_height)
                    assert height is not None
                    assert width is not None
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
