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
""" ``scenedetect.__main__`` Module

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

# PySceneDetect Library Imports
from scenedetect.cli import scenedetect_cli as cli
from scenedetect.cli.context import CliContext


def main():
    """ Main: PySceneDetect command-line interface (CLI) entry point.

    Passes control flow to the CLI parser (using the click library), whose
    entry point is the decorated scenedetect.cli.scenedetect_cli function.

    Once options have been processed, the main program logic is executed in the
    :py:func:`scenedetect.cli.controller.run_scenedetect` function.
    """
    cli_ctx = CliContext() # CliContext object passed between CLI commands.
    cli.main(obj=cli_ctx)  # Parse CLI arguments with registered callbacks.


if __name__ == '__main__':
    main()
