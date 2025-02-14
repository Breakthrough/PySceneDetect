# Benchmarking PySceneDetect
This repository benchmarks the performance of PySceneDetect in terms of both latency and accuracy.
We evaluate it using two standard datasets for video shot detection: [RAI](https://zenodo.org/records/14865179) and [BBC](https://zenodo.org/records/14865504).

## Dataset Download
### RAI Dataset
```
wget -O RAI/dataset.zip https://zenodo.org/api/records/14865179/files-archive
unzip RAI/dataset.zip -d RAI
rm -rf RAI/dataset.zip
```

### BBC
```
wget -O BBC/dataset.zip https://zenodo.org/api/records/14865504/files-archive
unzip BBC/dataset.zip -d BBC
rm -rf BBC/dataset.zip
```

### Evaluation
To evaluate PySceneDetect on a dataset, run the following command:
```
python evaluate.py -d <dataset_name>
```
For example, to evaluate it on the RAI dataset:
```
python evaluate.py -d RAI
```

### Result
- Results will be updated soon.
- Planned metrics: Recall, Precision, F1-score, and processing time.

## Citation
### RAI
```
@InProceedings{rai_dataset,
  author    = {Lorenzo Baraldi and Costantino Grana and Rita Cucchiara},
  title     = {Shot and scene detection via hierarchical clustering for re-using broadcast video},
  booktitle = {Proceedings of International Conference on Computer Analysis of Images and Patterns},
  year      = {2015},
}
```

### BBC
```
@InProceedings{bbc_dataset,
  author    = {Lorenzo Baraldi and Costantino Grana and Rita Cucchiara},
  title     = {A Deep Siamese Network for Scene Detection in Broadcast Videos},
  booktitle = {Proceedings of the 23rd ACM International Conference on Multimedia},
  year      = {2015},
}
```