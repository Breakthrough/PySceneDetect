# Video file used by test_video_file fixture.
import os

import pytest

TEST_VIDEO_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "testvideo.mp4")


@pytest.fixture
def test_video_file():
    # type: () -> str
    """ Fixture for test video file path (ensures file exists).

    Access in test case by adding a test_video_file argument to obtain the path.
    """
    print(TEST_VIDEO_FILE)
    if not os.path.exists(TEST_VIDEO_FILE):
        raise FileNotFoundError(
            'Test video file (%s) must be present to run test cases' % TEST_VIDEO_FILE)
    return TEST_VIDEO_FILE
