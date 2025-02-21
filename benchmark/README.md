# Benchmarking PySceneDetect
This repository benchmarks the performance of PySceneDetect in terms of both latency and accuracy.
We evaluate it using the standard dataset for video shot detection: [BBC](https://zenodo.org/records/14865504).

## Dataset Download
### BBC
```
# annotation
wget -O BBC/fixed.zip https://zenodo.org/records/14873790/files/fixed.zip
unzip BBC/fixed.zip -d BBC
rm -rf BBC/fixed.zip

# videos
wget -O BBC/videos.zip https://zenodo.org/records/14873790/files/videos.zip
unzip BBC/videos.zip -d BBC
rm -rf BBC/videos.zip
```

### AutoShot
Download `AutoShot_test.tar.gz` from [Google drive](https://drive.google.com/file/d/17diRkLlNUUjHDooXdqFUTXYje2-x4Yt6/view?usp=sharing).
```
tar -zxvf AutoShot.tar.gz
rm AutoShot.tar.gz
```

## Evaluation
To evaluate PySceneDetect on a dataset, run the following command from the root of the repo:
```
python -m benchmark -d <dataset_name> --detector <detector_name>
```
For example, to evaluate ContentDetector on the BBC dataset:
```
python -m benchmark -d BBC --detector detect-content
```

### Result
The performance is computed as recall, precision, f1, and elapsed time.

#### BBC

|      Detector     | Recall | Precision |   F1  | Elapsed time (second) |
|:-----------------:|:------:|:---------:|:-----:|:---------------------:|
|  AdaptiveDetector |  87.12 |   96.55   | 91.59 |         27.84         |
|  ContentDetector  |  84.70 |   88.77   | 86.69 |         28.20         |
|    HashDetector   |  92.30 |   75.56   | 83.10 |         16.00         |
| HistogramDetector |  89.84 |   72.03   | 79.96 |         15.13         |
| ThresholdDetector |  0.00  |   0.00    |  0.00 |         18.95         |

#### AutoShot

|      Detector     | Recall | Precision |   F1  | Elapsed time (second) |
|:-----------------:|:------:|:---------:|:-----:|:---------------------:|
|  AdaptiveDetector |  70.77 |   77.65   | 74.05 |          1.23         |
|  ContentDetector  |  63.67 |   76.40   | 69.46 |          1.21         |
|    HashDetector   |  56.66 |   76.35   | 65.05 |          1.16         |
| HistogramDetector |  63.36 |   53.34   | 57.92 |          1.23         |
| ThresholdDetector |  0.75  |   38.64   |  1.47 |          1.24         |

## Citation
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
