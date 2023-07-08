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

import sys

from scenedetect._cli import scenedetect_command
from scenedetect._cli.context import CliContext
from scenedetect._cli.controller import run_scenedetect


def main():
    """PySceneDetect command-line interface (CLI) entry point."""
    cli_ctx = CliContext()
    try:
        # Process command line arguments and subcommands to initialize the context.
        scenedetect_command.main(obj=cli_ctx) # Parse CLI arguments with registered callbacks.
    except SystemExit as exit:
        if exit.code != 0:
            raise

    # If we get here, processing the command line and loading the context worked. Let's run
    # the controller if we didn't process any help requests.
    if not ('-h' in sys.argv or '--help' in sys.argv):
        run_scenedetect(cli_ctx)


if __name__ == '__main__':
    main()
