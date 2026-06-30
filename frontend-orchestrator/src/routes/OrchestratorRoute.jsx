import { useEffect, useState } from "react";
import { backend } from "../lib/api";
import {
  buildScriptJobPayload,
  buildVoiceoverJobPayload,
  buildMusicJobPayload,
  buildSceneSequenceJobPayload,
  buildSceneAnimationJobPayload,
  buildVideoJobPayload,
} from "../lib/jobPayloads";

// Predefined option files copied from legacy workspace
import { scriptPresets, defaultScriptPreset } from "../data/scriptPresets";
import { scriptModelOptions } from "../data/scriptModels";
import { voiceStyles, defaultVoiceStyle, supportedVoiceGenders, getVoiceId } from "../data/voiceStyles";
import { GEMINI_FLASH_TTS_MODEL, voiceModelOptions } from "../data/voiceModels";
import { musicPresets, defaultMusicPreset } from "../data/musicPresets";
import { artStylePresets, defaultArtStylePreset } from "../data/artStylePresets";
import { artModelOptions } from "../data/artModels";
import { captionStylePresets, defaultCaptionStylePreset } from "../data/captionStylePresets";
import { videoAspectRatioOptions, videoDurationOptions } from "../data/videoOptions";
import { supportedLanguages } from "../data/languages";

const STEPS = [
  { num: 1, id: "script", label: "Video Script" },
  { num: 2, id: "audio", label: "Voice & Music" },
  { num: 3, id: "scenes", label: "Visual Scenes" },
  { num: 4, id: "animation", label: "Animation" },
  { num: 5, id: "video", label: "Video Assembly" },
];

export default function OrchestratorRoute({ projectId }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Background queue polling references
  const [jobs, setJobs] = useState({
    script: null,
    voice: null,
    music: null,
    scenes: null,
    animation: null,
    video: null,
  });

  // Steps output payloads
  const [results, setResults] = useState({
    script: null,
    voice: null,
    music: null,
    scenes: null,
    animation: null,
    video: null,
  });

  // Initial forms loaded from copied legacy presets
  const [forms, setForms] = useState({
    script: {
      niche: defaultScriptPreset.niche,
      style: defaultScriptPreset.style,
      topic_hint: "",
      duration_seconds: 60,
      model: "openai/gpt-5.1",
      truth_mode: defaultScriptPreset.truth_mode,
      language: "Malay",
    },
    voice: {
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
    },
    music: {
      prompt: defaultMusicPreset.prompt,
      style_name: defaultMusicPreset.title,
      number_of_songs: 1,
      output_format: "mp3",
      model: "mureka-ai/mureka-v9/generate-bgm",
    },
    art: {
      prompt: "A lone investigator studying classified files in a dim archive room",
      style_name: defaultArtStylePreset.title,
      art_direction: defaultArtStylePreset.artDirection,
      model: artModelOptions[0]?.value || "wavespeed-ai/z-image/turbo",
      enable_safety_checker: true,
    },
    animation: {
      duration: 5,
      negative_prompt: "blurry, low quality, distorted anatomy, text, logo, watermark",
    },
    video: {
      duration_seconds: 60,
      aspect_ratio: "9:16",
      music_volume: 0.16,
      caption_style_id: "hype",
      visual_source: "stills",
    },
  });

  // Monitor parallel background enqueued runs
  useEffect(() => {
    if (!projectId) return undefined;

    const activeJobIds = Object.entries(jobs)
      .filter(([_, j]) => j && !["completed", "failed", "cancelled"].includes(j.status))
      .map(([stepKey, j]) => ({ stepKey, job_id: j.job_id }));

    if (activeJobIds.length === 0) return undefined;

    const pollInterval = setInterval(async () => {
      for (const { stepKey, job_id } of activeJobIds) {
        try {
          const detail = await backend.job(job_id);
          setJobs((prev) => ({ ...prev, [stepKey]: detail }));

          if (detail.status === "completed") {
            let assets = [];
            try {
              const assetsData = await backend.jobAssets(job_id);
              assets = assetsData.assets || [];
            } catch (e) {
              console.error("Error fetching job assets:", e);
            }

            setResults((prev) => ({
              ...prev,
              [stepKey]: {
                ...detail.result,
                assets,
                audio_url: detail.result?.audio_url || assets.find(a => a.asset_type === "audio")?.url,
                video_url: detail.result?.video_url || assets.find(a => a.asset_type === "video")?.url,
              },
            }));

            // Chain automation settings downstream as steps finish
            if (stepKey === "script" && detail.result?.script) {
              setForms((prev) => ({
                ...prev,
                voice: { ...prev.voice, text: detail.result.script },
                art: {
                  ...prev.art,
                  prompt: `${detail.result.title}. Key subject and scene: ${detail.result.event_name}. Create the most visually striking moment from this story.`,
                },
                video: { ...prev.video, duration_seconds: detail.result.duration_seconds || 60 },
              }));
            } else if (stepKey === "scenes" && detail.result?.scenes) {
              setForms((prev) => ({
                ...prev,
                video: { ...prev.video, visual_source: "stills" },
              }));
            } else if (stepKey === "animation") {
              setForms((prev) => ({
                ...prev,
                video: { ...prev.video, visual_source: "animated" },
              }));
            }
          } else if (detail.status === "failed") {
            setError(`Job ${job_id} failed: ${detail.error?.message || "Internal error"}`);
          }
        } catch (err) {
          console.error("Stepper background polling error:", err);
        }
      }
    }, 4000);

    return () => clearInterval(pollInterval);
  }, [jobs, projectId]);

  // Load existing jobs on mount or project switch to restore state
  useEffect(() => {
    if (!projectId) return;

    let active = true;
    setLoading(true);
    setError("");

    const restoreProjectState = async () => {
      try {
        const data = await backend.jobs(projectId);
        if (!active) return;

        const projectJobs = data.jobs || [];

        // Sort by created_at descending (latest first)
        const sortedJobs = [...projectJobs].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );

        const latestJobs = {
          script: sortedJobs.find((j) => j.type === "script.generate"),
          voice: sortedJobs.find((j) => j.type === "voiceover.generate"),
          music: sortedJobs.find((j) => j.type === "background_music.generate"),
          scenes: sortedJobs.find((j) => j.type === "scene_sequence.generate"),
          animation: sortedJobs.find((j) => j.type === "scene_animation.generate"),
          video: sortedJobs.find((j) => j.type === "video.generate"),
        };

        // For each step, if a completed job exists, load its result and assets
        const recoveredResults = {};
        const recoveredJobs = {};

        for (const [stepKey, job] of Object.entries(latestJobs)) {
          if (!job) continue;

          recoveredJobs[stepKey] = job;

          if (job.status === "completed") {
            let assets = [];
            try {
              const assetsData = await backend.jobAssets(job.job_id);
              assets = assetsData.assets || [];
            } catch (e) {
              console.error(`Error recovering assets for job ${job.job_id}:`, e);
            }

            recoveredResults[stepKey] = {
              ...job.result,
              assets,
              audio_url: job.result?.audio_url || assets.find((a) => a.asset_type === "audio")?.url,
              video_url: job.result?.video_url || assets.find((a) => a.asset_type === "video")?.url,
            };
          }
        }

        setJobs((prev) => ({
          ...prev,
          ...recoveredJobs,
        }));

        setResults((prev) => ({
          ...prev,
          ...recoveredResults,
        }));

        // Set inputs based on latest completed results
        setForms((prev) => {
          const next = { ...prev };
          if (recoveredResults.script?.script) {
            next.voice = { ...next.voice, text: recoveredResults.script.script };
            next.art = {
              ...next.art,
              prompt: `${recoveredResults.script.title}. Key subject and scene: ${recoveredResults.script.event_name}. Create the most visually striking moment from this story.`,
            };
            next.video = { ...next.video, duration_seconds: recoveredResults.script.duration_seconds || 60 };
          }
          return next;
        });

        // Determine current step based on latest completed stage
        if (recoveredResults.video) {
          setCurrentStep(5);
        } else if (recoveredResults.animation) {
          setCurrentStep(5);
        } else if (recoveredResults.scenes) {
          setCurrentStep(4);
        } else if (recoveredResults.voice && recoveredResults.music) {
          setCurrentStep(3);
        } else if (recoveredResults.script) {
          setCurrentStep(2);
        } else {
          setCurrentStep(1);
        }
      } catch (err) {
        if (active) setError("Failed to restore project state: " + err.message);
      } finally {
        if (active) setLoading(false);
      }
    };

    restoreProjectState();

    return () => {
      active = false;
    };
  }, [projectId]);

  if (!projectId) {
    return (
      <div className="empty-state">
        <p>Please select a project workspace to begin video orchestration.</p>
      </div>
    );
  }

  const updateFormField = (step, field, value) => {
    setForms((prev) => ({
      ...prev,
      [step]: {
        ...prev[step],
        [field]: value,
      },
    }));
  };

  // Steppers executers enqueuers
  const executeScript = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = buildScriptJobPayload(forms.script);
      const accepted = await backend.createJob("scripts", payload, projectId);
      setJobs((prev) => ({ ...prev, script: accepted }));
      setResults((prev) => ({ ...prev, script: null }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const executeAudio = async () => {
    setLoading(true);
    setError("");
    try {
      const voicePayload = buildVoiceoverJobPayload(forms.voice);
      const musicPayload = buildMusicJobPayload(forms.music);

      if (!voicePayload) {
        throw new Error("Voiceover narration text cannot be empty.");
      }

      const voiceAccepted = await backend.createJob("voiceovers", voicePayload, projectId);
      const musicAccepted = await backend.createJob("background-music", musicPayload, projectId);

      setJobs((prev) => ({ ...prev, voice: voiceAccepted, music: musicAccepted }));
      setResults((prev) => ({ ...prev, voice: null, music: null }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const executeScenes = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = buildSceneSequenceJobPayload({
        scriptResult: results.script,
        artForm: forms.art,
      });

      if (!payload) {
        throw new Error("Complete a script write job first.");
      }

      const accepted = await backend.createJob("art-style/scenes", payload, projectId);
      setJobs((prev) => ({ ...prev, scenes: accepted }));
      setResults((prev) => ({ ...prev, scenes: null }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const executeAnimation = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = buildSceneAnimationJobPayload({
        artSceneResult: results.scenes,
        sceneAnimationForm: forms.animation,
      });

      if (!payload) {
        throw new Error("Complete scene sequencing first.");
      }

      const accepted = await backend.createJob("scene-animations", payload, projectId);
      setJobs((prev) => ({ ...prev, animation: accepted }));
      setResults((prev) => ({ ...prev, animation: null }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const executeVideo = async () => {
    setLoading(true);
    setError("");
    try {
      const payload = buildVideoJobPayload({
        scriptResult: results.script,
        artSceneResult: results.scenes,
        sceneAnimationResult: results.animation,
        voiceResult: results.voice,
        musicResult: results.music,
        videoForm: forms.video,
        captionStylePresets: captionStylePresets,
        defaultCaptionStylePreset: defaultCaptionStylePreset,
      });

      if (!payload) {
        throw new Error("Ensure script, voice narration, and visual layouts are fully prepared before assembly.");
      }

      const accepted = await backend.createJob("videos", payload, projectId);
      setJobs((prev) => ({ ...prev, video: accepted }));
      setResults((prev) => ({ ...prev, video: null }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stepper-step-container">
      {/* Visual Stepper Nodes */}
      <div className="stepper-nodes">
        {STEPS.map((step) => {
          const isCurrent = currentStep === step.num;
          let isCompleted = false;

          if (step.id === "script") isCompleted = !!results.script;
          else if (step.id === "audio") isCompleted = results.voice && results.music;
          else if (step.id === "scenes") isCompleted = !!results.scenes;
          else if (step.id === "animation") isCompleted = !!results.animation;
          else if (step.id === "video") isCompleted = !!results.video;

          return (
            <div
              key={step.id}
              className={`stepper-node ${isCurrent ? "active" : ""} ${isCompleted ? "completed" : ""}`}
              onClick={() => {
                const canGo =
                  step.num <= currentStep ||
                  (step.num === 2 && results.script) ||
                  (step.num === 3 && results.voice && results.music) ||
                  (step.num === 4 && results.scenes) ||
                  (step.num === 5 && results.scenes && results.voice && results.music);

                if (canGo) {
                  setCurrentStep(step.num);
                }
              }}
            >
              <div className="node-circle">{step.num}</div>
              <span className="node-label">{step.label}</span>
            </div>
          );
        })}
      </div>

      {error && <div className="message error" style={{ marginBottom: 20 }}>{error}</div>}

      {/* STEP 1: SCRIPT GENERATION */}
      {currentStep === 1 && (
        <div className="dashboard-card">
          <h2>Step 1: Write Video Script</h2>
          <p style={{ marginBottom: 20 }}>Describe your niche, style preferences, and story hint to write a text script.</p>

          <div className="grid-cols-2">
            <div>
              {/* Presets dropdown */}
              <div className="form-group">
                <label>Story Preset Selection</label>
                <select
                  onChange={(e) => {
                    const preset = scriptPresets.find((p) => p.id === e.target.value);
                    if (preset) {
                      setForms((prev) => ({
                        ...prev,
                        script: {
                          ...prev.script,
                          niche: preset.niche,
                          style: preset.style,
                          truth_mode: preset.truth_mode,
                        },
                      }));
                    }
                  }}
                >
                  <option value="">-- Custom Story Niche --</option>
                  {scriptPresets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Script Niche</label>
                <input
                  type="text"
                  value={forms.script.niche}
                  onChange={(e) => updateFormField("script", "niche", e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Style Mode</label>
                <input
                  type="text"
                  value={forms.script.style}
                  onChange={(e) => updateFormField("script", "style", e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Topic / Plot Hints</label>
                <textarea
                  rows="2"
                  value={forms.script.topic_hint}
                  onChange={(e) => updateFormField("script", "topic_hint", e.target.value)}
                />
              </div>

              <div className="grid-cols-3" style={{ gap: 10 }}>
                <div className="form-group">
                  <label>Duration</label>
                  <select
                    value={forms.script.duration_seconds}
                    onChange={(e) => updateFormField("script", "duration_seconds", Number(e.target.value))}
                  >
                    <option value={15}>15s</option>
                    <option value={30}>30s</option>
                    <option value={60}>60s</option>
                    <option value={90}>90s</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Language</label>
                  <select
                    value={forms.script.language}
                    onChange={(e) => updateFormField("script", "language", e.target.value)}
                  >
                    {supportedLanguages.map((lang) => (
                      <option key={lang.value} value={lang.value}>
                        {lang.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Planner Model</label>
                  <select
                    value={forms.script.model}
                    onChange={(e) => updateFormField("script", "model", e.target.value)}
                  >
                    {scriptModelOptions.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="button"
                className="btn-primary"
                disabled={loading || (jobs.script && !["completed", "failed", "cancelled"].includes(jobs.script.status))}
                onClick={executeScript}
                style={{ marginTop: 10 }}
              >
                {jobs.script && !["completed", "failed", "cancelled"].includes(jobs.script.status) ? (
                  <>
                    <div className="spinner" /> Generating ({jobs.script.status})...
                  </>
                ) : (
                  "Generate Script"
                )}
              </button>
            </div>

            {/* Output view */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <h3>Script Output</h3>
              {results.script ? (
                <div style={{ background: "var(--color-surface-2)", padding: 18, borderRadius: 12, border: "1px solid var(--color-border)" }}>
                  <h4 style={{ color: "var(--accent-violet)" }}>{results.script.title}</h4>
                  <p style={{ fontSize: 12, margin: "4px 0 12px" }}>Niche Event: <strong>{results.script.event_name}</strong></p>
                  <pre style={{ whiteSpace: "pre-wrap", maxHeight: 320, overflowY: "auto", fontSize: 13, color: "#cbd5e1", lineHeight: 1.6 }}>
                    {results.script.script}
                  </pre>
                </div>
              ) : jobs.script ? (
                <div className="empty-state">
                  <div className="spinner" style={{ width: 28, height: 28, color: "var(--accent-violet)" }} />
                  <p style={{ marginTop: 10 }}>Running background script generation job...</p>
                  <small>Job: {jobs.script.job_id} ({jobs.script.progress_current}/{jobs.script.progress_total})</small>
                </div>
              ) : (
                <div className="empty-state">
                  <p>Execute Step to write script.</p>
                </div>
              )}
            </div>
          </div>

          <div className="step-actions-row">
            <span style={{ fontSize: 12, color: "#6b7280" }}>Step 1 of 5</span>
            <button
              type="button"
              className="btn-primary"
              disabled={!results.script}
              onClick={() => setCurrentStep(2)}
            >
              Next: Prepare Audio →
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: VOICE & MUSIC */}
      {currentStep === 2 && (
        <div className="dashboard-card">
          <h2>Step 2: Generate Voiceover & Background Music</h2>
          <p style={{ marginBottom: 20 }}>Simultaneously queue voice narrations and custom instrumentals.</p>

          <div className="grid-cols-2" style={{ marginBottom: 20 }}>
            {/* Voice Settings */}
            <div style={{ borderRight: "1px solid var(--color-border)", paddingRight: 20 }}>
              <h3>Voiceover Settings</h3>
              
              <div className="form-group">
                <label>Voiceover Text</label>
                <textarea
                  rows="4"
                  value={forms.voice.text}
                  onChange={(e) => updateFormField("voice", "text", e.target.value)}
                />
              </div>

              <div className="grid-cols-2">
                <div className="form-group">
                  <label>Voice Style Selector</label>
                  <select
                    value={forms.voice.style_name}
                    onChange={(e) => {
                      const style = voiceStyles.find(s => s.name === e.target.value) || defaultVoiceStyle;
                      setForms(prev => {
                        const voice = { ...prev.voice, style_name: style.name };
                        if (voice.model !== GEMINI_FLASH_TTS_MODEL) {
                          voice.voice_id = getVoiceId(style, voice.gender);
                        }
                        return { ...prev, voice };
                      });
                    }}
                  >
                    {voiceStyles.map((item) => (
                      <option key={item.id} value={item.name}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Voice Gender</label>
                  <select
                    value={forms.voice.gender}
                    onChange={(e) => {
                      const gender = e.target.value;
                      setForms(prev => {
                        const voice = { ...prev.voice, gender };
                        if (voice.model !== GEMINI_FLASH_TTS_MODEL) {
                          const style = voiceStyles.find(s => s.name === voice.style_name) || defaultVoiceStyle;
                          voice.voice_id = getVoiceId(style, gender);
                        }
                        return { ...prev, voice };
                      });
                    }}
                  >
                    {supportedVoiceGenders.map((g) => (
                      <option key={g.value} value={g.value}>
                        {g.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>TTS Model Configuration</label>
                <select
                  value={forms.voice.model}
                  onChange={(e) => {
                    const model = e.target.value;
                    setForms(prev => {
                      const voice = { ...prev.voice, model };
                      if (model === GEMINI_FLASH_TTS_MODEL) {
                        voice.voice_id = "Achernar";
                        voice.language = "English (United States)";
                        voice.style_name = "Gemini Narrator";
                      } else {
                        const style = voiceStyles.find(s => s.id === defaultVoiceStyle.id);
                        voice.voice_id = getVoiceId(style, voice.gender);
                        voice.language = "English";
                        voice.style_name = style.name;
                      }
                      return { ...prev, voice };
                    });
                  }}
                >
                  {voiceModelOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Music Settings */}
            <div style={{ paddingLeft: 10 }}>
              <h3>Music Prompt</h3>

              <div className="form-group">
                <label>Theme Selection Preset</label>
                <select
                  onChange={(e) => {
                    const preset = musicPresets.find((p) => p.id === e.target.value);
                    if (preset) {
                      setForms((prev) => ({
                        ...prev,
                        music: {
                          ...prev.music,
                          prompt: preset.prompt,
                          style_name: preset.title,
                        },
                      }));
                    }
                  }}
                >
                  <option value="">-- Custom Prompt --</option>
                  {musicPresets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Instrumental Prompt</label>
                <textarea
                  rows="4"
                  value={forms.music.prompt}
                  onChange={(e) => updateFormField("music", "prompt", e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Music Generator Model</label>
                <select
                  value={forms.music.model}
                  onChange={(e) => updateFormField("music", "model", e.target.value)}
                >
                  <option value="mureka-ai/mureka-v9/generate-bgm">Mureka V9 BGM</option>
                </select>
              </div>
            </div>
          </div>

          <div style={{ display: "grid", placeItems: "center", marginBottom: 20 }}>
            <button
              type="button"
              className="btn-primary"
              disabled={
                loading ||
                (jobs.voice && !["completed", "failed", "cancelled"].includes(jobs.voice.status)) ||
                (jobs.music && !["completed", "failed", "cancelled"].includes(jobs.music.status))
              }
              onClick={executeAudio}
            >
              {((jobs.voice && !["completed", "failed", "cancelled"].includes(jobs.voice.status)) ||
                (jobs.music && !["completed", "failed", "cancelled"].includes(jobs.music.status))) ? (
                <>
                  <div className="spinner" /> Generating parallel Audio files...
                </>
              ) : (
                "Execute Audio Generation"
              )}
            </button>
          </div>

          {/* Previews output */}
          <div className="grid-cols-2">
            <div>
              <h4>Voiceover Audio</h4>
              {results.voice?.audio_url ? (
                <div className="audio-preview-row">
                  <audio src={results.voice.audio_url} controls className="audio-player-custom" />
                </div>
              ) : jobs.voice ? (
                <div className="empty-state" style={{ minHeight: 120 }}>
                  <div className="spinner" />
                  <p>Generating voice narration... ({jobs.voice.status})</p>
                </div>
              ) : (
                <div className="empty-state" style={{ minHeight: 120 }}>
                  <p>Voice narration not enqueued.</p>
                </div>
              )}
            </div>

            <div>
              <h4>Background Music</h4>
              {results.music?.audio_urls?.[0] ? (
                <div className="audio-preview-row">
                  <audio src={results.music.audio_urls[0]} controls className="audio-player-custom" />
                </div>
              ) : jobs.music ? (
                <div className="empty-state" style={{ minHeight: 120 }}>
                  <div className="spinner" />
                  <p>Generating background music... ({jobs.music.status})</p>
                </div>
              ) : (
                <div className="empty-state" style={{ minHeight: 120 }}>
                  <p>Music track not enqueued.</p>
                </div>
              )}
            </div>
          </div>

          <div className="step-actions-row">
            <button type="button" className="btn-secondary" onClick={() => setCurrentStep(1)}>
              ← Back to Script
            </button>
            <span style={{ fontSize: 12, color: "#6b7280" }}>Step 2 of 5</span>
            <button
              type="button"
              className="btn-primary"
              disabled={!results.voice || !results.music}
              onClick={() => setCurrentStep(3)}
            >
              Next: Generate Scenes →
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: VISUAL SCENES */}
      {currentStep === 3 && (
        <div className="dashboard-card">
          <h2>Step 3: Design Art Scenes Sequence</h2>
          <p style={{ marginBottom: 20 }}>Generate image templates for each sequence scene mapping your video script.</p>

          <div className="grid-cols-2">
            <div>
              {/* Presets dropdown */}
              <div className="form-group">
                <label>Art Style Preset</label>
                <select
                  onChange={(e) => {
                    const preset = artStylePresets.find((p) => p.id === e.target.value);
                    if (preset) {
                      setForms((prev) => ({
                        ...prev,
                        art: {
                          ...prev.art,
                          style_name: preset.title,
                          art_direction: preset.artDirection,
                        },
                      }));
                    }
                  }}
                >
                  <option value="">-- Custom Art Style --</option>
                  {artStylePresets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Art Scene Prompt</label>
                <textarea
                  rows="3"
                  value={forms.art.prompt}
                  onChange={(e) => updateFormField("art", "prompt", e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Style Mode Details</label>
                <input
                  type="text"
                  value={forms.art.style_name}
                  onChange={(e) => updateFormField("art", "style_name", e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Art Generation Model</label>
                <select
                  value={forms.art.model}
                  onChange={(e) => updateFormField("art", "model", e.target.value)}
                >
                  {artModelOptions.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                className="btn-primary"
                disabled={loading || (jobs.scenes && !["completed", "failed", "cancelled"].includes(jobs.scenes.status))}
                onClick={executeScenes}
                style={{ marginTop: 10 }}
              >
                {jobs.scenes && !["completed", "failed", "cancelled"].includes(jobs.scenes.status) ? (
                  <>
                    <div className="spinner" /> Generating sequence...
                  </>
                ) : (
                  "Execute Scene Generation"
                )}
              </button>
            </div>

            {/* Scenes grid preview */}
            <div>
              <h3>Scene Previews</h3>
              {results.scenes?.scenes ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10, maxHeight: 380, overflowY: "auto" }}>
                  {results.scenes.scenes.map((scene) => (
                    <div key={scene.scene_number} style={{ background: "var(--color-surface-2)", padding: 8, borderRadius: 8 }}>
                      <img src={scene.image_url} alt={`Scene ${scene.scene_number}`} className="asset-preview-thumb" />
                      <p style={{ fontSize: 11, fontWeight: 700, marginTop: 4 }}>Scene {scene.scene_number}</p>
                      <p style={{ fontSize: 10, color: "#6b7280", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {scene.narration}
                      </p>
                    </div>
                  ))}
                </div>
              ) : jobs.scenes ? (
                <div className="empty-state">
                  <div className="spinner" />
                  <p>Planning scenes and generating image style templates... ({jobs.scenes.status})</p>
                </div>
              ) : (
                <div className="empty-state">
                  <p>Execute Step to design scenes.</p>
                </div>
              )}
            </div>
          </div>

          <div className="step-actions-row">
            <button type="button" className="btn-secondary" onClick={() => setCurrentStep(2)}>
              ← Back to Audio
            </button>
            <span style={{ fontSize: 12, color: "#6b7280" }}>Step 3 of 5</span>
            <div style={{ display: "flex", gap: 10 }}>
              <button
                type="button"
                className="btn-secondary"
                disabled={!results.scenes}
                onClick={() => setCurrentStep(5)}
              >
                Skip to Video Assembly ➔
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={!results.scenes}
                onClick={() => setCurrentStep(4)}
              >
                Next: Animate Scenes →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 4: ANIMATION */}
      {currentStep === 4 && (
        <div className="dashboard-card">
          <h2>Step 4: Scene Animation Clipart</h2>
          <p style={{ marginBottom: 20 }}>Animate static image scenes using motion vector algorithms.</p>

          <div className="grid-cols-2">
            <div>
              <div className="form-group">
                <label>Negative Prompt</label>
                <textarea
                  rows="3"
                  value={forms.animation.negative_prompt}
                  onChange={(e) => updateFormField("animation", "negative_prompt", e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Motion Duration (Seconds)</label>
                <select
                  value={forms.animation.duration}
                  onChange={(e) => updateFormField("animation", "duration", Number(e.target.value))}
                >
                  <option value={4}>4s</option>
                  <option value={5}>5s</option>
                  <option value={8}>8s</option>
                </select>
              </div>

              <button
                type="button"
                className="btn-primary"
                disabled={loading || (jobs.animation && !["completed", "failed", "cancelled"].includes(jobs.animation.status))}
                onClick={executeAnimation}
                style={{ marginTop: 10 }}
              >
                {jobs.animation && !["completed", "failed", "cancelled"].includes(jobs.animation.status) ? (
                  <>
                    <div className="spinner" /> Animating clips...
                  </>
                ) : (
                  "Execute Animation"
                )}
              </button>
            </div>

            {/* Animations output view */}
            <div>
              <h3>Animated Scene Clips</h3>
              {results.animation?.scenes ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10, maxHeight: 380, overflowY: "auto" }}>
                  {results.animation.scenes.map((scene) => (
                    <div key={scene.scene_number} style={{ background: "var(--color-surface-2)", padding: 8, borderRadius: 8 }}>
                      <video src={scene.video_url} controls className="asset-preview-thumb" style={{ objectFit: "contain" }} />
                      <p style={{ fontSize: 11, fontWeight: 700, marginTop: 4 }}>Clip {scene.scene_number}</p>
                    </div>
                  ))}
                </div>
              ) : jobs.animation ? (
                <div className="empty-state">
                  <div className="spinner" />
                  <p>Generating motion videos from scenes... ({jobs.animation.status})</p>
                </div>
              ) : (
                <div className="empty-state">
                  <p>Execute Step to animate frames.</p>
                </div>
              )}
            </div>
          </div>

          <div className="step-actions-row">
            <button type="button" className="btn-secondary" onClick={() => setCurrentStep(3)}>
              ← Back to Scenes
            </button>
            <span style={{ fontSize: 12, color: "#6b7280" }}>Step 4 of 5</span>
            <button
              type="button"
              className="btn-primary"
              onClick={() => setCurrentStep(5)}
            >
              Skip / Next: Assemble Video →
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: VIDEO ASSEMBLY */}
      {currentStep === 5 && (
        <div className="dashboard-card">
          <h2>Step 5: Assemble Final Video</h2>
          <p style={{ marginBottom: 20 }}>Combine visual clips, voiceover, BGM track, and styled subtitles into a final video.</p>

          <div className="grid-cols-2">
            <div>
              <div className="form-group">
                <label>Aspect Ratio</label>
                <select
                  value={forms.video.aspect_ratio}
                  onChange={(e) => updateFormField("video", "aspect_ratio", e.target.value)}
                >
                  {videoAspectRatioOptions.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label} ({r.resolution})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Visual Source</label>
                <select
                  value={forms.video.visual_source}
                  onChange={(e) => updateFormField("video", "visual_source", e.target.value)}
                >
                  <option value="stills">Static Artwork Scenes (Fast)</option>
                  <option value="animated" disabled={!results.animation}>
                    Animated Art Clips (Dynamic)
                  </option>
                </select>
              </div>

              <div className="form-group">
                <label>Background Music Volume</label>
                <input
                  type="range"
                  min="0"
                  max="0.5"
                  step="0.05"
                  value={forms.video.music_volume}
                  onChange={(e) => updateFormField("video", "music_volume", Number(e.target.value))}
                />
                <span style={{ fontSize: 11, color: "#9ca3af" }}>{(forms.video.music_volume * 100).toFixed(0)}%</span>
              </div>

              <div className="form-group">
                <label>Subtitles Caption Style</label>
                <select
                  value={forms.video.caption_style_id}
                  onChange={(e) => updateFormField("video", "caption_style_id", e.target.value)}
                >
                  {captionStylePresets.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Video Duration Limit</label>
                <select
                  value={forms.video.duration_seconds}
                  onChange={(e) => updateFormField("video", "duration_seconds", Number(e.target.value))}
                >
                  {videoDurationOptions.map((d) => (
                    <option key={d} value={d}>
                      {d}s
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                className="btn-primary"
                disabled={loading || (jobs.video && !["completed", "failed", "cancelled"].includes(jobs.video.status))}
                onClick={executeVideo}
                style={{ marginTop: 10 }}
              >
                {jobs.video && !["completed", "failed", "cancelled"].includes(jobs.video.status) ? (
                  <>
                    <div className="spinner" /> Assembling video...
                  </>
                ) : (
                  "Assemble Final Video"
                )}
              </button>
            </div>

            {/* Assembly output view */}
            <div>
              <h3>Final Assembly Preview</h3>
              {results.video?.video_url ? (
                <div style={{ textAlign: "center" }}>
                  <video src={results.video.video_url} controls className="video-preview-large" />
                  <a
                    href={results.video.video_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-primary"
                    style={{ marginTop: 14, width: "100%" }}
                    download
                  >
                    Download Finished Video
                  </a>
                </div>
              ) : jobs.video ? (
                <div className="empty-state">
                  <div className="spinner" />
                  <p>Rendering timelines and burning subtitles... ({jobs.video.status})</p>
                  <small>Usually completes within 30-45 seconds</small>
                </div>
              ) : (
                <div className="empty-state">
                  <p>Execute Step to assemble components.</p>
                </div>
              )}
            </div>
          </div>

          <div className="step-actions-row">
            <button type="button" className="btn-secondary" onClick={() => setCurrentStep(4)}>
              ← Back to Animation
            </button>
            <span style={{ fontSize: 12, color: "#6b7280" }}>Step 5 of 5</span>
            <span style={{ color: "var(--accent-emerald)", fontWeight: 700, fontSize: 13 }}>
              {results.video ? "🏁 Video Ready!" : "Pipeline Ready"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
