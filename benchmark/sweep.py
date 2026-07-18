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
"""Parameter sweep harness for one detector on one dataset.

Brute-force grid search over a Cartesian product of detector parameters. The cost of
the grid is amortized using :class:`FanOutVideoStream`. One video decode per chunk of
``--workers`` cells, so a 100-cell grid on a 500-video corpus costs roughly
``500 * ceil(100 / workers)`` decodes, not ``500 * 100``.

Use ``--params "key=v1,v2,v3"`` for enumerated values and ``"key=a:b:s"`` for a numeric
``[a, b]`` range with step ``s`` (inclusive of ``b`` when the step lands there).
Multiple keys are separated by ``;`` and form a Cartesian product.

Example::

    python -m benchmark.sweep \\
      --detector detect-content --dataset BBC \\
      --params "threshold=15:35:1;min_scene_len=0.0:1.0:0.1" \\
      --tolerance 0,1 --workers 16 --out sweep.json

``min_scene_len`` is a :data:`TimecodeLike`: integers are frames, floats are seconds,
strings like ``"0.1s"`` or ``"00:00:00.500"`` also work. Prefer floats so the same
sweep is meaningful across datasets with different framerates.

Reports the top-10 cells by F1 at each tolerance plus the Pareto front across the two
tolerances. The full grid lives in the JSON output for offline plotting.
"""

from __future__ import annotations

import argparse
import itertools
import threading
import time
from pathlib import Path
from typing import Any

from tqdm import tqdm

from benchmark._common import (
    DEFAULT_BACKEND,
    DETECTORS,
    parse_tolerances,
    render_table,
    write_json,
)
from benchmark.dataset import DATASETS, Dataset, resolve_dataset
from benchmark.evaluator import BenchmarkResult, Prediction, evaluate
from scenedetect import AVAILABLE_BACKENDS, SceneManager, open_video
from scenedetect._fan_out import FanOutVideoStream

# --------------------------------------------------------------------- #
# Spec language: "key=v1,v2,v3" or "key=a:b:s"; clauses joined by ";".
# --------------------------------------------------------------------- #


def _coerce(token: str) -> Any:
    """Best-effort scalar coercion. Order: None, bool, int, float, str."""
    t = token.strip()
    if t == "None":
        return None
    if t == "True":
        return True
    if t == "False":
        return False
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def _expand_values(s: str) -> list[Any]:
    if ":" in s:
        parts = s.split(":")
        if len(parts) != 3:
            raise ValueError(f"Range spec must be 'start:stop:step', got {s!r}")
        a, b, step = _coerce(parts[0]), _coerce(parts[1]), _coerce(parts[2])
        if not all(isinstance(x, (int, float)) for x in (a, b, step)):
            raise ValueError(f"Range bounds must be numeric, got {s!r}")
        if step == 0:
            raise ValueError(f"Range step must be non-zero, got {s!r}")
        out: list[Any] = []
        v = a
        # Small epsilon to keep an inclusive upper bound robust against float drift.
        epsilon = abs(step) * 1e-9 if isinstance(step, float) else 0
        # Direction-aware: support a > b with negative step too.
        if step > 0:
            while v <= b + epsilon:
                out.append(v)
                v = v + step
        else:
            while v >= b - epsilon:
                out.append(v)
                v = v + step
        return out
    return [_coerce(v) for v in s.split(",") if v.strip()]


def parse_params_spec(spec: str | None) -> dict[str, list[Any]]:
    """Parse ``"k1=v1,v2;k2=a:b:s"`` into ``{"k1": [v1, v2], "k2": [...]}``."""
    if not spec:
        return {}
    out: dict[str, list[Any]] = {}
    for clause in spec.split(";"):
        clause = clause.strip()
        if not clause:
            continue
        if "=" not in clause:
            raise ValueError(f"Param clause missing '=': {clause!r}")
        key, _, values = clause.partition("=")
        out[key.strip()] = _expand_values(values.strip())
    return out


def cartesian_grid(spec: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Expand ``{"k1": [a, b], "k2": [c]}`` into ``[{"k1": a, "k2": c}, {"k1": b, "k2": c}]``."""
    if not spec:
        return [{}]
    keys = list(spec.keys())
    return [dict(zip(keys, combo, strict=True)) for combo in itertools.product(*spec.values())]


# --------------------------------------------------------------------- #
# Per-video fan-out driver
# --------------------------------------------------------------------- #


def _run_chunk(
    source_path: Path,
    backend: str,
    detector_cls: type,
    chunk: list[dict[str, Any]],
) -> list[tuple[list[int], float]]:
    """Drive one decode of ``source_path`` and fan out to ``len(chunk)`` parallel detectors.

    Returns one ``(cuts, elapsed)`` pair per chunk entry. ``elapsed`` is wall-clock per
    worker thread and is bound by the slowest detector in the chunk, so it is only a
    rough indicator of relative cost.
    """
    source = open_video(source_path, backend=backend)
    fan = FanOutVideoStream(source, n=len(chunk))
    fan.start()
    results: list[tuple[list[int], float]] = [([], 0.0) for _ in chunk]
    errors: list[BaseException | None] = [None] * len(chunk)

    def worker(i: int, params: dict[str, Any]) -> None:
        try:
            stream = fan.stream(i)
            detector = detector_cls(**params)
            sm = SceneManager()
            sm.add_detector(detector)
            t0 = time.time()
            sm.detect_scenes(video=stream)
            elapsed = time.time() - t0
            cuts = [scene[1].frame_num for scene in sm.get_scene_list()]
            results[i] = (cuts, elapsed)
        except BaseException as exc:
            errors[i] = exc
            fan.abort()

    threads = [threading.Thread(target=worker, args=(i, p)) for i, p in enumerate(chunk)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        fan.close()

    first_err = next((e for e in errors if e is not None), None)
    if first_err is not None:
        raise first_err
    return results


def _chunked(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def run_sweep(
    dataset: Dataset,
    detector_name: str,
    backend: str,
    grid: list[dict[str, Any]],
    workers: int,
) -> list[dict[Path, Prediction]]:
    """For each cell in ``grid``, return a ``{video_path: Prediction}`` mapping suitable
    for :func:`benchmark.evaluator.evaluate`. Cells are evaluated in chunks of
    ``workers`` parallel detectors per video decode."""
    detector_cls = DETECTORS[detector_name]
    # predictions_by_cell[cell_index][video_path] = Prediction
    predictions_by_cell: list[dict[Path, Prediction]] = [{} for _ in grid]
    pbar = tqdm(dataset, desc=f"sweep[{detector_name}]")
    for sample in pbar:
        for chunk_indices in _chunked(list(range(len(grid))), workers):
            chunk = [grid[i] for i in chunk_indices]
            outputs = _run_chunk(sample.video_file, backend, detector_cls, chunk)
            for cell_i, (cuts, elapsed) in zip(chunk_indices, outputs, strict=True):
                predictions_by_cell[cell_i][sample.video_file] = Prediction(
                    predicted_cuts=cuts,
                    ground_truth=sample.ground_truth,
                    elapsed=elapsed,
                )
    return predictions_by_cell


# --------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------- #


def _params_str(params: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(params.items()))


def _f1_for(result: BenchmarkResult) -> float:
    return result.hard_cuts.f1


def _print_top_n(
    label: str,
    cells: list[tuple[dict[str, Any], BenchmarkResult]],
    n: int = 10,
) -> None:
    ranked = sorted(cells, key=lambda c: _f1_for(c[1]), reverse=True)[:n]
    rows = []
    for params, result in ranked:
        hard = result.hard_cuts
        rows.append(
            [
                f"{hard.f1 * 100:.2f}",
                f"{hard.precision * 100:.2f}",
                f"{hard.recall * 100:.2f}",
                _params_str(params),
            ]
        )
    if not rows:
        return
    print(f"\n## {label} (top {min(n, len(ranked))})\n")
    print(render_table(["F1", "Precision", "Recall", "Params"], rows))


def _pareto_front(
    cells_at_tols: dict[int, list[tuple[dict[str, Any], BenchmarkResult]]],
) -> list[tuple[dict[str, Any], dict[int, float]]]:
    """Return cells that are not dominated by any other cell across the given tolerances.

    Domination: cell A dominates B if F1@tol(A) >= F1@tol(B) for every tol and strictly
    greater on at least one. Identical (P, R) cells coexist on the frontier.
    """
    tols = sorted(cells_at_tols.keys())
    if not tols:
        return []
    n_cells = len(cells_at_tols[tols[0]])
    # Build a parallel array of (params, {tol: f1}) entries.
    table: list[tuple[dict[str, Any], dict[int, float]]] = []
    for i in range(n_cells):
        params = cells_at_tols[tols[0]][i][0]
        f1s = {t: _f1_for(cells_at_tols[t][i][1]) for t in tols}
        table.append((params, f1s))
    frontier: list[tuple[dict[str, Any], dict[int, float]]] = []
    for i, (pi, fi) in enumerate(table):
        dominated = False
        for j, (_, fj) in enumerate(table):
            if i == j:
                continue
            if all(fj[t] >= fi[t] for t in tols) and any(fj[t] > fi[t] for t in tols):
                dominated = True
                break
        if not dominated:
            frontier.append((pi, fi))
    return frontier


def _print_pareto(
    cells_at_tols: dict[int, list[tuple[dict[str, Any], BenchmarkResult]]],
) -> None:
    frontier = _pareto_front(cells_at_tols)
    if len(frontier) <= 1:
        return
    tols = sorted(cells_at_tols.keys())
    header = [*(f"F1@{t}" for t in tols), "Params"]
    rows = [
        [*(f"{f1s[t] * 100:.2f}" for t in tols), _params_str(params)]
        for params, f1s in sorted(frontier, key=lambda x: -x[1][tols[0]])
    ]
    print(f"\n## Pareto frontier ({len(rows)} cells)\n")
    print(render_table(header, rows))


# --------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------- #


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sweep detector parameters on a benchmark dataset."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=list(DATASETS.keys()),
        help=f"Dataset name. One of: {', '.join(DATASETS.keys())}.",
    )
    parser.add_argument(
        "--detector",
        type=str,
        required=True,
        choices=list(DETECTORS.keys()),
        help=f"Detector name. One of: {', '.join(DETECTORS.keys())}.",
    )
    parser.add_argument(
        "--params",
        type=str,
        default="",
        help=(
            "Parameter spec. Clauses separated by ';'. Each clause is either "
            "'key=v1,v2,...' (enumerated values) or 'key=start:stop:step' (numeric range, "
            "inclusive of stop when it lands on a step). Omitted keys use the detector's "
            "default. For time-valued kwargs like 'min_scene_len', use floats (seconds) "
            "so the sweep is framerate-independent, e.g. "
            "'threshold=15:35:1;min_scene_len=0.0:1.0:0.1'."
        ),
    )
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=None,
        help="Base directory containing per-dataset subfolders. Defaults to 'benchmark'.",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default=DEFAULT_BACKEND,
        choices=sorted(AVAILABLE_BACKENDS.keys()),
        help=f"Video decoding backend (default: {DEFAULT_BACKEND}).",
    )
    parser.add_argument(
        "--tolerance",
        type=str,
        default="0,1",
        help="Comma-separated frame tolerances (default: 0,1).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help=(
            "Number of detector instances to drive in parallel from a single video decode "
            "(default: 8). Cells beyond --workers are processed in subsequent chunks, each "
            "re-decoding the source video. Memory grows with --workers * prefetch frames."
        ),
    )
    parser.add_argument(
        "--quick",
        type=int,
        nargs="?",
        const=10,
        default=None,
        metavar="N",
        help="Score only the first N samples for fast iteration.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Path to write a machine-readable JSON sweep file (one entry per cell).",
    )
    return parser


def main() -> None:
    args = create_parser().parse_args()
    tolerances = parse_tolerances(args.tolerance)
    if not tolerances:
        raise SystemExit("--tolerance must yield at least one value.")
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1.")

    spec = parse_params_spec(args.params)
    grid = cartesian_grid(spec)
    if not grid:
        raise SystemExit("Empty parameter grid.")

    dataset = resolve_dataset(args.dataset, args.dataset_root)
    if len(dataset) == 0:
        raise SystemExit(
            f"Dataset {args.dataset!r} at {args.dataset_root or 'benchmark'} is empty - "
            "check that videos and annotations are present."
        )
    if args.quick is not None:
        dataset._samples = dataset._samples[: args.quick]
        print(f"--quick: limited to first {len(dataset)} samples")

    print(
        f"Sweeping {args.detector} on {args.dataset}: "
        f"{len(grid)} cells x {len(dataset)} videos "
        f"(backend={args.backend}, workers={args.workers})"
    )

    predictions_by_cell = run_sweep(dataset, args.detector, args.backend, grid, args.workers)

    # Score every cell at every tolerance.
    cells_at_tols: dict[int, list[tuple[dict[str, Any], BenchmarkResult]]] = {
        t: [
            (params, evaluate(preds, tolerance=t))
            for params, preds in zip(grid, predictions_by_cell, strict=True)
        ]
        for t in tolerances
    }

    for t in tolerances:
        _print_top_n(f"Best by F1 @ tolerance={t}", cells_at_tols[t])
    if len(tolerances) >= 2:
        _print_pareto(cells_at_tols)

    if args.out:
        payload = {
            "detector": args.detector,
            "dataset": args.dataset,
            "backend": args.backend,
            "workers": args.workers,
            "spec": args.params,
            "cells": [
                {
                    "params": params,
                    "results": {str(t): cells_at_tols[t][i][1].to_dict() for t in tolerances},
                }
                for i, params in enumerate(grid)
            ],
        }
        write_json(args.out, payload)


if __name__ == "__main__":
    main()
