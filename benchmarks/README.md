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
|  AdaptiveDetector |  7.80  |   96.18   | 14.44 |         25.75         |
|  ContentDetector  |  84.52 |   88.77   | 86.59 |         25.50         |
|    HashDetector   |  8.57  |   80.27   | 15.48 |         23.78         |
| HistogramDetector |  8.22  |   70.82   | 14.72 |         18.60         |
| ThresholdDetector |  0.00  |    0.00   |  0.00 |         18.95         |

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