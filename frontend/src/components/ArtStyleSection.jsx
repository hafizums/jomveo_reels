import ArtStylePresetPicker from "./ArtStylePresetPicker";
import SectionHeading from "./SectionHeading";

export default function ArtStyleSection({
  presets,
  modelOptions,
  selectedPresetId,
  form,
  result,
  sceneResult,
  error,
  loading,
  sceneLoading,
  hasScriptText,
  onPresetSelect,
  onUseLatestScript,
  onFieldChange,
  onSubmit,
  onSceneSubmit,
}) {
  return (
    <section className="stack">
      <SectionHeading
        title="Art Style"
        description="Generate styled visuals with Z Image Turbo using predefined art directions matched to your story niches."
      />

      <ArtStylePresetPicker
        presets={presets}
        selectedPresetId={selectedPresetId}
        onSelect={onPresetSelect}
      />

      <section className="workspace">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <label>
            Scene Prompt
            <textarea
              name="prompt"
              rows="8"
              value={form.prompt}
              onChange={onFieldChange}
              placeholder="Describe the core scene, subject, and moment you want to visualize"
              required
            />
          </label>

          <button
            type="button"
            className="secondary-button"
            onClick={onUseLatestScript}
            disabled={!hasScriptText}
          >
            Use latest script as inspiration
          </button>

          <label>
            Art Style
            <input
              name="style_name"
              value={form.style_name}
              onChange={onFieldChange}
              placeholder="Cinematic Realism"
              required
            />
          </label>

          <label>
            Art Direction
            <textarea
              name="art_direction"
              rows="6"
              value={form.art_direction}
              onChange={onFieldChange}
              placeholder="Define the visual treatment, lighting, palette, and medium"
              required
            />
          </label>

          <label>
            Model
            <select
              name="model"
              value={form.model}
              onChange={onFieldChange}
              required
            >
              {modelOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} — {option.value}
                </option>
              ))}
            </select>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              name="enable_safety_checker"
              checked={form.enable_safety_checker}
              onChange={onFieldChange}
            />
            Enable safety checker
          </label>

          <p className="helper-text">
            GPT-5.4 Mini reads the complete script, chooses the scene count, and writes a
            dedicated visual prompt for every story beat.
          </p>

          <button type="submit" disabled={loading || sceneLoading}>
            {loading ? "Generating..." : "Generate art-style image"}
          </button>

          <button
            type="button"
            className="secondary-button"
            onClick={onSceneSubmit}
            disabled={!hasScriptText || loading || sceneLoading}
          >
            {sceneLoading ? "Generating scene sequence..." : "Generate scenes from latest script"}
          </button>

          {!hasScriptText ? (
            <p className="helper-text">Generate a script to unlock scene-sequence generation.</p>
          ) : null}

          {error ? <p className="message error">{error}</p> : null}
        </form>

        <section className="panel result-panel">
          <div className="result-header">
            <h2>Art Result</h2>
            {sceneResult ? <span>{sceneResult.scene_count} scenes</span> : null}
            {!sceneResult && result ? <span>{result.style_name}</span> : null}
          </div>

          {sceneResult ? (
            <div className="scene-sequence">
              {sceneResult.scenes.map((scene) => (
                <article className="scene-card" key={scene.scene_number}>
                  <img
                    className="result-image"
                    src={scene.image_url}
                    alt={`Scene ${scene.scene_number}: ${scene.narration}`}
                  />
                  <p className="script-event">
                    Scene {scene.scene_number} of {sceneResult.scene_count}
                  </p>
                  <p>{scene.narration}</p>
                  <a href={scene.image_url} target="_blank" rel="noreferrer">
                    Open scene image
                  </a>
                  <details>
                    <summary>Image prompt</summary>
                    <p className="scene-prompt">{scene.image_prompt}</p>
                  </details>
                </article>
              ))}
            </div>
          ) : result ? (
            <div className="script-content">
              <img
                className="result-image"
                src={result.image_url}
                alt={result.prompt}
              />
              <p className="script-event">Model: {result.model}</p>
              <p className="script-event">
                Safety checker: {result.enable_safety_checker ? "Completed" : "Disabled"}
              </p>
              <p className="script-event">{result.art_direction}</p>
              <a href={result.image_url} target="_blank" rel="noreferrer">
                Open image in a new tab
              </a>
              <pre className="script-output">{result.styled_prompt}</pre>
            </div>
          ) : (
            <div className="empty-state">
              <p>Your generated image or scene sequence will show up here.</p>
            </div>
          )}
        </section>
      </section>
    </section>
  );
}
