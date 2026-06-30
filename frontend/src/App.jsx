import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import GeneratorTabs from "./components/GeneratorTabs";
import CaptionStyleSection from "./components/CaptionStyleSection";
import ArtStyleSection from "./components/ArtStyleSection";
import BackgroundMusicSection from "./components/BackgroundMusicSection";
import ScriptGeneratorSection from "./components/ScriptGeneratorSection";
import VoiceoverGeneratorSection from "./components/VoiceoverGeneratorSection";
import VideoGeneratorSection from "./components/VideoGeneratorSection";
import SceneAnimationSection from "./components/SceneAnimationSection";
import { backend, defaultProjectId } from "./lib/api";
import { resolveQueueConfiguration } from "./lib/jobPayloads";
import AppShell from "./routes/AppShell";
import AssetsPage from "./routes/AssetsPage";
import BillingPage from "./routes/BillingPage";
import CreateSeriesPage from "./routes/CreateSeriesPage";
import DashboardPage from "./routes/DashboardPage";
import GeneratePage from "./routes/GeneratePage";
import JobDetailPage from "./routes/JobDetailPage";
import NotFoundPage from "./routes/NotFoundPage";
import ProjectJobsPage from "./routes/ProjectJobsPage";
import ProjectPage from "./routes/ProjectPage";
import {
  artStylePresets,
  defaultArtStylePreset,
} from "./data/artStylePresets";
import { artModelOptions, Z_IMAGE_TURBO_MODEL } from "./data/artModels";
import { supportedLanguages } from "./data/languages";
import {
  backgroundMusicVariants,
  defaultMusicPreset,
  musicPresets,
} from "./data/musicPresets";
import {
  captionStylePresets,
  defaultCaptionStylePreset,
  transcriptFormats,
} from "./data/captionStylePresets";
import {
  defaultScriptPreset,
  durationOptions,
  scriptPresets,
} from "./data/scriptPresets";
import { scriptModelOptions } from "./data/scriptModels";
import {
  defaultVoiceStyle,
  supportedVoiceGenders,
  getVoiceId,
  voiceStyles,
} from "./data/voiceStyles";
import {
  GEMINI_FLASH_TTS_MODEL,
  geminiLanguageOptions,
  geminiVoiceOptions,
  voiceModelOptions,
} from "./data/voiceModels";
import {
  videoAspectRatioOptions,
  videoDurationOptions,
  videoQualityOptions,
} from "./data/videoOptions";

const initialScriptForm = {
  niche: defaultScriptPreset.niche,
  style: defaultScriptPreset.style,
  topic_hint: "",
  duration_seconds: 60,
  model: "openai/gpt-5.1",
  truth_mode: defaultScriptPreset.truth_mode,
  language: "Malay",
};

const initialVoiceForm = {
  text: "",
  style_name: "Gemini Narrator",
  gender: "Female",
  voice_id: "Achernar",
  similarity: 0.85,
  stability: 0.45,
  use_speaker_boost: true,
  model: GEMINI_FLASH_TTS_MODEL,
  language: "English (United States)",
  speaker_name: "Narrator",
};

const initialMusicForm = {
  prompt: defaultMusicPreset.prompt,
  style_name: defaultMusicPreset.title,
  number_of_songs: 1,
  output_format: "mp3",
  model: "mureka-ai/mureka-v9/generate-bgm",
};

const initialArtForm = {
  prompt: "A lone investigator studying classified files in a dim archive room",
  style_name: defaultArtStylePreset.title,
  art_direction: defaultArtStylePreset.artDirection,
  model: Z_IMAGE_TURBO_MODEL,
  enable_safety_checker: true,
};

const initialCaptionForm = {
  template_name: defaultCaptionStylePreset.templateName,
  transcript_format: "auto",
  language_hint: "",
  style_name: defaultCaptionStylePreset.title,
  output_basename: "",
};

const initialCaptionFiles = {
  input_video: null,
  transcript: null,
};

const initialVideoForm = {
  duration_seconds: 60,
  aspect_ratio: "9:16",
  music_volume: 0.16,
  caption_style_id: "hype",
  visual_source: "stills",
  video_quality: "middle",
};

const initialSceneAnimationForm = {
  duration: 5,
  negative_prompt:
    "blurry, low quality, distorted anatomy, warped face, duplicated subject, extra limbs, flicker, jitter, sudden cuts, text, logo, watermark",
};

export default function App() {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState("scripts");
  const [selectedProjectId, setSelectedProjectId] = useState(
    localStorage.getItem("jomveo.selectedProjectId") || defaultProjectId,
  );
  const [dashboardRefresh, setDashboardRefresh] = useState(0);
  const [queueMessage, setQueueMessage] = useState("");
  const [queueError, setQueueError] = useState("");
  const [queueLoading, setQueueLoading] = useState(false);
  const [selectedPresetId, setSelectedPresetId] = useState(defaultScriptPreset.id);
  const [selectedVoiceStyleId, setSelectedVoiceStyleId] = useState(defaultVoiceStyle.id);
  const [selectedMusicPresetId, setSelectedMusicPresetId] = useState(defaultMusicPreset.id);
  const [selectedArtStylePresetId, setSelectedArtStylePresetId] = useState(defaultArtStylePreset.id);
  const [selectedCaptionStylePresetId, setSelectedCaptionStylePresetId] = useState(defaultCaptionStylePreset.id);
  const [scriptForm, setScriptForm] = useState(initialScriptForm);
  const [scriptResult, setScriptResult] = useState(null);
  const [scriptError, setScriptError] = useState("");
  const [scriptLoading, setScriptLoading] = useState(false);
  const [voiceForm, setVoiceForm] = useState(initialVoiceForm);
  const [voiceResult, setVoiceResult] = useState(null);
  const [voiceError, setVoiceError] = useState("");
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [musicForm, setMusicForm] = useState(initialMusicForm);
  const [musicResult, setMusicResult] = useState(null);
  const [musicError, setMusicError] = useState("");
  const [musicLoading, setMusicLoading] = useState(false);
  const [artForm, setArtForm] = useState(initialArtForm);
  const [artResult, setArtResult] = useState(null);
  const [artError, setArtError] = useState("");
  const [artLoading, setArtLoading] = useState(false);
  const [artSceneResult, setArtSceneResult] = useState(null);
  const [artSceneLoading, setArtSceneLoading] = useState(false);
  const [sceneAnimationForm, setSceneAnimationForm] = useState(initialSceneAnimationForm);
  const [sceneAnimationResult, setSceneAnimationResult] = useState(null);
  const [sceneAnimationError, setSceneAnimationError] = useState("");
  const [sceneAnimationLoading, setSceneAnimationLoading] = useState(false);
  const [captionForm, setCaptionForm] = useState(initialCaptionForm);
  const [captionFiles, setCaptionFiles] = useState(initialCaptionFiles);
  const [captionResult, setCaptionResult] = useState(null);
  const [captionError, setCaptionError] = useState("");
  const [captionLoading, setCaptionLoading] = useState(false);
  const [videoForm, setVideoForm] = useState(initialVideoForm);
  const [videoResult, setVideoResult] = useState(null);
  const [videoError, setVideoError] = useState("");
  const [videoLoading, setVideoLoading] = useState(false);

  const selectProject = useCallback((projectId) => {
    setSelectedProjectId(projectId);
    if (projectId) {
      localStorage.setItem("jomveo.selectedProjectId", projectId);
    }
  }, []);

  useEffect(() => {
    if (location.pathname !== "/generate" || selectedProjectId) return undefined;
    let active = true;
    backend.projects().then(data => {
      if (active && data.projects[0]) selectProject(data.projects[0].id);
    }).catch(() => {});
    return () => { active = false; };
  }, [location.pathname, selectProject, selectedProjectId]);

  const selectedPreset =
    scriptPresets.find((preset) => preset.id === selectedPresetId) ?? defaultScriptPreset;
  const selectedVoiceStyle =
    voiceStyles.find((style) => style.id === selectedVoiceStyleId) ?? defaultVoiceStyle;
  const selectedMusicPreset =
    musicPresets.find((preset) => preset.id === selectedMusicPresetId) ?? defaultMusicPreset;
  const selectedArtStylePreset =
    artStylePresets.find((preset) => preset.id === selectedArtStylePresetId) ?? defaultArtStylePreset;
  const selectedCaptionStylePreset =
    captionStylePresets.find((preset) => preset.id === selectedCaptionStylePresetId) ?? defaultCaptionStylePreset;

  const updateScriptField = (event) => {
    const { name, value } = event.target;
    setScriptForm((current) => ({
      ...current,
      [name]: name === "duration_seconds" ? Number(value) : value,
    }));
  };

  const updateVoiceField = (event) => {
    const { name, value } = event.target;
    if (name === "model") {
      setVoiceForm((current) => ({
        ...current,
        model: value,
        voice_id:
          value === GEMINI_FLASH_TTS_MODEL
            ? "Achernar"
            : getVoiceId(selectedVoiceStyle, current.gender),
        language: value === GEMINI_FLASH_TTS_MODEL ? "English (United States)" : "English",
        style_name: value === GEMINI_FLASH_TTS_MODEL ? "Gemini Narrator" : selectedVoiceStyle.name,
      }));
      setVoiceResult(null);
      setVoiceError("");
      return;
    }

    if (name === "gender") {
      setVoiceForm((current) => ({
        ...current,
        [name]: value,
        voice_id: getVoiceId(selectedVoiceStyle, value),
      }));
      setVoiceResult(null);
      setVoiceError("");
      return;
    }

    setVoiceForm((current) => ({
      ...current,
      [name]:
        name === "similarity" || name === "stability"
          ? Number(value)
          : name === "use_speaker_boost"
            ? event.target.checked
            : value,
    }));
  };

  const updateMusicField = (event) => {
    const { name, value } = event.target;
    setMusicForm((current) => ({
      ...current,
      [name]: name === "number_of_songs" ? Number(value) : value,
    }));
  };

  const updateArtField = (event) => {
    const { name, value, checked, type } = event.target;
    setArtForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const updateCaptionField = (event) => {
    const { name, value } = event.target;
    setCaptionForm((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const updateCaptionFile = (event) => {
    const { name, files } = event.target;
    setCaptionFiles((current) => ({
      ...current,
      [name]: files?.[0] ?? null,
    }));
    setCaptionResult(null);
    setCaptionError("");
  };

  const updateVideoField = (event) => {
    const { name, value } = event.target;
    setVideoForm((current) => ({
      ...current,
      [name]:
        name === "duration_seconds"
          ? Number(value)
          : name === "music_volume"
            ? Number(value)
            : value,
    }));
    setVideoResult(null);
    setVideoError("");
  };

  const updateSceneAnimationField = (event) => {
    const { name, value } = event.target;
    setSceneAnimationForm((current) => ({
      ...current,
      [name]: name === "duration" ? Number(value) : value,
    }));
    setSceneAnimationResult(null);
    setSceneAnimationError("");
  };

  const applyScriptPreset = (preset) => {
    setSelectedPresetId(preset.id);
    setScriptForm((current) => ({
      ...current,
      niche: preset.niche,
      style: preset.style,
      truth_mode: preset.truth_mode,
      topic_hint: "",
    }));
    setScriptResult(null);
    setScriptError("");
  };

  const applyVoiceStyle = (style) => {
    setSelectedVoiceStyleId(style.id);
    setVoiceForm((current) => ({
      ...current,
      style_name: style.name,
      voice_id:
        current.model === GEMINI_FLASH_TTS_MODEL
          ? current.voice_id
          : getVoiceId(style, current.gender),
    }));
    setVoiceResult(null);
    setVoiceError("");
  };

  const applyMusicPreset = (preset) => {
    setSelectedMusicPresetId(preset.id);
    setMusicForm((current) => ({
      ...current,
      prompt: preset.prompt,
      style_name: preset.title,
    }));
    setMusicResult(null);
    setMusicError("");
  };

  const applyArtStylePreset = (preset) => {
    setSelectedArtStylePresetId(preset.id);
    setArtForm((current) => ({
      ...current,
      style_name: preset.title,
      art_direction: preset.artDirection,
    }));
    setArtResult(null);
    setArtError("");
  };

  const applyCaptionStylePreset = (preset) => {
    setSelectedCaptionStylePresetId(preset.id);
    setCaptionForm((current) => ({
      ...current,
      style_name: preset.title,
      template_name: preset.templateName,
    }));
    setCaptionResult(null);
    setCaptionError("");
  };

  const useLatestScriptForVoiceover = () => {
    if (!scriptResult?.script) {
      return;
    }

    setVoiceForm((current) => {
      return {
        ...current,
        text: scriptResult.script,
        voice_id:
          current.model === GEMINI_FLASH_TTS_MODEL
            ? current.voice_id
            : getVoiceId(selectedVoiceStyle, current.gender),
      };
    });
    setVoiceError("");
    setActiveTab("voiceover");
  };

  const useLatestScriptForMusic = () => {
    if (!scriptResult?.script) {
      return;
    }

    setMusicForm((current) => ({
      ...current,
      prompt: `${selectedMusicPreset.prompt}. Build the mood around this topic: ${scriptResult.title} - ${scriptResult.event_name}. Keep it instrumental background music only.`,
    }));
    setMusicError("");
    setActiveTab("music");
  };

  const useLatestScriptForArt = () => {
    if (!scriptResult?.script) {
      return;
    }

    setArtForm((current) => ({
      ...current,
      prompt: `${scriptResult.title}. Key subject and scene: ${scriptResult.event_name}. Create the most visually striking moment from this story.`,
    }));
    setArtError("");
    setActiveTab("art");
  };

  const handleScriptSubmit = async (event) => {
    event.preventDefault();
    setScriptError("");
    setScriptLoading(true);

    try {
      const response = await fetch("/api/scripts/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(scriptForm),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Script request failed");
      }

      setScriptResult(data);
      setVideoForm((current) => ({
        ...current,
        duration_seconds: data.duration_seconds,
      }));
    } catch (submitError) {
      setScriptError(submitError.message);
    } finally {
      setScriptLoading(false);
    }
  };

  const handleVoiceSubmit = async (event) => {
    event.preventDefault();
    setVoiceError("");
    setVoiceLoading(true);

    try {
      const response = await fetch("/api/voiceovers/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(voiceForm),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Voiceover request failed");
      }

      setVoiceResult(data);
    } catch (submitError) {
      setVoiceError(submitError.message);
    } finally {
      setVoiceLoading(false);
    }
  };

  const handleMusicSubmit = async (event) => {
    event.preventDefault();
    setMusicError("");
    setMusicLoading(true);

    try {
      const response = await fetch("/api/background-music/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(musicForm),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Background music request failed");
      }

      setMusicResult(data);
    } catch (submitError) {
      setMusicError(submitError.message);
    } finally {
      setMusicLoading(false);
    }
  };

  const handleArtSubmit = async (event) => {
    event.preventDefault();
    setArtError("");
    setArtLoading(true);

    try {
      const response = await fetch("/api/art-style/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(artForm),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Art style request failed");
      }

      setArtResult(data);
      setArtSceneResult(null);
    } catch (submitError) {
      setArtError(submitError.message);
    } finally {
      setArtLoading(false);
    }
  };

  const handleArtScenesSubmit = async () => {
    setArtError("");

    if (!scriptResult?.script) {
      setArtError("Generate a script before creating a scene sequence.");
      return;
    }

    setArtSceneLoading(true);
    try {
      const response = await fetch("/api/art-style/scenes/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          script: scriptResult.script,
          title: scriptResult.title,
          event_name: scriptResult.event_name,
          duration_seconds: scriptResult.duration_seconds,
          planner_model: "openai/gpt-5.4-mini",
          style_name: artForm.style_name,
          art_direction: artForm.art_direction,
          model: artForm.model,
          enable_safety_checker: artForm.enable_safety_checker,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Scene sequence request failed");
      }

      setArtSceneResult(data);
      setArtResult(null);
      setSceneAnimationResult(null);
    } catch (submitError) {
      setArtError(submitError.message);
    } finally {
      setArtSceneLoading(false);
    }
  };

  const handleSceneAnimationSubmit = async (event) => {
    event.preventDefault();
    setSceneAnimationError("");
    if (!artSceneResult?.scenes?.length) {
      setSceneAnimationError("Generate an art scene sequence before animating it.");
      return;
    }

    setSceneAnimationLoading(true);
    try {
      const response = await fetch("/api/scene-animations/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          duration: sceneAnimationForm.duration,
          negative_prompt: sceneAnimationForm.negative_prompt,
          model: "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
          scenes: artSceneResult.scenes.map((scene) => ({
            scene_number: scene.scene_number,
            image_url: scene.image_url,
            motion_prompt: scene.motion_prompt,
          })),
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Scene animation failed");
      }
      setSceneAnimationResult(data);
    } catch (submitError) {
      setSceneAnimationError(submitError.message);
    } finally {
      setSceneAnimationLoading(false);
    }
  };

  const handleCaptionSubmit = async (event) => {
    event.preventDefault();
    setCaptionError("");

    if (!captionFiles.input_video) {
      setCaptionError("Please upload a video file before rendering captions.");
      return;
    }

    setCaptionLoading(true);

    try {
      const body = new FormData();
      body.append("input_video", captionFiles.input_video);
      body.append("template_name", captionForm.template_name);
      body.append("transcript_format", captionForm.transcript_format);
      body.append("language_hint", captionForm.language_hint);
      body.append("style_name", captionForm.style_name);
      body.append("output_basename", captionForm.output_basename);

      if (captionFiles.transcript) {
        body.append("transcript", captionFiles.transcript);
      }

      const response = await fetch("/api/caption-style/generate", {
        method: "POST",
        body,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Caption style request failed");
      }

      setCaptionResult(data);
    } catch (submitError) {
      setCaptionError(submitError.message);
    } finally {
      setCaptionLoading(false);
    }
  };

  const handleVideoSubmit = async (event) => {
    event.preventDefault();
    setVideoError("");

    const hasSelectedVisuals =
      videoForm.visual_source === "animated"
        ? Boolean(sceneAnimationResult?.scenes?.length)
        : Boolean(artSceneResult?.scenes?.length);
    if (!hasSelectedVisuals || !voiceResult?.audio_url) {
      setVideoError("Generate the selected visual source and a voiceover before creating the video.");
      return;
    }

    setVideoLoading(true);
    try {
      const videoCaptionPreset =
        captionStylePresets.find((preset) => preset.id === videoForm.caption_style_id) ??
        defaultCaptionStylePreset;
      const response = await fetch("/api/videos/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: scriptResult?.title || "Generated video",
          duration_seconds: videoForm.duration_seconds,
          aspect_ratio: videoForm.aspect_ratio,
          visual_source: videoForm.visual_source,
          image_urls: artSceneResult.scenes.map((scene) => scene.image_url),
          video_urls: sceneAnimationResult?.scenes?.map((scene) => scene.video_url) || [],
          voiceover_url: voiceResult.audio_url,
          music_url: musicResult?.audio_urls?.[0] || "",
          music_volume: videoForm.music_volume,
          caption_template: videoCaptionPreset.templateName,
          caption_style_name: videoCaptionPreset.title,
          language_hint: scriptResult?.language === "Malay" ? "ms" : "en",
          reference_script: voiceForm.text || scriptResult?.script || "",
          video_quality: videoForm.video_quality,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Video creation failed");
      }

      setVideoResult(data);
    } catch (submitError) {
      setVideoError(submitError.message);
    } finally {
      setVideoLoading(false);
    }
  };

  const queueConfiguration = (requestedKind) => {
    return resolveQueueConfiguration({activeTab,requestedKind,scriptForm,voiceForm,musicForm,artForm,scriptResult,artSceneResult,sceneAnimationForm,sceneAnimationResult,voiceResult,musicResult,videoForm,captionStylePresets,defaultCaptionStylePreset});
  };

  const queueProjectJob = async (requestedKind) => {
    setQueueError(""); setQueueMessage("");
    let projectId = selectedProjectId;
    if (!projectId) {
      try {
        setQueueLoading(true);
        const data = await backend.projects();
        projectId = data.projects[0]?.id || "";
        if (projectId) selectProject(projectId);
      } catch (error) {
        setQueueError(error.message);
        setQueueLoading(false);
        return;
      }
    }
    if (!projectId) {
      setQueueError("Please select or create a project before queueing a project job.");
      setQueueLoading(false);
      return;
    }
    const configuration = queueConfiguration(requestedKind);
    if (!configuration) {
      setQueueLoading(false);
      setQueueError(
        activeTab === "voiceover"
          ? "Enter voiceover text before queueing this project job."
          : "Generate the required source content before queueing this project job.",
      );
      return;
    }
    try {
      setQueueLoading(true); const [kind, payload] = configuration; const accepted = await backend.createJob(kind, payload, projectId);
      setQueueMessage(`Queued project job ${accepted.job_id}.`); setDashboardRefresh(value => value + 1);
    } catch (error) { setQueueError(error.message); } finally { setQueueLoading(false); }
  };

  const generatorWorkspace = (
      <section className="tabs-shell">
        <GeneratorTabs activeTab={activeTab} onChange={setActiveTab} />
        {activeTab !== "captions" ? <div className="queue-control"><button type="button" disabled={queueLoading} onClick={() => queueProjectJob()}>{queueLoading?"Queueing…":`Queue ${activeTab === "scripts" ? "script" : activeTab === "voiceover" ? "voiceover" : activeTab === "music" ? "music" : activeTab === "art" ? "art" : activeTab === "animation" ? "animation" : "video"} job`}</button>{activeTab === "art" ? <button type="button" disabled={queueLoading} onClick={() => queueProjectJob("art-style/scenes")}>{queueLoading?"Queueing…":"Queue scene sequence job"}</button> : null}<p>Project jobs use the selected project, billing credits, quota checks, and appear in the dashboard.</p>{queueMessage ? <p className="message success">{queueMessage}</p> : null}{queueError ? <p className="message error">{queueError}</p> : null}</div> : <p className="helper-text">Caption rendering currently runs synchronously.</p>}

        {activeTab === "scripts" ? (
          <ScriptGeneratorSection
            presets={scriptPresets}
            selectedPresetId={selectedPresetId}
            selectedPreset={selectedPreset}
            form={scriptForm}
            result={scriptResult}
            error={scriptError}
            loading={scriptLoading}
            supportedLanguages={supportedLanguages}
            durationOptions={durationOptions}
            modelOptions={scriptModelOptions}
            onPresetSelect={applyScriptPreset}
            onFieldChange={updateScriptField}
            onSubmit={handleScriptSubmit}
          />
        ) : null}

        {activeTab === "voiceover" ? (
          <VoiceoverGeneratorSection
            styles={voiceStyles}
            selectedStyleId={selectedVoiceStyleId}
            selectedStyle={selectedVoiceStyle}
            form={voiceForm}
            result={voiceResult}
            error={voiceError}
            loading={voiceLoading}
            hasScriptText={Boolean(scriptResult?.script)}
            supportedVoiceGenders={supportedVoiceGenders}
            modelOptions={voiceModelOptions}
            geminiVoiceOptions={geminiVoiceOptions}
            geminiLanguageOptions={geminiLanguageOptions}
            geminiModel={GEMINI_FLASH_TTS_MODEL}
            onStyleSelect={applyVoiceStyle}
            onUseLatestScript={useLatestScriptForVoiceover}
            onFieldChange={updateVoiceField}
            onSubmit={handleVoiceSubmit}
          />
        ) : null}

        {activeTab === "music" ? (
          <BackgroundMusicSection
            presets={musicPresets}
            selectedPresetId={selectedMusicPresetId}
            form={musicForm}
            result={musicResult}
            error={musicError}
            loading={musicLoading}
            hasScriptText={Boolean(scriptResult?.script)}
            variantOptions={backgroundMusicVariants}
            onPresetSelect={applyMusicPreset}
            onUseLatestScript={useLatestScriptForMusic}
            onFieldChange={updateMusicField}
            onSubmit={handleMusicSubmit}
          />
        ) : null}

        {activeTab === "art" ? (
          <ArtStyleSection
            presets={artStylePresets}
            modelOptions={artModelOptions}
            selectedPresetId={selectedArtStylePresetId}
            form={artForm}
            result={artResult}
            sceneResult={artSceneResult}
            error={artError}
            loading={artLoading}
            sceneLoading={artSceneLoading}
            hasScriptText={Boolean(scriptResult?.script)}
            onPresetSelect={applyArtStylePreset}
            onUseLatestScript={useLatestScriptForArt}
            onFieldChange={updateArtField}
            onSubmit={handleArtSubmit}
            onSceneSubmit={handleArtScenesSubmit}
          />
        ) : null}

        {activeTab === "captions" ? (
          <CaptionStyleSection
            presets={captionStylePresets}
            selectedPresetId={selectedCaptionStylePresetId}
            form={captionForm}
            files={captionFiles}
            result={captionResult}
            error={captionError}
            loading={captionLoading}
            transcriptFormats={transcriptFormats}
            onPresetSelect={applyCaptionStylePreset}
            onFieldChange={updateCaptionField}
            onFileChange={updateCaptionFile}
            onSubmit={handleCaptionSubmit}
          />
        ) : null}

        {activeTab === "animation" ? (
          <SceneAnimationSection
            form={sceneAnimationForm}
            result={sceneAnimationResult}
            error={sceneAnimationError}
            loading={sceneAnimationLoading}
            hasScenes={Boolean(artSceneResult?.scenes?.length)}
            sceneCount={artSceneResult?.scene_count || 0}
            onFieldChange={updateSceneAnimationField}
            onSubmit={handleSceneAnimationSubmit}
          />
        ) : null}

        {activeTab === "video" ? (
          <VideoGeneratorSection
            form={videoForm}
            result={videoResult}
            error={videoError}
            loading={videoLoading}
            hasScenes={Boolean(artSceneResult?.scenes?.length)}
            hasVoiceover={Boolean(voiceResult?.audio_url)}
            hasMusic={Boolean(musicResult?.audio_urls?.length)}
            hasAnimatedScenes={Boolean(sceneAnimationResult?.scenes?.length)}
            animatedSceneCount={sceneAnimationResult?.scene_count || 0}
            sceneCount={artSceneResult?.scene_count || 0}
            captionStylePresets={captionStylePresets}
            durationOptions={videoDurationOptions}
            aspectRatioOptions={videoAspectRatioOptions}
            qualityOptions={videoQualityOptions}
            onFieldChange={updateVideoField}
            onSubmit={handleVideoSubmit}
          />
        ) : null}
      </section>
  );

  return (
    <AppShell selectedProjectId={selectedProjectId}>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/workspace" element={<Navigate to="/dashboard" replace />} />
        <Route path="/series/new" element={<Navigate to="/create" replace />} />
        <Route path="/create" element={<CreateSeriesPage projectId={selectedProjectId} onProjectChange={selectProject} />} />
        <Route path="/dashboard" element={<DashboardPage projectId={selectedProjectId} onProjectChange={selectProject} refreshToken={dashboardRefresh} />} />
        <Route path="/generate" element={<GeneratePage>{generatorWorkspace}</GeneratePage>} />
        <Route path="/projects/:projectId" element={<ProjectPage onProjectChange={selectProject} refreshToken={dashboardRefresh} />} />
        <Route path="/projects/:projectId/jobs" element={<ProjectJobsPage onProjectChange={selectProject} />} />
        <Route path="/projects/:projectId/assets" element={<AssetsPage onProjectChange={selectProject} />} />
        <Route path="/projects/:projectId/billing" element={<BillingPage onProjectChange={selectProject} />} />
        <Route path="/jobs/:jobId" element={<JobDetailPage selectedProjectId={selectedProjectId} />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  );
}
