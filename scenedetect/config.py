# -*- coding: utf-8 -*-
#
#         VEGASSceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.hlinke.de/   ]
#     [  Github: coming soon  ]
#     [  Documentation: coming soon    ]
#
#  Copyright (C) 2019 Harold Linke <http://www.hlinke.de>.
# VEGASSceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file
#
# VEGASSceneDetect is based on pySceneDetect by Brandon Castellano
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses the Numpy, OpenCV, click, tqdm, and pytest libraries.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect config.py
this file reads configuration parameters for VegasScenedetect
"""

import json
import os

class SD_Config():
    """ Configuration of VEGASSCendetector """

    def __init__(self):
        # type: 
        """ SDConfig Constructor Method (__init__)

        Arguments:
            None

        Raises:
            None
        """
        
        #**VEGASPython**
        filedir = os.path.dirname(os.path.realpath(__file__))
        filepath = os.path.join(filedir, 'config.json')

        with open(filepath, "r") as read_file:
            data = json.load(read_file)

        self.useHSV           = False    # define if HSV or BGR should be used for content analysis - BGR is faster
        self.showPreview      = True   # defines, that the preview if the analysed video shoul dbe shown
        self.previewFrameSkip = 100      # defines the number of frames skipped before the preview is updated - lower numbers make the preview smoother but cost processing time
        self.showFrameValues  = False    # the values calculated for each frame are shown - can be used to chek the threshold for a cut
        self.threshold        = 30
        self.min_scene_len    = 15

        try:
            if "useHSV" in data:
                self.useHSV           = data["useHSV"]    # define if HSV or BGR should be used for content analysis - BGR is faster
            if "showPreview" in data:
                self.showPreview      = data["showPreview"]     # defines, that the preview if the analysed video shoul dbe shown
            if "PreviewFrameSkip" in data:
                self.PreviewFrameSkip = data["PreviewFrameSkip"]      # defines the number of frames skipped before the preview is updated - lower numbers make the preview smoother but cost processing time
            if "showFrameValues" in data:
                self.showFrameValues  = data["showFrameValues"]    # the values calculated for each frame are shown - can be used to chek the threshold for a cut
            if "threshold" in data:
                self.threshold = data["threshold"]       # threshold that needs to be exceeded to determine a cut
            if "min_scene_len" in data:
                self.min_scene_len = data["min_scene_len"] 
            if "print_parameters" in data:
                print("Parameters: useHSV:",self.useHSV, " showPreview:", self.showPreview, " PreviewFrameSkip:", self.PreviewFrameSkip, " showFrameValues:", self.showFrameValues, " Threshold:",self.threshold)
   
        except:
            print ("Error in Config File")
            print(data)
            print("useHSV:",self.useHSV, " showPreview:", self.showPreview, " PreviewFrameSkip:", self.PreviewFrameSkip, " showFrameValues:", self.showFrameValues, " Threshold:",self.threshold)
        #**/VEGASPython**
