# Projects & Research

This page lists open-source projects, research papers, and similar tools related to PySceneDetect. To suggest an addition, [open an issue on GitHub](https://github.com/Breakthrough/PySceneDetect/issues/new/choose).

## Projects Using PySceneDetect

The open-source projects below use PySceneDetect in their own code. They are listed for reference only: PySceneDetect does not maintain or endorse them, and each project has its own license.

### Datasets and model training

- [LTX-2](https://github.com/Lightricks/LTX-2): cuts training videos into scenes with `split_scenes.py`.
- [Data-Juicer](https://github.com/datajuicer/data-juicer): splits videos at scene changes with its `video_split_by_scene_mapper` operator.
- [OneTrainer](https://github.com/Nerogar/OneTrainer): finds cuts with `AdaptiveDetector` when extracting training clips.
- [VideoX-Fun](https://github.com/aigc-apps/VideoX-Fun): detects cuts in its video captioning pipeline.

### Video generation

- [ViMax](https://github.com/HKUDS/ViMax): splits generated transition videos into shots with `split_video_ffmpeg`.
- [InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk): detects shots in input videos by combining the content, adaptive, and threshold detectors.

### Agents, RAG, and data tools

- [ECC](https://github.com/affaan-m/ECC): measures the cut cadence of a reference video by sweeping `ContentDetector` thresholds.
- [RAG-Anything](https://github.com/HKUDS/RAG-Anything): splits videos into scenes before indexing them.
- [CAMEL](https://github.com/camel-ai/camel): extracts keyframes at scene changes in `VideoAnalysisToolkit`.
- [Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers): finds scene boundaries in scraped videos before extracting keyframes.
- [OmAgent](https://github.com/om-ai-lab/OmAgent): splits videos into scenes for its video understanding agent.
- [Pixeltable](https://github.com/pixeltable/pixeltable): provides `scene_detect` video functions with an example notebook.
- [MassGen](https://github.com/massgen/MassGen): extracts frames from each scene in its video extraction tool.

### Applications and tools

- [Moondream](https://github.com/m87-labs/moondream): detects scenes before running its content moderation model.
- [REAL Video Enhancer](https://github.com/TNTwise/REAL-Video-Enhancer): includes `ContentDetector` to catch scene changes during rendering.
- [movie-narrator](https://github.com/zcbacxc/movie-narrator): detects scenes as part of its movie recap pipeline.

## Research and Literature

The papers below either use PySceneDetect for video analysis or compare new shot-boundary detection methods against it:

- [Panda-70M: Captioning 70M Videos with Multiple Cross-Modality Teachers](https://arxiv.org/abs/2402.19479) by Tsai-Shien Chen, Aliaksandr Siarohin, Willi Menapace, Ekaterina Deyneka, Hsiang-wei Chao, Byung Eun Jeon, Yuwei Fang, Hsin-Ying Lee, Jian Ren, Ming-Hsuan Yang, and Sergey Tulyakov (2024).
- [Stable Remaster: Bridging the Gap Between Old Content and New Displays](https://arxiv.org/pdf/2306.06803.pdf) by Nathan Paull, Shuvam Keshari, and Yian Wong (2023).
- [LoL-V2T: Large-Scale Esports Video Description Dataset](https://ieeexplore.ieee.org/abstract/document/9522986) by Tsunehiko Tanaka and Edgar Simo-Serra (2021).
- [Online Detection of Action Start via Soft Computing for Smart City](https://ieeexplore.ieee.org/document/9099408) by Tian Wang, Yang Chen, Hongqiang Lv, Jing Teng, Hichem Snoussi, and Fei Tao (2020).
- [Thesis Project: Smart Shades and Cane for The Blind](https://www.linkedin.com/pulse/blind-people-dont-have-good-muhammad-hashim-1f/) by Muhammad Hashim (2020).
- [Movienet: a movie multilayer network model using visual and textual semantic cues](https://appliednetsci.springeropen.com/articles/10.1007/s41109-019-0226-0) by Youssef Mourchid, Benjamin Renoust, Olivier Roupin, L&ecirc; V&#259;n, Hocine Cherifi, and Mohammed El Hassouni (2019).
- [NLP-Enriched Automatic Video Segmentation](https://ieeexplore.ieee.org/document/8525880/) by Mohannad AlMousa, Rachid Benlamri, and Richard Khoury (2018).
- [Online Detection of Action Start in Untrimmed, Streaming Videos](https://arxiv.org/pdf/1802.06822) by Zheng Shou, Junting Pan, Jonathan Chan, Kazuyuki Miyazawa, Hassan Mansour, Anthony Vetro, Xavi Gir-i-Nieto, and Shih-Fu Chang (2018).
- [Story Understanding in Video Advertisements](https://arxiv.org/pdf/1807.11122) by Keren Ye, Kyle Buettner, and Adriana Kovashka (2018).

Publicly accessible links are preferred when suggesting new citations, though not required.

### Scene detection methodology

You can inspect the implementation of every built-in detector in [`scenedetect/detectors/`](https://github.com/Breakthrough/PySceneDetect/tree/main/scenedetect/detectors). For background discussion on references and methods, see [Issue #62](https://github.com/Breakthrough/PySceneDetect/issues/62).

## Similar Programs

These tools and models also detect scene cuts in video:

- [Scenecut Extractor](https://github.com/slhck/scenecut-extractor): wraps the `ffmpeg` `select` filter.
- `ffmpeg` `blackframe` filter ([thanks @tonycpsu](https://github.com/Breakthrough/PySceneDetect/issues/7)): detects fades to black only.
- [Shotdetect](http://johmathe.name/shotdetect.html): content-based detector for Linux and macOS.
- [MATLAB Scene Change Detection](https://www.mathworks.com/help/vision/examples/scene-change-detection.html): uses feature extraction and edge detection (requires MATLAB and Computer Vision Toolbox).
- [chaptertool](https://github.com/Mtillmann/chaptertool): CLI and web tool that converts PySceneDetect output to other formats.
- [TransNetV2](https://github.com/soCzech/TransNetV2): neural network for shot boundary detection (2020).
- [AutoShot](https://github.com/wentaozhu/AutoShot): neural network for shot boundary detection using neural architecture search (2023).
