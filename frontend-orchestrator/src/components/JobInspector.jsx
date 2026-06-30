import { useState, useMemo } from "react";
import { getFriendlyJobType } from "./JobCard";

export default function JobInspector({
  job,
  assets = [],
  onClose,
  onImport,
  adminEnabled = false,
  onCancel,
  cancelLoading = false,
}) {
  const [showJson, setShowJson] = useState(false);

  const durationText = useMemo(() => {
    if (!job || !job.started_at) return null;
    const start = new Date(job.started_at).getTime();
    const end = job.completed_at ? new Date(job.completed_at).getTime() : Date.now();
    const ms = end - start;
    if (ms < 0) return null;
    const secs = Math.floor(ms / 1000);
    const mins = Math.floor(secs / 60);
    if (mins > 0) return `${mins}m ${secs % 60}s`;
    return `${secs}s`;
  }, [job?.started_at, job?.completed_at, job?.status]);

  if (!job) {
    return (
      <div className="job-inspector-empty">
        <p>Select a job from the queue to inspect parameters, timeline, and generated media assets.</p>
      </div>
    );
  }

  const isTerminal = ["completed", "failed", "cancelled"].includes(job.status);
  const friendlyType = getFriendlyJobType(job.type);

  const handleCancelClick = () => {
    if (onCancel && window.confirm(`Are you sure you want to cancel job ${job.job_id}?`)) {
      onCancel(job.job_id);
    }
  };

  return (
    <div className="job-inspector" style={{ minHeight: "600px" }}>
      <div className="job-inspector-header">
        <div>
          <span className="eyebrow">Inspector Mode</span>
          <h3>{friendlyType}</h3>
          <code className="job-id-code">{job.job_id}</code>
        </div>
        {onClose && (
          <button type="button" className="inspector-close-btn" onClick={onClose}>
            ✕
          </button>
        )}
      </div>

      <div className="job-inspector-body">
        <div className="inspector-meta-grid">
          <div className="meta-item">
            <span className="meta-label">Status</span>
            <span className={`badge ${job.status}`}>{job.status}</span>
          </div>
          {durationText && (
            <div className="meta-item">
              <span className="meta-label">Duration</span>
              <span className="meta-val">{durationText}</span>
            </div>
          )}
          <div className="meta-item">
            <span className="meta-label">Attempts</span>
            <span className="meta-val">
              Attempt {job.attempt_count}/{job.max_attempts}
            </span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Progress</span>
            <span className="meta-val">
              {job.progress_current} / {job.progress_total}
            </span>
          </div>
        </div>

        {job.error && (
          <div className="inspector-error-panel">
            <strong>⚠️ {job.error.code || "Job Run Error"}</strong>
            <p>{job.error.message}</p>
          </div>
        )}

        <div className="inspector-section">
          <h4>Timeline Logs</h4>
          <ul className="timeline-list">
            <li>
              <span className="timeline-time">{new Date(job.created_at).toLocaleString()}</span>
              <span className="timeline-text">Job Created</span>
            </li>
            {job.started_at && (
              <li>
                <span className="timeline-time">{new Date(job.started_at).toLocaleString()}</span>
                <span className="timeline-text">Execution Started</span>
              </li>
            )}
            {job.completed_at && (
              <li>
                <span className="timeline-time">{new Date(job.completed_at).toLocaleString()}</span>
                <span className="timeline-text">Execution Succeeded</span>
              </li>
            )}
          </ul>
        </div>

        {job.input_payload && (
          <div className="inspector-section">
            <button
              type="button"
              className="btn-secondary inspector-toggle-btn"
              onClick={() => setShowJson(!showJson)}
              style={{ width: "100%", padding: 8, fontSize: 12 }}
            >
              {showJson ? "Hide Execution Parameters" : "Show Execution Parameters"}
            </button>
            {showJson && (
              <pre className="json-block" style={{ marginTop: 10 }}>
                <code>{JSON.stringify(job.input_payload, null, 2)}</code>
              </pre>
            )}
          </div>
        )}

        {job.status === "completed" && (
          <div className="inspector-section">
            <h4>Output Assets</h4>

            {assets.length > 0 ? (
              <div className="inspector-assets-list">
                {assets.map((asset) => {
                  const isImage = ["image", "art"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(jpeg|jpg|png|webp)/i);
                  const isAudio = ["audio", "voiceover", "music"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(mp3|wav|ogg)/i);
                  const isVideo = ["video", "clip"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(mp4|webm)/i);

                  return (
                    <div key={asset.id} className="inspector-asset-preview-card" style={{ background: "var(--color-surface-2)" }}>
                      <div className="asset-header">
                        <strong>Asset ({asset.asset_type})</strong>
                        <a href={asset.url} target="_blank" rel="noreferrer" className="download-link" download>
                          Download ↗
                        </a>
                      </div>

                      {isImage && (
                        <img src={asset.url} alt="Asset Output" className="asset-preview-thumb" style={{ aspectRatio: "auto", maxHeight: 300 }} />
                      )}

                      {isAudio && (
                        <audio src={asset.url} controls className="audio-player-custom" style={{ width: "100%", marginTop: 8 }} />
                      )}

                      {isVideo && (
                        <video src={asset.url} controls className="video-preview-large" style={{ maxHeight: 300, marginTop: 8 }} />
                      )}

                      <div className="asset-footer" style={{ marginTop: 6 }}>
                        <small>{asset.filename || "file-output"}</small>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : job.result ? (
              <div className="inspector-result-fallback">
                {job.type === "script.generate" && job.result.script && (
                  <div className="script-fallback-preview">
                    <strong>{job.result.title}</strong>
                    <pre className="script-output" style={{ background: "var(--color-surface-2)", padding: 12, borderRadius: 8, whiteSpace: "pre-wrap", fontSize: 13, color: "#cbd5e1" }}>
                      {job.result.script}
                    </pre>
                  </div>
                )}
                {job.type === "voiceover.generate" && job.result.audio_url && (
                  <audio src={job.result.audio_url} controls style={{ width: "100%" }} />
                )}
                {job.type === "background_music.generate" && job.result.audio_urls?.[0] && (
                  <audio src={job.result.audio_urls[0]} controls style={{ width: "100%" }} />
                )}
                {job.type === "art_style.generate" && job.result.image_url && (
                  <img src={job.result.image_url} alt="Result Preview" className="asset-preview-thumb" />
                )}
                {job.type === "video.generate" && job.result.video_url && (
                  <video src={job.result.video_url} controls className="video-preview-large" />
                )}
                <pre className="json-block" style={{ marginTop: 10 }}>
                  <code>{JSON.stringify(job.result, null, 2)}</code>
                </pre>
              </div>
            ) : (
              <p style={{ color: "#6b7280", fontSize: 12 }}>No outputs found.</p>
            )}
          </div>
        )}
      </div>

      <div className="job-inspector-footer">
        {job.status === "completed" && onImport && (
          <button type="button" className="btn-primary" style={{ width: "100%" }} onClick={() => onImport(job)}>
            Import Result to Stepper
          </button>
        )}

        {adminEnabled && !isTerminal && onCancel && (
          <button
            type="button"
            className="job-cancel-btn"
            style={{ width: "100%", padding: 12 }}
            disabled={cancelLoading}
            onClick={handleCancelClick}
          >
            {cancelLoading ? "Cancelling..." : "Cancel Active Job"}
          </button>
        )}
      </div>
    </div>
  );
}
