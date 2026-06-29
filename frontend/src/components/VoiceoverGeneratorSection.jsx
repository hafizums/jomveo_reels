import JobProgress from "./JobProgress";
import SectionHeading from "./SectionHeading";
import VoiceStylePicker from "./VoiceStylePicker";

export default function VoiceoverGeneratorSection({
  styles,
  selectedStyleId,
  selectedStyle,
  form,
  result,
  error,
  job,
  onCancel,
  sceneJob,
  onSceneCancel,
  hasScriptText,
  supportedVoiceGenders,
  modelOptions,
  geminiVoiceOptions,
  geminiLanguageOptions,
  geminiModel,
  onStyleSelect,
  onUseLatestScript,
  onFieldChange,
  onSubmit,
}) {
  const isGemini = form.model === geminiModel;

  return (
    <section className="stack">
      <SectionHeading
        title="Voiceover Generator"
        description="Turn your script into narration with ElevenLabs or Gemini 2.5 Flash TTS on WaveSpeed."
      />

      {!isGemini ? (
        <VoiceStylePicker
          styles={styles}
          selectedStyleId={selectedStyleId}
          onSelect={onStyleSelect}
        />
      ) : null}

      <section className="workspace">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <label>
            Voiceover Text
            <textarea
              name="text"
              rows="10"
              value={form.text}
              onChange={onFieldChange}
              placeholder="Paste a script here or pull in the latest generated script."
              required
            />
          </label>

          <button
            type="button"
            className="secondary-button"
            onClick={onUseLatestScript}
            disabled={!hasScriptText}
          >
            Use latest script
          </button>

          <label>
            Voice Model
            <select name="model" value={form.model} onChange={onFieldChange}>
              {modelOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {isGemini ? (
            <>
              <p className="helper-text">
                Gemini uses one named speaker, a Gemini voice, and an exact language locale.
              </p>
              <label>
                Language
                <select name="language" value={form.language} onChange={onFieldChange}>
                  {geminiLanguageOptions.map((language) => (
                    <option key={language} value={language}>{language}</option>
                  ))}
                </select>
              </label>
              <label>
                Speaker Name
                <input name="speaker_name" value={form.speaker_name} onChange={onFieldChange} required />
              </label>
              <label>
                Gemini Voice
                <select name="voice_id" value={form.voice_id} onChange={onFieldChange}>
                  {geminiVoiceOptions.map((voice) => (
                    <option key={voice} value={voice}>{voice}</option>
                  ))}
                </select>
              </label>
            </>
          ) : (
            <>
              <p className="helper-text">
                ElevenLabs uses a valid voice ID plus optional similarity and stability controls.
              </p>
              <label>
                Gender
                <select name="gender" value={form.gender} onChange={onFieldChange}>
                  {supportedVoiceGenders.map((gender) => (
                    <option key={gender.value} value={gender.value}>{gender.label}</option>
                  ))}
                </select>
              </label>

              <label>
                Style Name
                <input name="style_name" value={form.style_name} onChange={onFieldChange} required />
              </label>

              <label>
                Voice ID
                <input name="voice_id" value={form.voice_id} onChange={onFieldChange} required />
              </label>

              <label>
                Similarity
                <input name="similarity" type="number" min="0" max="1" step="0.01" value={form.similarity} onChange={onFieldChange} required />
              </label>

              <label>
                Stability
                <input name="stability" type="number" min="0" max="1" step="0.01" value={form.stability} onChange={onFieldChange} required />
              </label>

              <label className="checkbox-label">
                <input name="use_speaker_boost" type="checkbox" checked={form.use_speaker_boost} onChange={onFieldChange} />
                <span>Use Speaker Boost</span>
              </label>
            </>
          )}

          <button type="submit" disabled={!!job}>
            {job ? "Working..." : "Generate voiceover"}
          </button>

          {error ? <p className="message error">{error}</p> : null}
        </form>

        <section className="panel result-panel voice-panel">
          <div className="result-header">
            <h2>Voiceover Result</h2>
            {result ? <span>{result.style_name}</span> : null}
          </div>

          {job ? <JobProgress job={job} onCancel={onCancel} /> : result ? (
            <div className="script-content">
              <p className="script-event">Model: {result.model}</p>
              {result.model === geminiModel ? (
                <>
                  <p className="script-event">Language: {result.language}</p>
                  <p className="script-event">Speaker: {result.speaker_name}</p>
                </>
              ) : (
                <p className="script-event">Gender: {result.gender}</p>
              )}
              <p className="script-event">Voice ID: {result.voice_id}</p>
              {result.model !== geminiModel ? (
                <>
                  <p className="script-event">Similarity: {result.similarity} | Stability: {result.stability}</p>
                  <p className="script-event">Speaker Boost: {result.use_speaker_boost ? "On" : "Off"}</p>
                </>
              ) : null}
              <audio className="audio-player" controls src={result.audio_url}>
                Your browser does not support audio playback.
              </audio>
              <a href={result.audio_url} target="_blank" rel="noreferrer">
                Open audio in a new tab
              </a>
              <pre className="script-output">{result.text}</pre>
            </div>
          ) : (
            <div className="empty-state">
              <p>Your generated voiceover will show up here.</p>
            </div>
          )}
        </section>
      </section>
    </section>
  );
}
