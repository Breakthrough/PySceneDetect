# -*- coding: utf-8 -*-
#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2023 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Entry point for PySceneDetect's command-line interface."""

# PySceneDetect Library Imports
from scenedetect._cli import scenedetect_cli as cli
from scenedetect._cli.context import CliContext


def main():
    """PySceneDetect command-line interface (CLI) entry point.

    Passes control flow to the CLI parser (using the click library), whose
    entry point is the decorated scenedetect._cli.scenedetect_cli function.

    Once options have been processed, the main program logic is executed in the
    :func:`scenedetect._cli.controller.run_scenedetect` function.
    """
    cli_ctx = CliContext() # CliContext object passed between CLI commands.
    cli.main(obj=cli_ctx)  # Parse CLI arguments with registered callbacks.


if __name__ == '__main__':
    main()
