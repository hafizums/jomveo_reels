import { useState } from "react";
import { Link } from "react-router-dom";
import { artStylePresets, defaultArtStylePreset } from "../../data/artStylePresets";
import { captionStylePresets, defaultCaptionStylePreset } from "../../data/captionStylePresets";
import { createDurations, createLanguages, createNichePresets, createTones } from "../../data/createPresets";
import { defaultMusicPreset, musicPresets } from "../../data/musicPresets";
import { defaultVoiceStyle, voiceStyles } from "../../data/voiceStyles";
import { videoAspectRatioOptions, videoQualityOptions } from "../../data/videoOptions";
import CreateReviewPanel from "./CreateReviewPanel";
import NichePresetGrid from "./NichePresetGrid";
import SeriesDetailsForm from "./SeriesDetailsForm";
import VisualStyleForm from "./VisualStyleForm";
import VoiceMusicForm from "./VoiceMusicForm";

const initialSeries = {
  nicheId: createNichePresets[0].id,
  customNiche: "",
  seriesName: "",
  topic: "",
  language: "English",
  tone: "documentary",
  duration: 60,
  artStyleId: defaultArtStylePreset.id,
  visualSource: "stills",
  aspectRatio: "9:16",
  videoQuality: "middle",
  captionStyleId: defaultCaptionStylePreset.id,
  voiceStyleId: defaultVoiceStyle.id,
  musicPresetId: defaultMusicPreset.id,
  musicVolume: 0.16,
};

export function buildFirstScriptPayload(form) {
  const preset = createNichePresets.find(item => item.id === form.nicheId) ?? createNichePresets[0];
  const niche = form.nicheId === "custom" ? form.customNiche.trim() : preset.prompt;
  return {
    niche: `${niche || "Create an engaging repeatable faceless video series."} Use a ${form.tone} tone suitable for a recurring series.`,
    style: `${form.tone} storytelling`,
    topic_hint: form.topic.trim() || form.seriesName.trim(),
    duration_seconds: Number(form.duration),
    model: "openai/gpt-5.1",
    truth_mode: preset.truthMode,
    language: form.language,
  };
}

export default function CreateSeriesWizard({ projects, projectId, onProjectChange, onCreateProject, creatingProject, onQueueFirstVideo, externalError = "" }) {
  const [form, setForm] = useState(initialSeries);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [queueing, setQueueing] = useState(false);

  const updateField = event => {
    const { name, value } = event.target;
    setForm(current => ({ ...current, [name]: name === "duration" || name === "musicVolume" ? Number(value) : value }));
    setMessage("");
    setError("");
  };

  const selectedNiche = createNichePresets.find(item => item.id === form.nicheId) ?? createNichePresets[0];
  const selectedArt = artStylePresets.find(item => item.id === form.artStyleId) ?? defaultArtStylePreset;
  const selectedCaption = captionStylePresets.find(item => item.id === form.captionStyleId) ?? defaultCaptionStylePreset;
  const selectedVoice = voiceStyles.find(item => item.id === form.voiceStyleId) ?? defaultVoiceStyle;
  const selectedMusic = musicPresets.find(item => item.id === form.musicPresetId) ?? defaultMusicPreset;
  const selectedProject = projects.find(item => item.id === projectId);
  const nicheLabel = form.nicheId === "custom" ? form.customNiche.trim() || "Custom niche" : selectedNiche.title;

  const summary = {
    Niche: nicheLabel,
    Language: form.language,
    Duration: `${form.duration} seconds`,
    Style: selectedArt.title,
    Voice: selectedVoice.name,
    Captions: selectedCaption.title,
    Project: selectedProject?.name || "No project selected",
  };

  const saveDraft = () => {
    localStorage.setItem("jomveo.seriesDraft", JSON.stringify({ ...form, projectId }));
    setError("");
    setMessage("Series draft saved on this device.");
  };

  const queueFirstVideo = async () => {
    setMessage("");
    setError("");
    if (!projectId) {
      setError("Select or create a project before queueing the first video.");
      return;
    }
    if (form.nicheId === "custom" && !form.customNiche.trim()) {
      setError("Describe your custom niche before queueing the first video.");
      return;
    }
    setQueueing(true);
    try {
      const accepted = await onQueueFirstVideo(buildFirstScriptPayload(form));
      setMessage(`Queued first video script job ${accepted.job_id}.`);
    } catch (queueError) {
      setError(queueError.message || "Could not queue the first video script.");
    } finally {
      setQueueing(false);
    }
  };

  return (
    <section className="create-wizard-card">
      <section className="create-step">
        <header><span>1</span><div><h2>Choose niche</h2><p>Start with a proven format or describe your own.</p></div></header>
        <NichePresetGrid presets={createNichePresets} selectedId={form.nicheId} onSelect={nicheId => setForm(current => ({ ...current, nicheId }))} />
      </section>
      <section className="create-step">
        <header><span>2</span><div><h2>Series details</h2><p>Give the series enough direction to create its first script.</p></div></header>
        <SeriesDetailsForm form={form} onChange={updateField} projects={projects} projectId={projectId} onProjectChange={onProjectChange} onCreateProject={onCreateProject} creatingProject={creatingProject} languages={createLanguages} tones={createTones} durations={createDurations} />
      </section>
      <section className="create-step">
        <header><span>3</span><div><h2>Visual style</h2><p>These preferences are saved for later production stages.</p></div></header>
        <VisualStyleForm form={form} onChange={updateField} artStyles={artStylePresets} captionStyles={captionStylePresets} aspectRatios={videoAspectRatioOptions} qualityOptions={videoQualityOptions} />
      </section>
      <section className="create-step">
        <header><span>4</span><div><h2>Voice and music</h2><p>Choose the intended narration and soundtrack mood.</p></div></header>
        <VoiceMusicForm form={form} onChange={updateField} voiceStyles={voiceStyles} musicPresets={musicPresets} />
      </section>
      <section className="create-step create-review-step">
        <header><span>5</span><div><h2>Review and create</h2><p>The first action queues a script only. Continue in Advanced Generator when it is ready.</p></div></header>
        <CreateReviewPanel summary={summary} />
        {externalError || error ? <p className="message error" role="alert">{externalError || error}</p> : null}
        {message ? <p className="message success" role="status">{message}</p> : null}
        <div className="create-actions">
          <button type="button" className="secondary-button" onClick={saveDraft}>Save Series Draft</button>
          <button type="button" onClick={queueFirstVideo} disabled={queueing}>{queueing ? "Queueing…" : "Queue First Video"}</button>
          <Link className="secondary-link" to="/generate">Open Advanced Generator</Link>
        </div>
      </section>
    </section>
  );
}
