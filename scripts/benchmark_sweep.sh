#!/usr/bin/env bash
# Overnight parameter sweep across detectors x datasets.
# JSON + log per cell are written under benchmark/results/sweep/.
#
# Grids are sized to fit comfortably in ~8-10 hours on a reasonably fast machine
# with --workers=16. Tune DETECTORS / DATASETS / WORKERS via env to subset.
# A failed (det, ds) pair logs a warning and continues; check the final summary.
#
# Environment overrides:
#   DATASET_ROOT  Base directory containing per-dataset subfolders (BBC/, AutoShot/, ClipShots/).
#                 Defaults to the in-repo benchmark/ folder.
#   OUT_DIR       Where to write results. Defaults to benchmark/results/sweep.
#   WORKERS       Parallel detectors per video decode (default: 16). Memory ~= workers * 24MB.
#   QUICK         If set to N, limits each dataset to first N samples (smoke-test override).
#   PY            Python interpreter. Defaults to python on PATH.
#   DETECTORS     Space-separated subset; defaults to all five sweep-supported detectors.
#   DATASETS      Space-separated subset; defaults to BBC AutoShot ClipShots.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATASET_ROOT="${DATASET_ROOT:-$REPO_ROOT/benchmark}"
OUT_DIR="${OUT_DIR:-$REPO_ROOT/benchmark/results/sweep}"
WORKERS="${WORKERS:-16}"
PY="${PY:-python}"
DETECTORS="${DETECTORS:-detect-content detect-adaptive detect-hash detect-hist}"
DATASETS="${DATASETS:-BBC AutoShot ClipShots}"

QUICK_FLAG=""
if [[ -n "${QUICK:-}" ]]; then
  QUICK_FLAG="--quick $QUICK"
fi

# Per-detector grid. Hits the most impactful axes per detector at a coarse enough
# step to fit in an overnight run. Use the per-detector outputs to design a finer
# follow-up sweep around the winning cell.
grid_for() {
  case "$1" in
    detect-content)
      echo "threshold=15:35:2;min_scene_len=0.0,0.2,0.4,0.6,0.8"
      ;;
    detect-adaptive)
      echo "adaptive_threshold=1.5:6.0:0.5;min_scene_len=0.4,0.6;window_width=2,3"
      ;;
    detect-hash)
      echo "threshold=0.25:0.55:0.025;size=8,16"
      ;;
    detect-hist)
      echo "threshold=0.02:0.35:0.01;bins=128,256"
      ;;
    *)
      echo ""
      ;;
  esac
}

mkdir -p "$OUT_DIR"
# SUMMARY_LOG lets several concurrent (detector-parallel) runs keep separate
# summaries while sharing OUT_DIR for the per-pair JSON outputs.
SUMMARY="${SUMMARY_LOG:-$OUT_DIR/_summary.log}"
echo "Sweep started: $(date -Iseconds)" | tee -a "$SUMMARY"
echo "DATASET_ROOT=$DATASET_ROOT" | tee -a "$SUMMARY"
echo "WORKERS=$WORKERS" | tee -a "$SUMMARY"
echo | tee -a "$SUMMARY"

for det in $DETECTORS; do
  spec="$(grid_for "$det")"
  if [[ -z "$spec" ]]; then
    echo "SKIP $det -- no grid defined" | tee -a "$SUMMARY"
    continue
  fi
  for ds in $DATASETS; do
    out_json="$OUT_DIR/$det-$ds.json"
    log_file="$OUT_DIR/$det-$ds.log"
    if [[ -s "$out_json" ]]; then
      echo "SKIP $det on $ds -- $out_json already exists" | tee -a "$SUMMARY"
      continue
    fi
    started="$(date +%s)"
    echo "RUN  $det on $ds [$spec]" | tee -a "$SUMMARY"
    if "$PY" -m benchmark.sweep \
        --detector "$det" --dataset "$ds" \
        --dataset-root "$DATASET_ROOT" \
        --params "$spec" \
        --tolerance 0,1 \
        --workers "$WORKERS" \
        $QUICK_FLAG \
        --out "$out_json" 2>&1 | tee "$log_file"; then
      elapsed=$(( $(date +%s) - started ))
      echo "OK   $det on $ds in ${elapsed}s" | tee -a "$SUMMARY"
    else
      elapsed=$(( $(date +%s) - started ))
      echo "FAIL $det on $ds after ${elapsed}s (see $log_file)" | tee -a "$SUMMARY"
    fi
  done
done

echo | tee -a "$SUMMARY"
echo "Sweep complete: $(date -Iseconds)" | tee -a "$SUMMARY"
