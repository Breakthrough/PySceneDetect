#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2025 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Shared test helpers."""

import typing as ty

from click.testing import CliRunner

from scenedetect._cli import scenedetect as _scenedetect_cli
from scenedetect._cli.context import CliContext
from scenedetect._cli.controller import run_scenedetect


def invoke_cli(args: list[str], catch_exceptions: bool = False) -> tuple[int, str]:
    """Invoke the scenedetect CLI in-process using Click's CliRunner.

    Replicates the two-step execution of ``__main__.py``:

    1. ``scenedetect.main(obj=context)`` — parse args and register callbacks on ``CliContext``
    2. ``run_scenedetect(context)`` — execute detection and output commands

    Returns ``(exit_code, output_text)``.
    """
    context = CliContext()
    runner = CliRunner()
    result = runner.invoke(_scenedetect_cli, args, obj=context, catch_exceptions=catch_exceptions)
    if result.exit_code == 0:
        run_scenedetect(context)
    return result.exit_code, result.output
