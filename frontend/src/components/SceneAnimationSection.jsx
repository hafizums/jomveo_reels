import JobProgress from "./JobProgress";
import SectionHeading from "./SectionHeading";

export default function SceneAnimationSection({
  form,
  result,
  error,
  job,
  onCancel,
  sceneJob,
  onSceneCancel,
  hasScenes,
  sceneCount,
  onFieldChange,
  onSubmit,
}) {
  return (
    <section className="stack">
      <SectionHeading
        title="Animate Scenes"
        description="Turn each generated scene image into a short motion clip with Wan 2.2 I2V 480P Ultra Fast."
      />

      <section className="workspace">
        <form className="panel form-panel" onSubmit={onSubmit}>
          <div className="source-list">
            <p className={hasScenes ? "source-ready" : "source-missing"}>
              {hasScenes ? `✓ ${sceneCount} scene images ready` : "○ Generate an art scene sequence first"}
            </p>
          </div>

          <label>
            Clip Duration
            <select name="duration" value={form.duration} onChange={onFieldChange}>
              <option value="5">5 seconds per scene</option>
              <option value="8">8 seconds per scene</option>
            </select>
          </label>

          <label>
            Negative Prompt
            <textarea
              name="negative_prompt"
              rows="5"
              value={form.negative_prompt}
              onChange={onFieldChange}
            />
          </label>

          <p className="helper-text">
            Only each scene image is supplied as the start frame. No final frame is sent.
            WaveSpeed lists pricing at $0.05 for 5 seconds or $0.08 for 8 seconds per scene.
          </p>

          <button type="submit" disabled={!hasScenes || loading}>
            {job ? "Working..." : "Animate all scenes"}
          </button>
          {error ? <p className="message error">{error}</p> : null}
        </form>

        <section className="panel result-panel">
          <div className="result-header">
            <h2>Animated Scenes</h2>
            {result ? <span>{result.scene_count} clips</span> : null}
          </div>

          {job ? <JobProgress job={job} onCancel={onCancel} /> : result ? (
            <div className="scene-sequence">
              {result.scenes.map((scene) => (
                <article className="scene-card" key={scene.scene_number}>
                  <video className="video-player animated-scene-video" controls src={scene.video_url}>
                    Your browser does not support video playback.
                  </video>
                  <p className="script-event">Scene {scene.scene_number}</p>
                  <p>{scene.motion_prompt}</p>
                  <a href={scene.video_url} target="_blank" rel="noreferrer">Open animated clip</a>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state"><p>Your animated scene clips will show up here.</p></div>
          )}
        </section>
      </section>
    </section>
  );
}
