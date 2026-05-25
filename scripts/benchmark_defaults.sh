#!/usr/bin/env bash
# Run every detector against every dataset at default kwargs.
# JSON + log per cell are written under benchmark/results/defaults/.
#
# Environment overrides:
#   DATASET_ROOT  Base directory containing per-dataset subfolders (BBC/, AutoShot/, ClipShots/).
#                 Defaults to the in-repo benchmark/ folder; override when datasets live
#                 elsewhere (e.g. DATASET_ROOT=D:/path/to/benchmark scripts/benchmark_defaults.sh).
#   OUT_DIR       Where to write results. Defaults to benchmark/results/defaults.
#   PY            Python interpreter. Defaults to python on PATH.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATASET_ROOT="${DATASET_ROOT:-$REPO_ROOT/benchmark}"
OUT_DIR="${OUT_DIR:-$REPO_ROOT/benchmark/results/defaults}"
PY="${PY:-python}"

DETECTORS=(detect-adaptive detect-content detect-hash detect-hist detect-threshold)
DATASETS=(BBC AutoShot ClipShots)

mkdir -p "$OUT_DIR"
for det in "${DETECTORS[@]}"; do
  for ds in "${DATASETS[@]}"; do
    "$PY" -m benchmark --detector "$det" --dataset "$ds" \
      --dataset-root "$DATASET_ROOT" --tolerance 0,1 \
      --out "$OUT_DIR/$det-$ds.json" | tee "$OUT_DIR/$det-$ds.log"
  done
done
