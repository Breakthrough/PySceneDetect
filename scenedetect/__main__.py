#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2024 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Entry point for PySceneDetect's command-line interface."""

import sys
from logging import getLogger

from scenedetect._cli import scenedetect
from scenedetect._cli.context import CliContext
from scenedetect._cli.controller import run_scenedetect
from scenedetect.platform import FakeTqdmLoggingRedirect, logging_redirect_tqdm


def main():
    """PySceneDetect command-line interface (CLI) entry point."""
    context = CliContext()
    try:
        # Process command line arguments and subcommands to initialize the context.
        scenedetect.main(obj=context)  # Parse CLI arguments with registered callbacks.
    except SystemExit as exit:
        help_command = any(arg in sys.argv for arg in ["-h", "--help"])
        if help_command or exit.code != 0:
            raise

    # If we get here, processing the command line and loading the context worked. Let's run
    # the controller if we didn't process any help requests.
    logger = getLogger("pyscenedetect")
    # Ensure log messages don't conflict with any progress bars. If we're in quiet mode, where
    # no progress bars get created, we instead create a fake context manager. This is done here
    # to avoid needing a separate context manager at each point a progress bar is created.
    log_redirect = (
        FakeTqdmLoggingRedirect() if context.quiet_mode else logging_redirect_tqdm(loggers=[logger])
    )

    with log_redirect:
        try:
            run_scenedetect(context)
        except KeyboardInterrupt:
            logger.info("Stopped.")
            if __debug__:
                raise
        except BaseException as ex:
            if __debug__:
                raise
            else:
                logger.critical("ERROR: Unhandled exception:", exc_info=ex)
                raise SystemExit(1) from None


if __name__ == "__main__":
    main()
