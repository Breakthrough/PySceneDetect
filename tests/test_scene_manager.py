#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""PySceneDetect scenedetect.scene_manager Tests

This file includes unit tests for the scenedetect.scene_manager.SceneManager class,
which applies SceneDetector algorithms on VideoStream backends.
"""

from fractions import Fraction

import pytest

from scenedetect import SceneDetector, open_video
from scenedetect.backends.opencv import VideoStreamCv2
from scenedetect.common import FramePosition, Timecode
from scenedetect.detectors import AdaptiveDetector, ContentDetector
from scenedetect.scene_manager import SceneManager, _resolve_end_time, expand_scenes_to_bounds
from scenedetect.video_stream import FrameNumbering

TEST_VIDEO_START_FRAMES_ACTUAL = [150, 180, 394]


def test_scene_list(test_video_file):
    """Test SceneManager get_scene_list method with VideoStreamCv2/ContentDetector."""
    video = VideoStreamCv2(test_video_file, frame_numbering=FrameNumbering.SOURCE)
    sm = SceneManager()
    sm.add_detector(ContentDetector())

    start_time = 5.0
    end_time = 10.0

    assert end_time > start_time

    video.seek(start_time)
    sm.auto_downscale = True

    num_frames = sm.detect_scenes(video=video, end_time=end_time)

    # This CFR fixture contributes source frames 150 through 299.
    assert num_frames == 150

    scene_list = sm.get_scene_list()
    assert scene_list
    # Each scene is in the format (start position, end position).
    assert len(scene_list[0]) == 2

    # The selected source frame range is [150, 300).
    assert scene_list[0][0].frame_number == 150
    assert scene_list[-1][1].frame_number == 300
    # The final timestamp still belongs to the last processed frame.
    assert isinstance(video.position, FramePosition)
    assert scene_list[-1][1].timecode == video.position.timecode

    for i, _ in enumerate(scene_list):
        assert scene_list[i][0].frame_number < scene_list[i][1].frame_number
        if i > 0:
            # Ensure frame list is sorted (i.e. end time frame of
            # one scene is equal to the start time of the next).
            assert scene_list[i - 1][1] == scene_list[i][0]


def test_get_scene_list_start_in_scene(test_video_file):
    """Test SceneManager `get_scene_list()` method with the `start_in_scene` flag."""
    video = VideoStreamCv2(test_video_file, frame_numbering=FrameNumbering.SOURCE)
    sm = SceneManager()
    sm.add_detector(ContentDetector())

    # End time must be short enough that we won't detect any scenes.
    end_time = 25
    sm.auto_downscale = True
    sm.detect_scenes(video=video, end_time=end_time)
    # Should be an empty list.
    assert len(sm.get_scene_list()) == 0
    # Should be a list with a single element spanning the processed range.
    scene_list = sm.get_scene_list(start_in_scene=True)
    assert len(scene_list) == 1
    assert scene_list[0][0].frame_number == 0
    assert scene_list[0][1].frame_number == end_time


# TODO: This would be more readable if the callbacks were defined within the test case, e.g.
# split up the callback function and callback lambda test cases.
class FakeCallback:
    """Fake callback used for testing. Tracks the frame numbers the callback was invoked with."""

    def __init__(self):
        self.scene_list: list[int] = []

    def get_callback_lambda(self):
        """For testing using a lambda.."""
        return lambda image, position: self._callback(image, position)

    def get_callback_func(self):
        """For testing using a callback function."""

        def callback(image, position):
            nonlocal self
            self._callback(image, position)

        return callback

    def _callback(self, image, position: FramePosition):
        self.scene_list.append(position.frame_number)


def test_detect_scenes_callback(test_video_file):
    """Test SceneManager detect_scenes method with a callback function.

    Note that the API signature of the callback will undergo breaking changes in v1.0.
    """
    video = VideoStreamCv2(test_video_file, frame_numbering=FrameNumbering.SOURCE)
    sm = SceneManager()
    sm.add_detector(ContentDetector())

    fake_callback = FakeCallback()

    start_time = 5.0
    end_time = 15.0
    video.seek(start_time)
    sm.auto_downscale = True

    _ = sm.detect_scenes(
        video=video, end_time=end_time, callback=fake_callback.get_callback_lambda()
    )
    scene_list = sm.get_scene_list()
    assert [start.frame_number for start, _ in scene_list] == TEST_VIDEO_START_FRAMES_ACTUAL
    assert fake_callback.scene_list == TEST_VIDEO_START_FRAMES_ACTUAL[1:]

    # Perform same test using callback function instead of lambda.
    sm.clear()
    sm.add_detector(ContentDetector())
    fake_callback = FakeCallback()
    video.seek(start_time)

    _ = sm.detect_scenes(video=video, end_time=end_time, callback=fake_callback.get_callback_func())
    scene_list = sm.get_scene_list()
    assert [start.frame_number for start, _ in scene_list] == TEST_VIDEO_START_FRAMES_ACTUAL
    assert fake_callback.scene_list == TEST_VIDEO_START_FRAMES_ACTUAL[1:]


def test_detect_scenes_callback_adaptive(test_video_file):
    """Test SceneManager detect_scenes method with a callback function and a detector which
    requires frame buffering.

    Note that the API signature of the callback will undergo breaking changes in v1.0.
    """
    video = VideoStreamCv2(test_video_file, frame_numbering=FrameNumbering.SOURCE)
    sm = SceneManager()
    sm.add_detector(AdaptiveDetector())

    fake_callback = FakeCallback()

    start_time = 5.0
    end_time = 15.0
    video.seek(start_time)
    sm.auto_downscale = True

    _ = sm.detect_scenes(
        video=video, end_time=end_time, callback=fake_callback.get_callback_lambda()
    )
    scene_list = sm.get_scene_list()
    assert [start.frame_number for start, _ in scene_list] == TEST_VIDEO_START_FRAMES_ACTUAL
    assert fake_callback.scene_list == TEST_VIDEO_START_FRAMES_ACTUAL[1:]

    # Perform same test using callback function instead of lambda.
    sm.clear()
    sm.add_detector(AdaptiveDetector())
    fake_callback = FakeCallback()
    video.seek(start_time)

    _ = sm.detect_scenes(video=video, end_time=end_time, callback=fake_callback.get_callback_func())
    scene_list = sm.get_scene_list()
    assert [start.frame_number for start, _ in scene_list] == TEST_VIDEO_START_FRAMES_ACTUAL
    assert fake_callback.scene_list == TEST_VIDEO_START_FRAMES_ACTUAL[1:]


def test_detect_scenes_crop(test_video_file):
    video = VideoStreamCv2(test_video_file, frame_numbering=FrameNumbering.SOURCE)
    sm = SceneManager()
    sm.crop = (10, 10, 1900, 1000)
    sm.add_detector(ContentDetector())

    start_time = 5.0
    end_time = 15.0
    video.seek(start_time)
    sm.auto_downscale = True

    _ = sm.detect_scenes(video=video, end_time=end_time)
    scene_list = sm.get_scene_list()
    assert [start.frame_number for start, _ in scene_list] == TEST_VIDEO_START_FRAMES_ACTUAL


def test_crop_invalid():
    sm = SceneManager()
    sm.crop = None  # type: ignore[assignment]
    sm.crop = (0, 0, 0, 0)
    sm.crop = (1, 1, 0, 0)
    sm.crop = (0, 0, 1, 1)
    with pytest.raises(TypeError):
        sm.crop = 1  # type: ignore[assignment]
    with pytest.raises(TypeError):
        sm.crop = (1, 1)  # type: ignore[assignment]
    with pytest.raises(TypeError):
        sm.crop = (1, 1, 1)  # type: ignore[assignment]
    with pytest.raises(ValueError):
        sm.crop = (1, 1, 1, -1)


def _position(frame_number: int) -> FramePosition:
    return FramePosition(
        timecode=Timecode(pts=frame_number, time_base=Fraction(1, 10)),
        frame_number=frame_number,
    )


def test_expand_scenes_to_bounds_two_scenes():
    """Scenes detected inside a sub-window should be extended outward."""
    p0 = _position(0)
    p130 = _position(130)
    p150 = _position(150)
    p170 = _position(170)
    p300 = _position(300)

    scenes = [(p130, p150), (p150, p170)]
    expanded = expand_scenes_to_bounds(scenes, start=p0, end=p300)

    assert expanded == [(p0, p150), (p150, p300)]


def test_expand_scenes_to_bounds_empty():
    """Empty scene lists pass through unchanged."""
    assert expand_scenes_to_bounds([], _position(0), _position(10)) == []


def test_expand_scenes_to_bounds_single_scene():
    """A single scene gets both endpoints extended."""
    p0 = _position(0)
    p130 = _position(130)
    p170 = _position(170)
    p300 = _position(300)

    scenes = [(p130, p170)]
    expanded = expand_scenes_to_bounds(scenes, start=p0, end=p300)

    assert expanded == [(p0, p300)]


def test_expand_scenes_to_bounds_does_not_mutate_input():
    """The input scene list must not be modified in place."""
    p0 = _position(0)
    p130 = _position(130)
    p150 = _position(150)
    p170 = _position(170)
    p300 = _position(300)

    scenes = [(p130, p150), (p150, p170)]
    original = list(scenes)
    expand_scenes_to_bounds(scenes, start=p0, end=p300)

    assert scenes == original


@pytest.mark.parametrize(
    ("start", "end", "frame_numbering", "expected"),
    [
        (10, None, FrameNumbering.RELATIVE, None),
        (None, 15, FrameNumbering.RELATIVE, 15),
        (10, "0.125s", FrameNumbering.RELATIVE, Fraction(1, 8)),
        ("0.3s", 15, FrameNumbering.SOURCE, 15),
        (15, 10, FrameNumbering.RELATIVE, 0),
    ],
)
def test_resolve_end_time(start, end, frame_numbering, expected):
    result = _resolve_end_time(start, end, frame_numbering)
    if isinstance(expected, Fraction):
        assert isinstance(result, Timecode)
        assert result.seconds == expected
    else:
        assert result == expected


def test_resolve_end_time_rejects_unknown_relative_origin():
    with pytest.raises(ValueError, match="timestamp start"):
        _resolve_end_time("0.3s", 15, FrameNumbering.RELATIVE)


@pytest.mark.parametrize("backend", ["opencv", "pyav"])
@pytest.mark.parametrize("frame_skip", [0, 3])
def test_time_cutoff_preserves_next_frame(
    test_vfr_drop3_video: str, auto_close, backend: str, frame_skip: int
):
    """Stop before the timestamp cutoff, including during a skipped-frame sequence."""
    processed: list[int] = []

    class RecordingDetector(SceneDetector):
        def process_frame(self, position: FramePosition, frame_img) -> list[FramePosition]:
            processed.append(position.frame_number)
            return []

    reference = auto_close(open_video(test_vfr_drop3_video, backend=backend))
    for _ in range(6):
        assert reference.read(decode=False) is True
    last_included = reference.position
    assert isinstance(last_included, FramePosition)
    assert reference.read(decode=False) is True
    first_excluded = reference.position
    assert isinstance(first_excluded, FramePosition)

    video = auto_close(open_video(test_vfr_drop3_video, backend=backend))
    manager = SceneManager()
    manager.add_detector(RecordingDetector())
    num_frames = manager.detect_scenes(
        video=video,
        end_time=first_excluded.timecode,
        frame_skip=frame_skip,
    )

    assert num_frames == 6
    assert processed == list(range(0, 6, frame_skip + 1))
    assert video.position == last_included

    scene_list = manager.get_scene_list(start_in_scene=True)
    assert len(scene_list) == 1
    assert scene_list[0][1].frame_number == 6

    assert video.peek_timecode() == first_excluded.timecode
    assert video.read(decode=False) is True
    assert video.position == first_excluded
