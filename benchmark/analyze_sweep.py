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
"""Derive default-parameter recommendations from sweep results.

Applies a fixed decision procedure to the grid JSONs under ``benchmark/results/sweep/``
rather than just taking the argmax of mean F1@1:

1. Baseline the shipped default (nearest grid cell).
2. Candidate set: cells within ``EPSILON`` of the best mean F1@1 (the plateau, not the peak).
3. Neighborhood robustness: reject cells with a steep drop to any one-grid-step neighbor
   along a fine-grained numeric axis (categorical axes like ``size``/``bins`` are not
   "steps" and are excluded).
4. Weighting sensitivity: a candidate must beat the default under the equal-dataset mean
   and under every leave-one-dataset-out mean -- i.e. the *improvement* survives removing
   any single dataset. (Being within EPSILON of each scheme's argmax is hopeless when
   per-dataset optima diverge, and is not the question a defaults change asks.) The pooled
   micro-average is reported for context but is not a gate: pooling events lets the
   largest corpus (ClipShots, ~10x the cuts) dominate, making it a dataset-weighting
   choice rather than a robustness check.
5. Precision floor: per dataset, candidate precision@1 must not fall more than
   ``PRECISION_SLACK`` below the default's.
6. Materiality: recommend a change only for >= ``MIN_GAIN`` mean F1@1 over the default,
   gains >= 1.0 on at least two datasets, and no dataset regressing by > 1.0.
7. min_scene_len isolation: for detectors that swept it, also rank with it fixed at the
   default-equivalent slice so the threshold recommendation stands on its own.

Prints a markdown report to stdout. Requires the sweep JSONs locally (not committed);
see ``scripts/benchmark_sweep.sh``.
"""

from __future__ import annotations

from benchmark.report_sweep import DATASETS, _load_cells, _params_str, _table

EPSILON = 1.0  # candidate set: within this many F1 points of the best mean
MAX_NEIGHBOR_DROP = 2.0  # reject cells this much better than their worst neighbor
FINE_AXIS_MIN_VALUES = 4  # axes with fewer distinct values are categorical, not grid steps
PRECISION_SLACK = 5.0  # per-dataset precision@1 may not drop more than this vs default
MIN_GAIN = 2.0  # mean F1@1 gain required to recommend changing a default

# Shipped defaults mapped onto the swept grid (nearest cell). min_scene_len defaults to
# 15 *frames*; the sweeps used seconds, so 0.6 matches only at 25 fps (BBC) and is ~0.5
# at 30 fps web video -- flagged in the report. hash's 0.395 maps to the 0.4 grid point.
DEFAULTS: dict[str, dict] = {
    "detect-content": {"min_scene_len": 0.6, "threshold": 27},
    "detect-adaptive": {"adaptive_threshold": 3.0, "min_scene_len": 0.6, "window_width": 2},
    "detect-hash": {"size": 16, "threshold": 0.4},
    "detect-hist": {"bins": 256, "threshold": 0.05},
}
MSL_SWEPT = {"detect-content", "detect-adaptive"}


def _f1(matched: int, fp: int, missed: int) -> float:
    p = matched / (matched + fp) if matched + fp else 0.0
    r = matched / (matched + missed) if matched + missed else 0.0
    return 200.0 * p * r / (p + r) if p + r else 0.0


class Cell:
    """One parameter combination with per-dataset hard-cut results at tolerance 1."""

    def __init__(self, params: dict, per_ds: dict[str, dict]):
        self.params = params
        self.key = _params_str(params)
        self.per_ds = per_ds  # dataset -> hard_cuts dict (matched/fp/missed/precision/recall/f1)
        self.mean_f1 = sum(d["f1"] for d in per_ds.values()) / len(per_ds)
        self.micro_f1 = _f1(
            sum(d["matched"] for d in per_ds.values()),
            sum(d["false_positives"] for d in per_ds.values()),
            sum(d["missed"] for d in per_ds.values()),
        )

    def lodo(self, skip: str) -> float:
        rest = [d["f1"] for ds, d in self.per_ds.items() if ds != skip]
        return sum(rest) / len(rest)


def _load(det: str) -> list[Cell]:
    per_key: dict[str, dict[str, dict]] = {}
    params_by_key: dict[str, dict] = {}
    for ds in DATASETS:
        cells = _load_cells(det, ds)
        if cells is None:
            return []
        for c in cells:
            key = _params_str(c["params"])
            per_key.setdefault(key, {})[ds] = c["results"]["1"]["aggregate"]["hard_cuts"]
            params_by_key[key] = c["params"]
    return [Cell(params_by_key[k], v) for k, v in per_key.items() if len(v) == len(DATASETS)]


def _neighbors(cell: Cell, cells: list[Cell]) -> list[Cell]:
    """Cells one grid step away along exactly one fine-grained numeric axis.

    Axes with fewer than ``FINE_AXIS_MIN_VALUES`` distinct values (e.g. ``size=8,16``,
    ``bins=128,256``, ``window_width=2,3``) are categorical choices, not grid steps, so
    a large score difference across them is not a knife-edge.
    """
    axes = {k: sorted({c.params[k] for c in cells}) for k in cell.params}
    out = []
    for other in cells:
        diff = [k for k in cell.params if other.params[k] != cell.params[k]]
        if len(diff) != 1:
            continue
        (k,) = diff
        vals = axes[k]
        if len(vals) < FINE_AXIS_MIN_VALUES:
            continue
        if abs(vals.index(other.params[k]) - vals.index(cell.params[k])) == 1:
            out.append(other)
    return out


def analyze(det: str) -> list[str]:
    cells = _load(det)
    out = [f"## {det}\n"]
    if not cells:
        return [*out, "(sweep JSONs missing)\n"]

    # Match by the canonical params string: grid generation leaves float artifacts
    # (e.g. 0.4000000000000001) that a plain dict comparison would miss.
    default_key = _params_str(DEFAULTS[det])
    default = next((c for c in cells if c.key == default_key), None)
    best = max(cells, key=lambda c: c.mean_f1)

    def row(c: Cell, label: str) -> list[str]:
        return [
            label,
            f"{c.mean_f1:.2f}",
            *(f"{c.per_ds[ds]['f1']:.2f}" for ds in DATASETS),
            c.key,
        ]

    rows = [row(best, "best")]
    if default is not None:
        rows.insert(0, row(default, "default"))
    out.append(_table(["Cell", "Mean F1@1", *DATASETS, "Params"], rows))
    out.append("")
    if default is None:
        out.append(f"> Default cell {DEFAULTS[det]} not present in the grid; criteria that")
        out.append("> compare against the default are skipped below.\n")

    # Gated weighting schemes: equal-dataset mean + leave-one-dataset-out means. A
    # candidate is weighting-stable if it beats the default under every scheme, i.e. the
    # improvement does not hinge on any single dataset. Micro-average is reported per
    # candidate but deliberately not gated (see module docstring). Without a default cell
    # to compare against, fall back to within-EPSILON-of-best per scheme.
    schemes = [lambda c: c.mean_f1]
    schemes += [lambda c, ds=ds: c.lodo(ds) for ds in DATASETS]
    scheme_floor = (
        [s(default) for s in schemes]
        if default is not None
        else [max(s(c) for c in cells) - EPSILON for s in schemes]
    )

    candidates = sorted(
        (c for c in cells if c.mean_f1 >= best.mean_f1 - EPSILON),
        key=lambda c: c.mean_f1,
        reverse=True,
    )
    cand_rows = []
    passing = []
    for c in candidates:
        nbrs = _neighbors(c, cells)
        worst_drop = max((c.mean_f1 - n.mean_f1 for n in nbrs), default=0.0)
        robust = worst_drop <= MAX_NEIGHBOR_DROP
        stable = all(s(c) >= floor for s, floor in zip(schemes, scheme_floor, strict=True))
        if default is not None:
            prec_ok = all(
                c.per_ds[ds]["precision"] >= default.per_ds[ds]["precision"] - PRECISION_SLACK
                for ds in DATASETS
            )
            deltas = [c.per_ds[ds]["f1"] - default.per_ds[ds]["f1"] for ds in DATASETS]
            material = (
                c.mean_f1 - default.mean_f1 >= MIN_GAIN
                and sum(d >= 1.0 for d in deltas) >= 2
                and all(d >= -1.0 for d in deltas)
            )
        else:
            prec_ok = material = True
        ok = robust and stable and prec_ok and material
        if ok:
            passing.append(c)
        mark = lambda b: "yes" if b else "NO"  # noqa: E731
        cand_rows.append(
            [
                f"{c.mean_f1:.2f}",
                f"{c.micro_f1:.2f}",
                f"{worst_drop:.2f}",
                mark(robust),
                mark(stable),
                mark(prec_ok),
                mark(material),
                "PASS" if ok else "-",
                c.key,
            ]
        )
    out.append(f"**Candidates (mean F1@1 within {EPSILON:g} of best):**\n")
    out.append(
        _table(
            [
                "Mean",
                "Micro",
                "NbrDrop",
                "Robust",
                "WeightStable",
                "PrecFloor",
                "Material",
                "Verdict",
                "Params",
            ],
            cand_rows,
        )
    )
    out.append("")

    if det in MSL_SWEPT:
        msl = DEFAULTS[det]["min_scene_len"]
        fixed = [c for c in cells if c.params.get("min_scene_len") == msl]
        top = sorted(fixed, key=lambda c: c.mean_f1, reverse=True)[:3]
        out.append(f"**With min_scene_len fixed at the default-equivalent {msl:g}s:**\n")
        out.append(
            _table(
                ["Mean F1@1", *DATASETS, "Params"],
                [
                    [f"{c.mean_f1:.2f}", *(f"{c.per_ds[ds]['f1']:.2f}" for ds in DATASETS), c.key]
                    for c in top
                ],
            )
        )
        out.append("")

    if passing:
        pick = passing[0]
        gain = f" (+{pick.mean_f1 - default.mean_f1:.2f} mean F1@1 vs default)" if default else ""
        out.append(f"**Recommendation: CHANGE to `{pick.key}`{gain}.**\n")
    else:
        out.append(
            "**Recommendation: KEEP current default** (no candidate passes all criteria; "
            "see verdict column for which gate fails).\n"
        )
    return out


def main() -> None:
    print("# Detector default recommendations from sweep data\n")
    print(
        "Generated by `benchmark/analyze_sweep.py`. Criteria: candidate plateau within "
        f"{EPSILON:g} F1 of best; worst one-step neighbor drop <= {MAX_NEIGHBOR_DROP:g} along "
        "fine-grained axes; beats the default under equal-mean and each leave-one-dataset-out "
        "weighting (pooled micro-average reported, not gated); "
        f"per-dataset precision floor (default - "
        f"{PRECISION_SLACK:g}); materiality (>= {MIN_GAIN:g} mean F1@1 gain, >= 1.0 on two "
        "datasets, no dataset worse by > 1.0). min_scene_len defaults to 15 frames (= 0.6s "
        "only at 25 fps); the default cell uses the nearest swept slice.\n"
    )
    for det in DEFAULTS:
        for line in analyze(det):
            print(line)


if __name__ == "__main__":
    main()
