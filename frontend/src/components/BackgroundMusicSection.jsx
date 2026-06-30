import MusicPresetPicker from "./MusicPresetPicker";
import ProjectActionCard from "./ProjectActionCard";
import SectionHeading from "./SectionHeading";

export default function BackgroundMusicSection({
  presets,
  selectedPresetId,
  form,
  result,
  error,
  loading,
  hasScriptText,
  variantOptions,
  onPresetSelect,
  onUseLatestScript,
  onFieldChange,
  onSubmit,
  onQueue,
  queueLoading,
  queueMessage,
  queueError,
}) {
  return (
    <section className="stack">
      <SectionHeading
        title="Background Music"
        description="Generate original non-vocal background tracks with presets tuned for shorts, documentaries, and storytelling."
      />

      <MusicPresetPicker
        presets={presets}
        selectedPresetId={selectedPresetId}
        onSelect={onPresetSelect}
      />

      <section className="workspace">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <label>
            Music Prompt
            <textarea
              name="prompt"
              rows="8"
              value={form.prompt}
              onChange={onFieldChange}
              placeholder="Describe the mood, instruments, pacing, and atmosphere"
              required
            />
          </label>

          <button
            type="button"
            className="secondary-button"
            onClick={onUseLatestScript}
            disabled={!hasScriptText}
          >
            ↑ Use latest script as inspiration
          </button>

          <p className="helper-text">
            These presets are written for original non-vocal background music. Review
            platform and licensing terms before commercial use.
          </p>

          <label>
            Style Name
            <input
              name="style_name"
              value={form.style_name}
              onChange={onFieldChange}
              placeholder="Dark Documentary"
              required
            />
          </label>

          <label>
            Variants
            <select
              name="number_of_songs"
              value={form.number_of_songs}
              onChange={onFieldChange}
            >
              {variantOptions.map((count) => (
                <option key={count} value={count}>
                  {count} variation{count > 1 ? "s" : ""}
                </option>
              ))}
            </select>
          </label>

          <label>
            Output Format
            <input
              name="output_format"
              value={form.output_format}
              onChange={onFieldChange}
              placeholder="mp3"
              required
            />
          </label>

          <label>
            Model
            <input
              name="model"
              value={form.model}
              onChange={onFieldChange}
              placeholder="mureka-ai/mureka-v9/generate-bgm"
              required
            />
          </label>

          <button type="submit" disabled={loading}>
            {loading ? "Generating…" : "Generate background music"}
          </button>

          {error ? <p className="message error">{error}</p> : null}

          <ProjectActionCard
            label="Save music job to project"
            onQueue={onQueue}
            loading={queueLoading}
            message={queueMessage}
            error={queueError}
          />
        </form>

        <section className="panel result-panel music-panel">
          <div className="result-header">
            <h2>Music Result</h2>
            {result ? <span>{result.style_name}</span> : null}
          </div>

          {result ? (
            <div className="script-content">
              <p className="script-event">Model: {result.model}</p>
              {result.audio_urls.map((audioUrl, index) => (
                <div key={audioUrl} className="audio-block">
                  <p className="script-event">Variation {index + 1}</p>
                  <audio className="audio-player" controls src={audioUrl}>
                    Your browser does not support audio playback.
                  </audio>
                  <a href={audioUrl} target="_blank" rel="noreferrer">
                    Open audio variation {index + 1}
                  </a>
                </div>
              ))}
              <pre className="script-output">{result.prompt}</pre>
            </div>
          ) : (
            <div className="empty-state">
              <p>Your generated background music will show up here.</p>
            </div>
          )}
        </section>
      </section>
    </section>
  );
}
