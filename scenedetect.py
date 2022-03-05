# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site:   http://www.scenedetect.scenedetect.com/         ]
#     [  Docs:   http://manual.scenedetect.scenedetect.com/      ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#
# Copyright (C) 2014-2022 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#

# This is a convenience/backwards-compatibility script, and simply provides an
# alternative to running PySceneDetect from source (in addition to the standard
# python -m scenedetect).
if __name__ == "__main__":
    # pylint: disable=no-name-in-module
    from scenedetect.__main__ import main
    main()
