import ProjectActionCard from "./ProjectActionCard";
import ScriptPresetPicker from "./ScriptPresetPicker";
import SectionHeading from "./SectionHeading";

export default function ScriptGeneratorSection({
  presets,
  selectedPresetId,
  selectedPreset,
  form,
  result,
  error,
  loading,
  supportedLanguages,
  durationOptions,
  modelOptions,
  onPresetSelect,
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
        title="60-Second Script Generator"
        description="Choose a preset below, then refine the framework before generating your script."
      />

      <ScriptPresetPicker
        presets={presets}
        selectedPresetId={selectedPresetId}
        onSelect={onPresetSelect}
      />

      <section className="workspace">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <label>
            Niche
            <textarea
              name="niche"
              rows="9"
              value={form.niche}
              onChange={onFieldChange}
              placeholder="Describe the content niche and guardrails"
              required
            />
          </label>

          <label>
            Style
            <input
              name="style"
              value={form.style}
              onChange={onFieldChange}
              placeholder="Storytelling"
              required
            />
          </label>

          <label>
            Topic Hint
            <input
              name="topic_hint"
              value={form.topic_hint}
              onChange={onFieldChange}
              placeholder={selectedPreset.topic_placeholder}
            />
          </label>

          <label>
            Language
            <select name="language" value={form.language} onChange={onFieldChange}>
              {supportedLanguages.map((language) => (
                <option key={language.value} value={language.value}>
                  {language.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Duration
            <select
              name="duration_seconds"
              value={form.duration_seconds}
              onChange={onFieldChange}
            >
              {durationOptions.map((seconds) => (
                <option key={seconds} value={seconds}>
                  {seconds} seconds
                </option>
              ))}
            </select>
          </label>

          <label>
            Model
            <select name="model" value={form.model} onChange={onFieldChange}>
              {modelOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} — {option.value}
                </option>
              ))}
            </select>
          </label>

          <label>
            Truth Mode
            <input
              name="truth_mode"
              value={form.truth_mode}
              onChange={onFieldChange}
              placeholder="factual"
              required
            />
          </label>

          {/* Primary action: synchronous preview */}
          <button type="submit" disabled={loading}>
            {loading ? "Writing…" : "Generate script"}
          </button>

          {error ? <p className="message error">{error}</p> : null}

          {/* Secondary action: async project job */}
          <ProjectActionCard
            label="Save script to project"
            onQueue={onQueue}
            loading={queueLoading}
            message={queueMessage}
            error={queueError}
          />
        </form>

        <section className="panel result-panel script-panel">
          <div className="result-header">
            <h2>Script Result</h2>
            {result ? <span>{result.model}</span> : null}
          </div>

          {result ? (
            <div className="script-content">
              <h3>{result.title}</h3>
              <p className="script-event">{result.event_name}</p>
              <p className="script-event">Language: {result.language}</p>
              <pre className="script-output">{result.script}</pre>
              <div className="fact-box">
                <strong>Framework note</strong>
                <p>{result.factual_basis}</p>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Your script will appear here after generation.</p>
            </div>
          )}
        </section>
      </section>
    </section>
  );
}
