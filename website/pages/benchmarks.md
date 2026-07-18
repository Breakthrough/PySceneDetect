
# Benchmarks

PySceneDetect's detectors are benchmarked for accuracy against public
shot-boundary-detection corpora. Scoring follows the
[TRECVID-SBD convention](https://www-nlpir.nist.gov/projects/tv2007/pastdata/shot_boundary.07.html)
(greedy 1-to-1 nearest-neighbor matching with a configurable frame tolerance for hard cuts;
point-in-interval matching for fades), so numbers are comparable to published results.
The benchmark harness, datasets, and full raw results live in
[`benchmark/`](https://github.com/Breakthrough/PySceneDetect/tree/main/benchmark) on GitHub.

Three datasets are used, chosen to cover very different content:

 - **BBC Planet Earth** - 11 long-form broadcast episodes (hard cuts only)
 - **AutoShot** - short-form web/user-generated clips (hard cuts only)
 - **ClipShots** - 500 short web clips with hard cuts *and* typed gradual transitions

## Accuracy at default settings

<img src="../img/benchmark-f1-defaults.svg" alt="Grouped bar chart of hard-cut F1 score per detector and dataset at default settings. AdaptiveDetector leads on BBC (92) and AutoShot (74); HistogramDetector trails, dropping to 20 on ClipShots." style="max-width:100%;">

Hard cuts, strict frame-exact matching (tolerance 0). F1 cells are shaded by score.

### BBC Planet Earth

<table class="bm-table">
<tr><th>Detector</th><th>Recall</th><th>Precision</th><th>F1</th></tr>
<tr><td>AdaptiveDetector</td><td>87.12</td><td>96.55</td><td class="bm-t1">91.59</td></tr>
<tr><td>ContentDetector</td><td>84.70</td><td>88.77</td><td class="bm-t1">86.69</td></tr>
<tr><td>HashDetector</td><td>92.30</td><td>75.56</td><td class="bm-t1">83.10</td></tr>
<tr><td>HistogramDetector</td><td>89.84</td><td>72.03</td><td class="bm-t2">79.96</td></tr>
<tr><td>ThresholdDetector&nbsp;*</td><td>0.06</td><td>0.70</td><td>0.11</td></tr>
</table>

### AutoShot

<table class="bm-table">
<tr><th>Detector</th><th>Recall</th><th>Precision</th><th>F1</th></tr>
<tr><td>AdaptiveDetector</td><td>70.59</td><td>77.46</td><td class="bm-t2">73.86</td></tr>
<tr><td>ContentDetector</td><td>63.49</td><td>76.19</td><td class="bm-t2">69.26</td></tr>
<tr><td>HashDetector</td><td>56.48</td><td>76.11</td><td class="bm-t2">64.84</td></tr>
<tr><td>HistogramDetector</td><td>63.27</td><td>53.23</td><td class="bm-t3">57.82</td></tr>
<tr><td>ThresholdDetector&nbsp;*</td><td>0.75</td><td>38.64</td><td>1.47</td></tr>
</table>

### ClipShots (hard cuts)

<table class="bm-table">
<tr><th>Detector</th><th>Recall</th><th>Precision</th><th>F1</th></tr>
<tr><td>AdaptiveDetector</td><td>85.97</td><td>41.25</td><td class="bm-t3">55.75</td></tr>
<tr><td>ContentDetector</td><td>81.93</td><td>42.36</td><td class="bm-t3">55.84</td></tr>
<tr><td>HashDetector</td><td>81.34</td><td>30.14</td><td class="bm-t3">43.98</td></tr>
<tr><td>HistogramDetector</td><td>72.20</td><td>11.47</td><td>19.80</td></tr>
<tr><td>ThresholdDetector&nbsp;*</td><td>0.08</td><td>0.58</td><td>0.14</td></tr>
</table>

### ClipShots (fades)

<table class="bm-table">
<tr><th>Detector</th><th>Recall</th><th>Precision</th><th>F1</th></tr>
<tr><td>AdaptiveDetector</td><td>13.65</td><td>98.12</td><td>23.96</td></tr>
<tr><td>ContentDetector</td><td>26.03</td><td>98.04</td><td class="bm-t3">41.14</td></tr>
<tr><td>HashDetector</td><td>18.77</td><td>94.53</td><td>31.33</td></tr>
<tr><td>HistogramDetector</td><td>69.67</td><td>81.99</td><td class="bm-t2">75.33</td></tr>
<tr><td>ThresholdDetector&nbsp;*</td><td>5.69</td><td>99.24</td><td>10.77</td></tr>
</table>

\* ThresholdDetector detects fades to/from black, not shot-to-shot transitions; near-zero
hard-cut scores are expected. Included for completeness.

## Parameter sweeps

Beyond the default values, a sweep over each detector's key parameters shows how
accuracy per dataset changes:

<img src="../img/benchmark-sweep-curves.svg" alt="Four small-multiple line charts showing hard-cut F1 at 1-frame tolerance versus threshold for detect-content, detect-adaptive, detect-hash, and detect-hist. Each panel has one line per dataset with a dot at that dataset's optimum; BBC and AutoShot peak at lower thresholds than ClipShots in most panels." style="max-width:100%;">

Dots mark each dataset's optimum within the shown parameter slice. Long-form broadcast content (BBC)
generally prefers lower thresholds than short web clips (ClipShots), so the defaults aim for a
robust middle ground.

<img src="../img/benchmark-f1-optimal.svg" alt="Grouped bar chart of hard-cut F1 at 1-frame tolerance after parameter tuning. Bars show the best single cross-dataset parameter set per detector and dataset, a black tick marks the v0.7 default, and a dot marks each dataset's own optimum. HistogramDetector shows the largest gap between default and tuned scores, most dramatically on ClipShots (20 vs 48); for ContentDetector and AdaptiveDetector on BBC the default tick sits slightly above the tuned bar." style="max-width:100%;">

Scored by mean hard-cut F1 at 1-frame tolerance across all three datasets:

<table class="bm-table">
<tr><th>Detector</th><th>Best mean F1</th><th>Best parameters</th><th>v0.7 default</th></tr>
<tr><td>AdaptiveDetector</td><td class="bm-t2">76.3</td><td>adaptive_threshold=3.5, window_width=3, min_scene_len=0.6s</td><td>adaptive_threshold=3.0, window_width=2</td></tr>
<tr><td>ContentDetector</td><td class="bm-t2">73.4</td><td>threshold=31, min_scene_len=0.6s</td><td>threshold=27</td></tr>
<tr><td>HashDetector</td><td class="bm-t2">69.8</td><td>threshold=0.35, size=8</td><td>threshold=0.395, size=16</td></tr>
<tr><td>HistogramDetector</td><td class="bm-t2">66.3</td><td>threshold=0.20, bins=128</td><td>threshold=0.05, bins=256</td></tr>
</table>

Full per-dataset breakdowns are in
[`benchmark/SWEEP_REPORT.md`](https://github.com/Breakthrough/PySceneDetect/blob/main/benchmark/SWEEP_REPORT.md).

## Benchmarking

See [`benchmark/README.md`](https://github.com/Breakthrough/PySceneDetect/blob/main/benchmark/README.md)
for dataset download instructions and usage.

```bash
# Score one detector on one dataset:
python -m benchmark --detector detect-content --dataset BBC

# Grid sweep over detector parameters:
python -m benchmark.sweep --detector detect-content --dataset BBC \
    --params "threshold=15:35:1;min_scene_len=0.0:1.0:0.1"
```
