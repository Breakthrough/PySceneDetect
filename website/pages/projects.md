# Projects & Research

This page highlights industry and cloud adoption alongside open-source projects, research papers, and similar tools related to PySceneDetect. To suggest an addition, [open an issue on GitHub](https://github.com/Breakthrough/PySceneDetect/issues/new/choose).

## Projects Utilizing PySceneDetect

The projects listed below are publicly known to use PySceneDetect in their code or implementation and are listed for *reference only*. **PySceneDetect neither maintains nor endorses any projects and links listed on this page.**

### Industry Adoption

| Organization | Project | Description |
| --- | --- | --- |
| NVIDIA | [Semantic Split C-RADIO NIM](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/nv-semantic-split-cradio/-) | GPU-accelerated PySceneDetect performs initial scene splitting before C-RADIO semantic stitching and filtering. |
| NVIDIA (NVlabs) | [ShotBench](https://github.com/NVlabs/ShotBench) | Cosmos shot-detection evaluation suite wrapping `ContentDetector`. |
| Amazon Web Services | [Bedrock Video Understanding](https://github.com/aws-samples/sample-bedrock-video-understanding) | AWS Lambda layer running `ContentDetector` to segment S3 videos for Amazon Bedrock multimodal analysis ([AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/unlocking-video-insights-at-scale-with-amazon-bedrock-multimodal-models/)). |
| Google Cloud | [Multimodal Data Curation](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/use-cases/multimodal-data-curation) | Uses `SceneManager` and `ContentDetector` with Cloud Storage, Dataflow, and Vertex AI Gemini for video dataset curation. |
| Microsoft | [MMCTAgent](https://github.com/microsoft/MMCTAgent) | Video-reasoning agent framework using `ContentDetector` and `AdaptiveDetector` in its scene chunking pipeline. |
| Microsoft Research | [Magma](https://github.com/microsoft/Magma) | Video preprocessing pipeline running `ContentDetector` to split training videos into single-scene clips. |
| Microsoft Azure | [Real-Time Video Generation](https://github.com/Azure/realtimevideogen) | Serving stack using `SceneManager` and `ContentDetector` across its `StreamEdit`, `StreamDub`, and `StreamShort` apps. |
| Oracle Cloud Infrastructure | [Multimodal Data Processing with NVIDIA Nemotron](https://blogs.oracle.com/ai-and-datascience/multimodal-data-processing-nvidia-nemotron-model) | Scales PySceneDetect via Ray actors with FFmpeg proxies ahead of NVIDIA Nemotron Nano 2 VL inference on H100 GPUs. |
| Backblaze | [B2 Video Scene Search](https://github.com/backblaze-b2-samples/clip-video-scene-search) | Reference Backblaze B2 sample app using `ContentDetector` to segment videos for semantic scene search. |
| Elastic & Jina AI | [AI Video Search with Elasticsearch](https://www.elastic.co/search-labs/blog/ai-video-search-jina-embeddings) | Elasticsearch Labs guide using PySceneDetect for scene boundary detection before FFmpeg chunking and Jina multimodal vector indexing. |
| Hugging Face | [video-dataset-scripts](https://github.com/huggingface/video-dataset-scripts) | Video fine-tuning toolkit providing `scene_split.py` with `ContentDetector` and `split_video_ffmpeg`. |
| Hugging Face | [FineVideo](https://github.com/huggingface/fineVideo) | Dataset alignment pipeline using `SceneManager` and `ContentDetector` to align scene boundaries and frame rates. |
| Sony AI | [HumanGif](https://github.com/sony/humangif) | Segments raw training videos into duration-bounded single-scene clips using `AdaptiveDetector`. |
| Alibaba (ModelScope) | [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio) | Splits input videos into shots in `video_process.py` for audio-visual speaker separation. |
| Alibaba (Tongyi Lab) | [Tongyi DeepResearch](https://github.com/Alibaba-NLP/DeepResearch) | Built-in `video_analysis.py` agent tool using `ContentDetector` for scene-aware keyframe extraction. |
| ByteDance | [LatentSync](https://github.com/bytedance/LatentSync) | Preprocessing pipeline running the `scenedetect` CLI (`detect-adaptive` and `split-video`) to split training videos into shots. |
| ByteDance (Seed) | [VeOmni](https://github.com/ByteDance-Seed/VeOmni) | Stage-1 multimodal training preprocessor splitting raw videos into scene clips with PySceneDetect and FFmpeg. |
| Tencent (Hunyuan) | [OmniCapBench](https://github.com/Tencent-Hunyuan/OmniCapBench) | Audio-visual captioning evaluation pipeline running `ContentDetector` for video segmentation. |
| Tencent (ARC Lab) | [VerseCrafter](https://github.com/TencentARC/VerseCrafter) | 4D video world-model dataset pipeline running `ContentDetector` in `1_run_scenedetect.py` to export scene lists. |
| Zhipu AI | [ZCode Plugins (`video-agent-kit`)](https://github.com/zai-org/zcode-plugins/blob/main/plugins/video-agent-kit/mcp/ve_tools/shots.py) | MCP server tool (`ve_tools/shots.py`) running `ContentDetector` to generate `shots.json` shot timeline caches. |

### Video Generation, Datasets & Model Training

- [LTX-2](https://github.com/Lightricks/LTX-2): cuts training videos into scenes with `split_scenes.py`.
- [Data-Juicer](https://github.com/datajuicer/data-juicer): splits videos at scene changes with its `video_split_by_scene_mapper` operator.
- [OneTrainer](https://github.com/Nerogar/OneTrainer): finds cuts with `AdaptiveDetector` when extracting training clips.
- [VideoX-Fun](https://github.com/aigc-apps/VideoX-Fun): detects cuts in its video captioning pipeline.
- [ViMax](https://github.com/HKUDS/ViMax): splits generated transition videos into shots with `split_video_ffmpeg`.
- [InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk): detects shots in input videos by combining the content, adaptive, and threshold detectors.

### Agents, RAG, Datasets, Apps & Tools

- [Moondream](https://github.com/m87-labs/moondream): detects scenes before running its content moderation model.
- [REAL Video Enhancer](https://github.com/TNTwise/REAL-Video-Enhancer): includes `ContentDetector` to catch scene changes during rendering.
- [movie-narrator](https://github.com/zcbacxc/movie-narrator): detects scenes as part of its movie recap pipeline.
- [ECC](https://github.com/affaan-m/ECC): measures the cut cadence of a reference video by sweeping `ContentDetector` thresholds.
- [RAG-Anything](https://github.com/HKUDS/RAG-Anything): splits videos into scenes before indexing them.
- [CAMEL](https://github.com/camel-ai/camel): extracts keyframes at scene changes in `VideoAnalysisToolkit`.
- [Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers): finds scene boundaries in scraped videos before extracting keyframes.
- [OmAgent](https://github.com/om-ai-lab/OmAgent): splits videos into scenes for its video understanding agent.
- [Pixeltable](https://github.com/pixeltable/pixeltable): provides `scene_detect` video functions with an example notebook.
- [MassGen](https://github.com/massgen/MassGen): extracts frames from each scene in its video extraction tool.


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
