#!/usr/bin/env python
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the
# included LICENSE file or visit one of the following pages for details:
#  - http://www.bcastell.com/projects/pyscenedetect/
#  - https://github.com/Breakthrough/PySceneDetect/
#
# This software uses Numpy and OpenCV; see the LICENSE-NUMPY and
# LICENSE-OPENCV files or visit one of above URLs for details.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.__main__ Module

Provides functionality to run PySceneDetect directly as a Python module (in
addition to using in other scripts via `import scenedetect`) by running:

  > python -m scenedetect

This module provides a high-level main() function, utilizing the scenedetect.cli
module, itself based on the click library, to provide command-line interface (CLI)
parsing functionality.  Also note that a convenience script scenedetect.py is also
included for development purposes (allows ./scenedetect.py vs python -m scenedetect)

Installing PySceneDetect (using `python setup.py install` in the parent directory)
will also add the `scenedetect` command to %PATH% be used from anywhere.
"""


def main():

    import scenedetect.cli
    from scenedetect.cli import CliContext

    cli_ctx = CliContext()
    # pylint: disable=unexpected-keyword-arg, no-value-for-parameter
    scenedetect.cli.cli.main(obj=cli_ctx)

if __name__ == '__main__':
    main()
