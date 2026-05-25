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
"""Benchmark dataset definitions and registry.

Each :class:`Dataset` is a corpus of :class:`Sample` records (video file + typed ground truth)
loaded eagerly at construction. Ground-truth files for the supported corpora are at most a few
hundred kilobytes total, so eager loading avoids re-reading the same files for every sweep cell.

Add a new dataset by:

1. Subclassing :class:`Dataset` and populating ``self._samples`` in ``__init__``.
2. Registering it in :data:`DATASETS` under the name used by ``--dataset``.
"""

from __future__ import annotations

import glob
import json
import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from benchmark.evaluator import EventInterval, Frames, GroundTruth

logger = logging.getLogger("pyscenedetect")


@dataclass(frozen=True)
class Sample:
    """One scored video: a path on disk plus its typed ground truth."""

    video_file: Path
    ground_truth: GroundTruth


class Dataset:
    """Iterable corpus of :class:`Sample` records.

    Subclasses populate ``self._samples`` in their constructor; this base provides the iteration
    and length protocol. ``event_types`` advertises which TRECVID-SBD event categories the
    dataset's ground truth contains, so consumers can skip columns/tables for categories that
    have no events (e.g. fade transitions on BBC/AutoShot).
    """

    event_types: frozenset[str] = frozenset({"hard_cut"})
    _samples: list[Sample]

    def __iter__(self) -> Iterator[Sample]:
        return iter(self._samples)

    def __len__(self) -> int:
        return len(self._samples)


def _read_tab_separated_cuts(scene_file: str) -> list[Frames]:
    """Parse a BBC/AutoShot-style annotation file.

    Each line is tab-separated; the second column is the 0-based frame index of a
    hard cut. Returns 1-based frame indices, matching the convention used by
    :class:`scenedetect.FrameTimecode`.
    """
    with open(scene_file) as f:
        return [int(line.strip().split("\t")[1]) + 1 for line in f]


class BBCDataset(Dataset):
    """The BBC Planet Earth dataset.

    Baraldi et al., "A Deep Siamese Network for Scene Detection in Broadcast Videos",
    ACM Multimedia 2015. https://arxiv.org/abs/1510.08893

    11 long-form videos (``BBC/videos/bbc_<id>.mp4``) with hard-cut annotations in
    ``BBC/fixed/<id>-scenes.txt``.
    """

    def __init__(self, dataset_dir: str):
        video_files = sorted(glob.glob(os.path.join(dataset_dir, "videos", "*.mp4")))
        scene_files = sorted(glob.glob(os.path.join(dataset_dir, "fixed", "*.txt")))
        if len(video_files) != len(scene_files):
            raise ValueError(
                f"BBC dataset at {dataset_dir!r}: {len(video_files)} videos but "
                f"{len(scene_files)} annotation files."
            )
        self._samples: list[Sample] = []
        for video_file, scene_file in zip(video_files, scene_files, strict=True):
            video_id = os.path.basename(video_file).replace("bbc_", "").split(".")[0]
            scene_id = os.path.basename(scene_file).split("-")[0]
            if video_id != scene_id:
                raise ValueError(f"BBC id mismatch: {video_file} vs {scene_file}")
            self._samples.append(
                Sample(
                    video_file=Path(video_file),
                    ground_truth=GroundTruth(hard_cuts=_read_tab_separated_cuts(scene_file)),
                )
            )


class AutoShotDataset(Dataset):
    """The AutoShot dataset (test splits).

    Zhu et al., "AutoShot: A Short Video Dataset and State-of-the-Art Shot Boundary
    Detection", CVPRW 2023. The original test set has 200 videos; 36 are no longer
    publicly available, so the corpus iterates over whatever is present on disk.

    Videos at ``AutoShot/videos/<id>.mp4``, hard-cut annotations at
    ``AutoShot/annotations/<id>.txt``.
    """

    def __init__(self, dataset_dir: str):
        # 36 of the original 200 videos are no longer publicly available, so intersect
        # by id rather than zipping the directory listings strictly.
        videos_by_id = {
            os.path.basename(p).split(".")[0]: p
            for p in glob.glob(os.path.join(dataset_dir, "videos", "*.mp4"))
        }
        scenes_by_id = {
            os.path.basename(p).split(".")[0]: p
            for p in glob.glob(os.path.join(dataset_dir, "annotations", "*.txt"))
        }
        self._samples: list[Sample] = [
            Sample(
                video_file=Path(videos_by_id[vid]),
                ground_truth=GroundTruth(hard_cuts=_read_tab_separated_cuts(scenes_by_id[vid])),
            )
            for vid in sorted(videos_by_id.keys() & scenes_by_id.keys())
        ]


class ClipShotsDataset(Dataset):
    """The ClipShots dataset (test split by default).

    Tang et al., "Fast Video Shot Transition Localization with Deep Structured Models",
    ACCV 2018. https://github.com/Tangshitao/ClipShots

    The only in-tree dataset with typed gradual-transition (fade/dissolve) ground truth in
    addition to hard cuts. Layout under ``ClipShots/``::

        annotations/{train,test,only_gradual}.json
        video_lists/{train,test,only_gradual}.txt   (optional split filter)
        videos/*.mp4

    Each annotation entry is ``{"transitions": [[start, end], ...], "frame_num": float}``.
    Hard cuts are single-frame spans (``end == start + 1``); wider spans are gradual
    transitions. Unlike the BBC/AutoShot annotations, ClipShots frame indices already match
    PySceneDetect's boundary-frame convention (the prediction's ``frame_num`` lines up with
    ``transition[1]`` directly), so no offset is applied here.

    Loading rules:

    - Videos listed in ``video_lists/<split>.txt`` but absent from the annotations JSON are
      silently ignored (the filter runs against the JSON, not the other way).
    - Annotations whose ``.mp4`` is not on disk are skipped (so partial corpora work).
    - Malformed transitions (fewer than 2 entries, negative span, zero-width span) are
      skipped with a warning rather than crashing the load.

    Only the ``ClipShotsDataset(dir, split=...)`` constructor honors a non-default split;
    the registry entry in :data:`DATASETS` always loads the ``test`` split.
    """

    event_types = frozenset({"hard_cut", "fade"})

    def __init__(self, dataset_dir: str, split: str = "test"):
        ann_path = os.path.join(dataset_dir, "annotations", f"{split}.json")
        videos_dir = os.path.join(dataset_dir, "videos")
        with open(ann_path) as f:
            annotations: dict = json.load(f)
        split_list_path = os.path.join(dataset_dir, "video_lists", f"{split}.txt")
        if os.path.exists(split_list_path):
            with open(split_list_path) as allow_f:
                allowed = {line.strip() for line in allow_f if line.strip()}
            annotations = {k: v for k, v in annotations.items() if k in allowed}
        total = len(annotations)
        skipped_missing = 0
        self._samples: list[Sample] = []
        for video_name in sorted(annotations):
            video_path = os.path.join(videos_dir, video_name)
            if not os.path.exists(video_path):
                skipped_missing += 1
                continue
            hard_cuts: list[Frames] = []
            fades: list[EventInterval] = []
            # `... or []` (not `.get(k, [])`) so an explicit JSON `null` is treated as empty.
            for transition in annotations[video_name].get("transitions") or []:
                if len(transition) < 2:
                    logger.warning("ClipShots %s: malformed transition %r", video_name, transition)
                    continue
                start, end = int(transition[0]), int(transition[1])
                span = end - start
                if span == 1:
                    hard_cuts.append(end)
                elif span > 1:
                    fades.append(EventInterval(start=start, end=end))
                else:
                    logger.warning(
                        "ClipShots %s: skipping degenerate transition %r", video_name, transition
                    )
            self._samples.append(
                Sample(
                    video_file=Path(video_path),
                    ground_truth=GroundTruth(hard_cuts=hard_cuts, fades=fades),
                )
            )
        logger.info(
            "ClipShots %s: loaded %d/%d samples (%d videos missing on disk)",
            split,
            len(self._samples),
            total,
            skipped_missing,
        )


# Mapping of --dataset names to constructors. Typed as a plain callable so
# subclass-specific positional signatures (each takes ``dataset_dir: str``)
# aren't widened away by the base ``Dataset`` class's empty ``__init__``.
DATASETS: dict[str, type] = {
    "BBC": BBCDataset,
    "AutoShot": AutoShotDataset,
    "ClipShots": ClipShotsDataset,
}


def resolve_dataset(name: str, root: str | None) -> Dataset:
    """Instantiate the named dataset.

    ``root`` overrides the default repo-relative path; pass ``None`` (or the empty string)
    to use ``benchmark/<name>/``.
    """
    base = root if root else "benchmark"
    return DATASETS[name](os.path.join(base, name))
