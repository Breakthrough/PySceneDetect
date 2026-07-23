#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Shared test helpers."""

import contextlib
import typing as ty

from click.testing import CliRunner

from scenedetect._cli import scenedetect as _scenedetect_cli
from scenedetect._cli.context import CliContext
from scenedetect._cli.controller import run_scenedetect


def close_video_stream(stream: ty.Any) -> None:
    """Deterministically release a VideoStream's native resources.

    `VideoStream` has no public close()/context-manager API, so tests release the
    backend-specific handles directly. Closing while the interpreter is healthy avoids
    ResourceWarnings (and native teardown work) at interpreter shutdown. Safe to call
    multiple times; never raises.
    """
    backend = getattr(stream, "BACKEND_NAME", None)
    if backend == "pyav":
        # Close the decode generator first to break its cycle with the container. `_io` is
        # the file handle backing the container (opened by the stream when given a path).
        for attr in ("_decoder", "_container", "_io"):
            handle = getattr(stream, attr, None)
            if handle is not None:
                with contextlib.suppress(Exception):
                    handle.close()
    elif backend == "opencv":
        cap = getattr(stream, "_cap", None)
        if cap is not None:
            with contextlib.suppress(Exception):
                cap.release()
    elif backend == "moviepy":
        reader = getattr(stream, "_reader", None)
        if reader is not None:
            with contextlib.suppress(Exception):
                reader.close()


def invoke_cli(args: list[str], catch_exceptions: bool = False) -> tuple[int, str]:
    """Invoke the scenedetect CLI in-process using Click's CliRunner.

    Replicates the two-step execution of ``__main__.py``:

    1. ``scenedetect.main(obj=context)`` - parse args and register callbacks on ``CliContext``
    2. ``run_scenedetect(context)`` - execute detection and output commands

    Returns ``(exit_code, output_text)``.
    """
    context = CliContext()
    runner = CliRunner()
    try:
        result = runner.invoke(
            _scenedetect_cli, args, obj=context, catch_exceptions=catch_exceptions
        )
        if result.exit_code == 0:
            run_scenedetect(context)
        return result.exit_code, result.output
    finally:
        # The CLI opens a VideoStream on `context` and has no teardown path; close it here so
        # its native handles are released deterministically instead of at interpreter shutdown.
        if context.video_stream is not None:
            close_video_stream(context.video_stream)
