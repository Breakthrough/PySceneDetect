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

"""The ``scenedetect.output.labels`` module adds *optional* semantic labels to the scenes found by
PySceneDetect. Pixel-based detectors locate the cuts; this helper sends each detected time range to
the `TwelveLabs <https://twelvelabs.io>`_ Pegasus video-understanding model and attaches a short
natural-language description to each scene.

This integration is entirely opt-in: it is never invoked by detection and requires the optional
``twelvelabs`` dependency (``pip install scenedetect[twelvelabs]``) plus a TwelveLabs API key. A
free key with a generous free tier is available at https://twelvelabs.io.

Per-scene labelling relies on Pegasus' ``start_time``/``end_time`` support, which currently requires
the ``pegasus1.5`` model with a ``video_url`` (or asset) source rather than a ``video_id``. Use the
same video you ran detection on so the timecodes line up::

    from scenedetect import detect, ContentDetector
    from scenedetect.output import label_scenes

    scenes = detect("my_video.mp4", ContentDetector())
    labels = label_scenes(scenes, video_url="https://example.com/my_video.mp4")
    for label in labels:
        print(label.index, label.label)

A ``video_id`` (already indexed) source is also accepted for models that support it.
"""

import logging
import os
import typing as ty
from dataclasses import dataclass

from scenedetect.common import SceneList

logger = logging.getLogger("pyscenedetect")

DEFAULT_MODEL: str = "pegasus1.5"
"""Default TwelveLabs Pegasus model used for scene labelling."""

DEFAULT_PROMPT: str = (
    "Describe what happens in this part of the video in a single concise sentence."
)
"""Default prompt sent to Pegasus for each scene."""


@dataclass
class SceneLabel:
    """A semantic label generated for a single detected scene. The list returned by
    :func:`label_scenes` runs parallel to (and in the same order as) the input scene list."""

    index: int
    """0-based index of the scene this label describes."""
    start_time: float
    """Scene start, in seconds from the beginning of the video."""
    end_time: float
    """Scene end, in seconds from the beginning of the video."""
    label: str
    """Natural-language description of the scene returned by Pegasus."""


def label_scenes(
    scene_list: SceneList,
    video_id: str | None = None,
    *,
    video_url: str | None = None,
    model_name: str = DEFAULT_MODEL,
    prompt: str = DEFAULT_PROMPT,
    max_tokens: int = 512,
    api_key: str | None = None,
    client: ty.Any | None = None,
) -> list[SceneLabel]:
    """Generate a semantic label for each scene using the TwelveLabs Pegasus model.

    Each scene's start/end timecode is forwarded to Pegasus so the description covers only that
    portion of the video. This is opt-in and does not affect detection in any way.

    Arguments:
        scene_list: Scenes to label, as returned by
            :meth:`SceneManager.get_scene_list()
            <scenedetect.scene_manager.SceneManager.get_scene_list>`
            or :func:`detect() <scenedetect.detect>`.
        video_id: ID of the video as already uploaded/indexed with TwelveLabs. Mutually exclusive
            with `video_url`; one of the two is required.
        video_url: Public URL of the video. Mutually exclusive with `video_id`.
        model_name: TwelveLabs Pegasus model to use (default: ``"pegasus1.5"``).
        prompt: Instruction sent to Pegasus for each scene.
        max_tokens: Maximum number of tokens Pegasus may generate per scene. Note that
            ``pegasus1.5`` requires this to be at least 512.
        api_key: TwelveLabs API key. Defaults to the ``TWELVELABS_API_KEY`` environment variable.
            Ignored when `client` is provided.
        client: Pre-configured ``twelvelabs.TwelveLabs`` client. If omitted, one is created from
            `api_key`.

    Returns:
        A list of :class:`SceneLabel`, one per input scene, in the same order as `scene_list`.

    Raises:
        ImportError: If the optional ``twelvelabs`` package is not installed.
        ValueError: If neither or both of `video_id`/`video_url` are given, or if no API key is
            available when constructing a client.
    """
    if (video_id is None) == (video_url is None):
        raise ValueError("Exactly one of 'video_id' or 'video_url' must be provided.")

    if client is None:
        client = _create_client(api_key)

    video_context = None
    if video_url is not None:
        from twelvelabs.types.video_context import VideoContext_Url

        video_context = VideoContext_Url(url=video_url)

    labels: list[SceneLabel] = []
    for index, (start, end) in enumerate(scene_list):
        start_seconds = start.seconds
        end_seconds = end.seconds
        response = client.analyze(
            model_name=model_name,
            video_id=video_id,
            video=video_context,
            prompt=prompt,
            max_tokens=max_tokens,
            start_time=start_seconds,
            end_time=end_seconds,
        )
        labels.append(
            SceneLabel(
                index=index,
                start_time=start_seconds,
                end_time=end_seconds,
                label=response.data.strip() if response.data else "",
            )
        )
        logger.debug("Labelled scene %d [%.3fs-%.3fs]", index, start_seconds, end_seconds)
    return labels


def _create_client(api_key: str | None) -> ty.Any:
    """Create a ``twelvelabs.TwelveLabs`` client, surfacing a friendly error if the optional
    dependency is missing or no API key is available."""
    try:
        from twelvelabs import TwelveLabs
    except ImportError as ex:
        raise ImportError(
            "The 'twelvelabs' package is required for scene labelling. Install it with:\n\n"
            "    pip install scenedetect[twelvelabs]\n\n"
            "Get a free API key at https://twelvelabs.io."
        ) from ex

    key = api_key if api_key is not None else os.environ.get("TWELVELABS_API_KEY")
    if not key:
        raise ValueError(
            "No TwelveLabs API key provided. Pass 'api_key=' or set the TWELVELABS_API_KEY "
            "environment variable. Get a free key at https://twelvelabs.io."
        )
    return TwelveLabs(api_key=key)
