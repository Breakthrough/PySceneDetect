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

The papers below either use PySceneDetect in their video pipelines or evaluate shot-boundary detection methods against it:

| Paper | Year | Use Case |
| --- | --- | --- |
| [SAM 3: Segment Anything with Concepts](https://arxiv.org/abs/2511.16719) | 2025 | Shot boundary detection to pick single-shot clips. |
| [V-JEPA 2: Self-Supervised Video Models Enable Understanding, Prediction and Planning](https://arxiv.org/abs/2506.09985) | 2025 | Splits pretraining videos into clips at scene transitions. |
| [MAGI-1: Autoregressive Video Generation at Scale](https://arxiv.org/abs/2505.13211) | 2025 | Cuts long videos into single-shot clips. |
| [Cosmos World Foundation Model Platform for Physical AI](https://arxiv.org/abs/2501.03575) | 2025 | One of the shot boundary detectors evaluated. |
| [Open-Sora: Democratizing Efficient Video Production for All](https://arxiv.org/abs/2412.20404) | 2024 | Detects scenes and cuts videos into clips. |
| [HunyuanVideo: A Systematic Framework For Large Video Generative Models](https://arxiv.org/abs/2412.03603) | 2024 | Splits raw videos into single-shot clips. |
| [Movie Gen: A Cast of Media Foundation Models](https://arxiv.org/abs/2410.13720) | 2024 | Shot boundary detection to filter out videos with jittery camera movement. |
| [LLaVA-Video: Video Instruction Tuning With Synthetic Data](https://arxiv.org/abs/2410.02713) | 2024 | Counts scenes in a video to select dynamic videos. |
| [Emu3: Next-Token Prediction is All You Need](https://arxiv.org/abs/2409.18869) | 2024 | Uses `ContentDetector` and `ThresholdDetector` to split videos into scenes. |
| [Panda-70M: Captioning 70M Videos with Multiple Cross-Modality Teachers](https://arxiv.org/abs/2402.19479) | 2024 | Stage-1 shot boundary detection in its semantics-aware video splitting pipeline. |
| [Stable Video Diffusion: Scaling Latent Video Diffusion Models to Large Datasets](https://arxiv.org/abs/2311.15127) | 2023 | Cut detection on base video clips, run at three frame rates. |
| [LaVie: High-Quality Video Generation with Cascaded Latent Diffusion Models](https://arxiv.org/abs/2309.15103) | 2023 | Scene detection to segment the dataset's source videos. |
| [InternVid: A Large-scale Video-Text Dataset for Multimodal Understanding and Generation](https://arxiv.org/abs/2307.06942) | 2023 | Cuts videos at scene changes with threshold 27. |
| [Stable Remaster: Bridging the Gap Between Old Content and New Displays](https://arxiv.org/abs/2306.06803) | 2023 | Python API to segment episodes into scene clips for parallel remastering. |
| [LoL-V2T: Large-Scale Esports Video Description Dataset](https://ieeexplore.ieee.org/abstract/document/9522986) | 2021 | Splits full-match esports broadcasts into clips before filtering non-gameplay scenes. |
| [Online Detection of Action Start via Soft Computing for Smart City](https://ieeexplore.ieee.org/document/9099408) | 2020 | Online action-start detection in smart-city video analysis. |
| [Thesis Project: Smart Shades and Cane for The Blind](https://www.linkedin.com/pulse/blind-people-dont-have-good-muhammad-hashim-1f/) | 2020 | Assistive-vision thesis project using scene change analysis. |
| [Movienet: a movie multilayer network model using visual and textual semantic cues](https://appliednetsci.springeropen.com/articles/10.1007/s41109-019-0226-0) | 2019 | Extracts movie scenes for a multilayer narrative network model. |
| [Story Understanding in Video Advertisements](https://arxiv.org/abs/1807.11122) | 2018 | Shot boundary detection as a climax indicator feature in video ads. |
| [Online Detection of Action Start in Untrimmed, Streaming Videos](https://arxiv.org/abs/1802.06822) | 2018 | Shot boundary detection baseline evaluated against online action-start detection. |
| [NLP-Enriched Automatic Video Segmentation](https://ieeexplore.ieee.org/document/8525880/) | 2018 | Visual video segmentation for topic-indexed lecture videos. |

Publicly accessible links are preferred when suggesting new citations, though not required.

## Methodology of PySceneDetect

You can inspect the implementation of every built-in detector in [`scenedetect/detectors/`](https://github.com/Breakthrough/PySceneDetect/tree/main/scenedetect/detectors). For background discussion on references and methods, see [Issue #62](https://github.com/Breakthrough/PySceneDetect/issues/62).

## Similar Programs

These tools and models also detect scene cuts in video:

- [Scenecut Extractor](https://github.com/slhck/scenecut-extractor): wraps the `ffmpeg` `select` filter.
- `ffmpeg` `blackframe` filter ([thanks @tonycpsu](https://github.com/Breakthrough/PySceneDetect/issues/7)): detects fades to black only.
- [Shotdetect](https://github.com/johmathe/Shotdetect): content-based detector for Linux and macOS.
- [MATLAB Scene Change Detection](https://www.mathworks.com/help/vision/examples/scene-change-detection.html): uses feature extraction and edge detection (requires MATLAB and Computer Vision Toolbox).
- [chaptertool](https://github.com/Mtillmann/chaptertool): CLI and web tool that converts PySceneDetect output to other formats.
- [TransNetV2](https://github.com/soCzech/TransNetV2): neural network for shot boundary detection (2020).
- [AutoShot](https://github.com/wentaozhu/AutoShot): neural network for shot boundary detection using neural architecture search (2023).
