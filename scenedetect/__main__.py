# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/pyscenedetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2012-2018 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 2-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/pyscenedetect/
#
# This software uses Numpy, OpenCV, click, pytest, mkvmerge, and ffmpeg. See
# the included LICENSE-* files, or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect scenedetect.__main__ Module

Provides entry point for PySceneDetect's command-line interface (CLI)
functionality (in addition to using in other scripts via `import scenedetect`)
by installing the module and running the `scenedetect` command, or by calling:

  > python -m scenedetect

This module provides a high-level main() function, utilizing the scenedetect.cli
module, itself based on the click library, to provide command-line interface (CLI)
parsing functionality.  Also note that a convenience script scenedetect.py is also
included for development purposes (allows ./scenedetect.py vs python -m scenedetect)

Installing PySceneDetect (using `python setup.py install` in the parent directory)
will also add the `scenedetect` command to %PATH% be used from anywhere.
"""

import logging

# PySceneDetect Library Imports
from scenedetect.cli import CliContext
from scenedetect.cli import scenedetect_cli as cli

def main():
    """ Main: PySceneDetect command-line interface (CLI) entry point.

    Passes control flow to the CLI parser (using the click library), whose
    entry point is the decorated scenedetect.cli.scenedetect_cli function.
    """

    cli_ctx = CliContext()  # CliContext object passed between CLI commands.
    try:
        # pylint: disable=unexpected-keyword-arg, no-value-for-parameter
        cli.main(obj=cli_ctx)   # Parse CLI arguments with registered callbacks.
    finally:
        cli_ctx.cleanup()

if __name__ == '__main__':
    main()
