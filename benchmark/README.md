# Benchmarking PySceneDetect

Benchmarks PySceneDetect's detection accuracy and latency against public shot-boundary-detection
corpora. Scoring follows the [TRECVID-SBD][trecvid] convention (greedy 1-to-1 nearest-neighbor
matching with a configurable frame tolerance for hard cuts; point-in-interval matching for fade
transitions; mean absolute frame offset on matched events) so numbers are comparable to published
SBD results.

[trecvid]: https://www-nlpir.nist.gov/projects/tv2007/pastdata/shot_boundary.07.html

Supported datasets:

- [BBC Planet Earth](https://zenodo.org/records/14865504):
  11 long-form broadcast clips; hard cuts only
- [AutoShot](https://drive.google.com/file/d/17diRkLlNUUjHDooXdqFUTXYje2-x4Yt6/view?usp=sharing):
  Short-form web clips; hard cuts only

## Usage

```bash
# Single detector x single dataset:
python -m benchmark --detector detect-content --dataset BBC
```

Pass `--help` for `--dataset-root`, `--backend`, `--tolerance`, and `--out` options.

## Dataset Download

### BBC

```bash
# annotations
wget -O BBC/fixed.zip https://zenodo.org/records/14873790/files/fixed.zip
unzip BBC/fixed.zip -d BBC
rm -rf BBC/fixed.zip

# videos
wget -O BBC/videos.zip https://zenodo.org/records/14873790/files/videos.zip
unzip BBC/videos.zip -d BBC
rm -rf BBC/videos.zip
```

### AutoShot

Download `AutoShot_test.tar.gz` from
[Google Drive](https://drive.google.com/file/d/17diRkLlNUUjHDooXdqFUTXYje2-x4Yt6/view?usp=sharing).

```bash
tar -zxvf AutoShot_test.tar.gz
rm AutoShot_test.tar.gz
```

Set `--dataset-root /path/to/datasets` to override. The default dataset location assumes they are
all placed in the benchmark folder (e.g. `benchmark/BBC`, `benchmark/AutoShot`).

## Results (defaults)

*NOTE*: These results were generated before the new scoring methodology was implemented and will be
updated as soon as possible. The precision and recall scores are still relevant, just the evaluation
strategy is being expanded to allow for more dataset coverage and also tuning of parameters.

#### BBC

|      Detector     | Recall | Precision |   F1  | Elapsed time (second) |
|:-----------------:|:------:|:---------:|:-----:|:---------------------:|
|  AdaptiveDetector |  87.12 |   96.55   | 91.59 |         27.84         |
|  ContentDetector  |  84.70 |   88.77   | 86.69 |         28.20         |
|    HashDetector   |  92.30 |   75.56   | 83.10 |         16.00         |
| HistogramDetector |  89.84 |   72.03   | 79.96 |         15.13         |
| ThresholdDetector |   0.00 |    0.00   |  0.00 |         18.95         |

#### AutoShot

|      Detector     | Recall | Precision |   F1  | Elapsed time (second) |
|:-----------------:|:------:|:---------:|:-----:|:---------------------:|
|  AdaptiveDetector |  70.77 |   77.65   | 74.05 |          1.23         |
|  ContentDetector  |  63.67 |   76.40   | 69.46 |          1.21         |
|    HashDetector   |  56.66 |   76.35   | 65.05 |          1.16         |
| HistogramDetector |  63.36 |   53.34   | 57.92 |          1.23         |
| ThresholdDetector |   0.75 |   38.64   |  1.47 |          1.24         |

## Citations

### BBC

```
@InProceedings{bbc_dataset,
  author    = {Lorenzo Baraldi and Costantino Grana and Rita Cucchiara},
  title     = {A Deep Siamese Network for Scene Detection in Broadcast Videos},
  booktitle = {Proceedings of the 23rd ACM International Conference on Multimedia},
  year      = {2015},
}
```

### AutoShot

```
@InProceedings{autoshot_dataset,
  author    = {Wentao Zhu and Yufang Huang and Xiufeng Xie and Wenxian Liu and Jincan Deng and Debing Zhang and Zhangyang Wang and Ji Liu},
  title     = {AutoShot: A Short Video Dataset and State-of-the-Art Shot Boundary Detection},
  booktitle = {Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR) Workshops},
  year      = {2023},
}
```
