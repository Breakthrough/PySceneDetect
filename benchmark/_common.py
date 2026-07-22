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
"""Shared formatting and detector-registry helpers for ``python -m benchmark`` and
``python -m benchmark.sweep``.

Kept intentionally small: the two entry points have different prediction loops (one
default-kwargs pass vs a fan-out parameter sweep) but render results into the same
tables.
"""

from __future__ import annotations

import json
import math
from typing import Any

from benchmark.evaluator import BenchmarkResult
from scenedetect import (
    AdaptiveDetector,
    ContentDetector,
    HashDetector,
    HistogramDetector,
    ThresholdDetector,
)

DEFAULT_BACKEND = "opencv"

DETECTORS: dict[str, type] = {
    "detect-adaptive": AdaptiveDetector,
    "detect-content": ContentDetector,
    "detect-hash": HashDetector,
    "detect-hist": HistogramDetector,
    "detect-threshold": ThresholdDetector,
}


def parse_tolerances(spec: str) -> tuple[int, ...]:
    """Parse ``"0,1,5"`` into ``(0, 1, 5)``. Blank entries (e.g. trailing comma) are dropped."""
    return tuple(int(x.strip()) for x in spec.split(",") if x.strip())


def fmt_pct(value: float, count: int) -> str:
    """Percentage, or ``n/a`` when the underlying class has zero events."""
    return "n/a" if count == 0 else f"{value * 100:.2f}"


def fmt_offset(value: float) -> str:
    return "n/a" if math.isnan(value) else f"{value:.3f}"


def render_table(header: list[str], rows: list[list[str]]) -> str:
    """Build a pipe-delimited GitHub-flavored Markdown table as a single string."""
    widths = [max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(len(header))]
    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(header, widths, strict=True)) + " |"
    body = [
        "| " + " | ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)) + " |" for r in rows
    ]
    return "\n".join([header_line, sep, *body])


HARD_HEADER = ["Tolerance", "Precision", "Recall", "F1", "Offset", "Elapsed"]
FADE_HEADER = ["Tolerance", "Precision", "Recall", "F1"]


def hard_row(result: BenchmarkResult) -> list[str]:
    hard = result.hard_cuts
    hard_predictions = hard.matched + hard.false_positives
    hard_events = hard.matched + hard.missed
    return [
        str(result.tolerance),
        fmt_pct(hard.precision, hard_predictions),
        fmt_pct(hard.recall, hard_events),
        fmt_pct(hard.f1, hard_events),
        fmt_offset(result.mean_abs_offset_hard_cuts),
        f"{result.elapsed_mean:.2f}",
    ]


def fade_row(result: BenchmarkResult) -> list[str]:
    fades = result.fades
    fade_predictions = fades.matched + fades.false_positives
    fade_events = fades.matched + fades.missed
    return [
        str(result.tolerance),
        fmt_pct(fades.precision, fade_predictions),
        fmt_pct(fades.recall, fade_events),
        fmt_pct(fades.f1, fade_events),
    ]


def write_json(out_path: str, payload: dict[str, Any]) -> None:
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\nWrote results to {out_path}")
