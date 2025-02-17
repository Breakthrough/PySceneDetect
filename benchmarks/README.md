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

### Evaluation
To evaluate PySceneDetect on a dataset, run the following command:
```
python benchmark.py -d <dataset_name> --detector <detector_name>
```
For example, to evaluate ContentDetector on the BBC dataset:
```
python evaluate.py -d BBC --detector detect-content
```

### Result
The performance is computed as recall, precision, f1, and elapsed time.
The following results indicate that ContentDetector achieves the highest performance on the BBC dataset.

|      Detector     | Recall | Precision |   F1  | Elapsed time (second) |
|:-----------------:|:------:|:---------:|:-----:|:---------------------:|
|  AdaptiveDetector |  87.52 |   97.21   | 92.11 |         27.84         |
|  ContentDetector  |  85.23 |   89.53   | 87.33 |         26.46         |
|    HashDetector   |  92.96 |   76.27   | 83.79 |         16.26         |
| HistogramDetector |  90.55 |   72.76   | 80.68 |         16.13         |
| ThresholdDetector |  0.00  |   0.00    |  0.00 |         18.95         |

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