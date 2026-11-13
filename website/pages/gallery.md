
# Project Gallery

The following open-source projects use PySceneDetect in their own code.  They are listed for reference only: PySceneDetect does not endorse or maintain them, and each project is covered by its own license.

If you know of a project that should be listed here, feel free to [raise an issue](https://github.com/Breakthrough/PySceneDetect/issues/new/choose) with a link to where it uses PySceneDetect.  Research papers that use PySceneDetect are listed on the [Research & Literature](literature.md) page.

## Datasets and Model Training

 - [LTX-2](https://github.com/Lightricks/LTX-2) - the LTX-2 trainer's `split_scenes.py` script cuts training videos into scenes
 - [Data-Juicer](https://github.com/datajuicer/data-juicer) - the `video_split_by_scene_mapper` operator splits videos at scene changes, with a choice of detector
 - [OneTrainer](https://github.com/Nerogar/OneTrainer) - the video tool finds cuts with `AdaptiveDetector` when extracting clips
 - [VideoX-Fun](https://github.com/aigc-apps/VideoX-Fun) - detects cuts in its video captioning pipeline

## Video Generation

 - [ViMax](https://github.com/HKUDS/ViMax) - splits generated transition videos into shots with `split_video_ffmpeg`
 - [InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk) - detects shots in the input video, combining the content, adaptive, and threshold detectors

## Agents, RAG, and Data Tools

 - [ECC](https://github.com/affaan-m/ECC) - measures the cut cadence of a reference video by sweeping `ContentDetector` thresholds
 - [RAG-Anything](https://github.com/HKUDS/RAG-Anything) - segments videos into scenes before indexing them
 - [CAMEL](https://github.com/camel-ai/camel) - the `VideoAnalysisToolkit` extracts keyframes at scene changes
 - [Skill Seekers](https://github.com/yusufkaraaslan/Skill_Seekers) - the video scraper finds scene boundaries, then extracts keyframes
 - [OmAgent](https://github.com/om-ai-lab/OmAgent) - splits videos into scenes for its video understanding agent
 - [Pixeltable](https://github.com/pixeltable/pixeltable) - provides `scene_detect` video functions, with a cookbook notebook
 - [MassGen](https://github.com/massgen/MassGen) - the video extraction tool takes frames from each scene

## Applications and Tools

 - [Moondream](https://github.com/m87-labs/moondream) - the content moderation recipe detects scenes before running the model
 - [REAL Video Enhancer](https://github.com/TNTwise/REAL-Video-Enhancer) - includes a copy of `ContentDetector` to catch scene changes while rendering
 - [movie-narrator](https://github.com/zcbacxc/movie-narrator) - detects scenes as one step of its movie recap pipeline
