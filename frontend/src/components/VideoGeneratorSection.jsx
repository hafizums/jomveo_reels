import JobProgress from "./JobProgress";
import SectionHeading from "./SectionHeading";

export default function VideoGeneratorSection({
  form,
  result,
  error,
  job,
  onCancel,
  sceneJob,
  onSceneCancel,
  hasScenes,
  hasVoiceover,
  hasMusic,
  sceneCount,
  hasAnimatedScenes,
  animatedSceneCount,
  captionStylePresets,
  durationOptions,
  aspectRatioOptions,
  onFieldChange,
  onSubmit,
}) {
  const usesAnimatedScenes = form.visual_source === "animated";
  const hasSelectedVisuals = usesAnimatedScenes ? hasAnimatedScenes : hasScenes;
  const canGenerate = hasSelectedVisuals && hasVoiceover;
  const selectedCaptionStyle =
    captionStylePresets.find((preset) => preset.id === form.caption_style_id) ??
    captionStylePresets[0];

  return (
    <section className="stack">
      <SectionHeading
        title="Video Creator"
        description="Combine still or animated scenes, voiceover, background music, and captions into one finished MP4."
      />

      <section className="workspace">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <div className="source-list">
            <p className={hasSelectedVisuals ? "source-ready" : "source-missing"}>
              {usesAnimatedScenes
                ? hasAnimatedScenes
                  ? `✓ ${animatedSceneCount} animated scene clips ready`
                  : "○ Animated scene clips required"
                : hasScenes
                  ? `✓ ${sceneCount} still scene images ready`
                  : "○ Still scene images required"}
            </p>
            <p className={hasVoiceover ? "source-ready" : "source-missing"}>
              {hasVoiceover ? "✓ Voiceover ready" : "○ Voiceover required"}
            </p>
            <p className={hasMusic ? "source-ready" : "source-optional"}>
              {hasMusic ? "✓ Background music ready" : "○ Background music optional"}
            </p>
            <p className="source-ready">✓ {selectedCaptionStyle.title} captions required</p>
          </div>

          <label>
            Visual Source
            <select name="visual_source" value={form.visual_source} onChange={onFieldChange}>
              <option value="stills">Still images with pan and zoom</option>
              <option value="animated">Wan animated scene clips</option>
            </select>
          </label>

          <label>
            Video Duration
            <select name="duration_seconds" value={form.duration_seconds} onChange={onFieldChange}>
              {durationOptions.map((duration) => (
                <option key={duration} value={duration}>{duration} seconds</option>
              ))}
            </select>
          </label>

          <label>
            Aspect Ratio
            <select name="aspect_ratio" value={form.aspect_ratio} onChange={onFieldChange}>
              {aspectRatioOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} — {option.resolution}
                </option>
              ))}
            </select>
          </label>

          <label>
            Subtitle Style
            <select name="caption_style_id" value={form.caption_style_id} onChange={onFieldChange}>
              {captionStylePresets.map((preset) => (
                <option key={preset.id} value={preset.id}>{preset.title}</option>
              ))}
            </select>
            <span className="helper-text">{selectedCaptionStyle.description}</span>
          </label>

          <label>
            Music Volume
            <input
              type="range"
              name="music_volume"
              min="0"
              max="0.5"
              step="0.01"
              value={form.music_volume}
              onChange={onFieldChange}
              disabled={!hasMusic}
            />
            <span className="helper-text">{Math.round(form.music_volume * 100)}%</span>
          </label>

          <p className="helper-text">
            The selected duration is exact. Visuals are repeated or trimmed to fill it, and the
            selected caption style is always burned in.
          </p>

          <button type="submit" disabled={!canGenerate || loading}>
            {job ? "Working..." : "Create video"}
          </button>
          {!canGenerate ? (
            <p className="message error">Generate the selected visual source and voiceover first.</p>
          ) : null}
          {error ? <p className="message error">{error}</p> : null}
        </form>

        <section className="panel result-panel video-result-panel">
          <div className="result-header">
            <h2>Final Video</h2>
            {result ? <span>{result.aspect_ratio}</span> : null}
          </div>

          {job ? <JobProgress job={job} onCancel={onCancel} /> : result ? (
            <div className="script-content">
              <video className="video-player generated-video" controls src={result.output_url}>
                Your browser does not support video playback.
              </video>
              <p className="script-event">
                {result.width} × {result.height} · {result.duration_seconds} seconds · {result.scene_count} scenes
              </p>
              <p className="script-event">Captions: Burned in</p>
              <p className="script-event">
                Visuals: {result.visual_source === "animated" ? "Animated scene clips" : "Still images"}
              </p>
              <a href={result.output_url} target="_blank" rel="noreferrer">Open final video</a>
            </div>
          ) : (
            <div className="empty-state"><p>Your assembled video will show up here.</p></div>
          )}
        </section>
      </section>
    </section>
  );
}
