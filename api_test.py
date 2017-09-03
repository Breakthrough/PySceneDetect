
#
# PySceneDetect v0.5 API Test Script
#
# NOTE: This file can only be used with development versions of PySceneDetect,
#       and gives a high-level overview of how the new API will look and work.
#       This file is for development and testing purposes mostly, although it
#       also serves as a base for further example and test programs.
#

from __future__ import print_function

import scenedetect
import scenedetect.detectors
import scenedetect.manager


def main():

    print("Running PySceneDetect API test...")

    print("Version being used:")
    print(scenedetect.__version__)

    content_detector = scenedetect.detectors.ContentDetector()
    smgr = scenedetect.manager.SceneManager(detector = content_detector)

    scenedetect.detect_scenes_file("goldeneye.mp4", smgr)

    print("Detected %d scenes in video." % (len(smgr.scene_list)))

if __name__ == "__main__":
    main()

