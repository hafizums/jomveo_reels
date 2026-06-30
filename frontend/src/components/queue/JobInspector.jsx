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

  if (!job) {
    return (
      <div className="job-inspector-empty">
        <p>Select a job to inspect details, parameters, and generated assets.</p>
      </div>
    );
  }

  const isTerminal = ["completed", "failed", "cancelled"].includes(job.status);
  const friendlyType = getFriendlyJobType(job.type);

  // Compute duration
  const durationText = useMemo(() => {
    if (!job.started_at) return null;
    const start = new Date(job.started_at).getTime();
    const end = job.completed_at
      ? new Date(job.completed_at).getTime()
      : Date.now();
    const ms = end - start;
    if (ms < 0) return null;
    const secs = Math.floor(ms / 1000);
    const mins = Math.floor(secs / 60);
    if (mins > 0) {
      return `${mins}m ${secs % 60}s`;
    }
    return `${secs}s`;
  }, [job.started_at, job.completed_at, job.status]);

  const handleCancelClick = () => {
    if (onCancel && window.confirm(`Are you sure you want to cancel job ${job.job_id}?`)) {
      onCancel(job.job_id);
    }
  };

  return (
    <div className="job-inspector">
      <div className="job-inspector-header">
        <div>
          <span className="eyebrow">Job Inspector</span>
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
            <span className={`status-badge ${job.status}`}>{job.status}</span>
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

        {/* Error panel */}
        {job.error && (
          <div className="inspector-error-panel">
            <strong>⚠️ {job.error.code || "Job Error"}</strong>
            <p>{job.error.message}</p>
          </div>
        )}

        {/* Timeline */}
        <div className="inspector-section">
          <h4>Timeline</h4>
          <ul className="timeline-list">
            <li>
              <span className="timeline-time">
                {new Date(job.created_at).toLocaleString()}
              </span>
              <span className="timeline-text">Job Created</span>
            </li>
            {job.started_at && (
              <li>
                <span className="timeline-time">
                  {new Date(job.started_at).toLocaleString()}
                </span>
                <span className="timeline-text">Execution Started</span>
              </li>
            )}
            {job.completed_at && (
              <li>
                <span className="timeline-time">
                  {new Date(job.completed_at).toLocaleString()}
                </span>
                <span className="timeline-text">Execution Succeeded</span>
              </li>
            )}
          </ul>
        </div>

        {/* Input parameters */}
        {job.input_payload && (
          <div className="inspector-section">
            <button
              type="button"
              className="secondary-button inspector-toggle-btn"
              onClick={() => setShowJson(!showJson)}
            >
              {showJson ? "Hide Input Parameters" : "Show Input Parameters"}
            </button>
            {showJson && (
              <pre className="inspector-json-block">
                <code>{JSON.stringify(job.input_payload, null, 2)}</code>
              </pre>
            )}
          </div>
        )}

        {/* Output Previews */}
        {job.status === "completed" && (
          <div className="inspector-section">
            <h4>Outputs & Previews</h4>

            {assets.length > 0 ? (
              <div className="inspector-assets-list">
                {assets.map((asset) => {
                  const isImage = ["image", "art"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(jpeg|jpg|png|webp)/i);
                  const isAudio = ["audio", "voiceover", "music"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(mp3|wav|ogg)/i);
                  const isVideo = ["video", "clip"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(mp4|webm)/i);

                  return (
                    <div key={asset.id} className="inspector-asset-preview-card">
                      <div className="asset-header">
                        <strong>Asset ({asset.asset_type})</strong>
                        <a
                          href={asset.url}
                          target="_blank"
                          rel="noreferrer"
                          className="download-link"
                          download
                        >
                          Download ↗
                        </a>
                      </div>

                      {isImage && (
                        <img
                          src={asset.url}
                          alt="Asset Output"
                          className="result-image inspector-preview-img"
                        />
                      )}

                      {isAudio && (
                        <audio src={asset.url} controls className="audio-player" />
                      )}

                      {isVideo && (
                        <video src={asset.url} controls className="video-player inspector-preview-vid" />
                      )}

                      <div className="asset-footer">
                        <small className="filename-small">
                          {asset.filename || "file-output"}
                        </small>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : job.result ? (
              // Fallback to job.result inspection if assets not loaded or empty
              <div className="inspector-result-fallback">
                {job.type === "script.generate" && job.result.script && (
                  <div className="script-fallback-preview">
                    <strong>{job.result.title}</strong>
                    <pre className="script-output">{job.result.script}</pre>
                  </div>
                )}
                {job.type === "voiceover.generate" && job.result.audio_url && (
                  <audio src={job.result.audio_url} controls className="audio-player" />
                )}
                {job.type === "background_music.generate" && job.result.audio_urls?.[0] && (
                  <audio src={job.result.audio_urls[0]} controls className="audio-player" />
                )}
                {job.type === "art_style.generate" && job.result.image_url && (
                  <img src={job.result.image_url} alt="Result Preview" className="result-image" />
                )}
                {job.type === "video.generate" && job.result.video_url && (
                  <video src={job.result.video_url} controls className="video-player" />
                )}
                <pre className="inspector-json-block small-json">
                  <code>{JSON.stringify(job.result, null, 2)}</code>
                </pre>
              </div>
            ) : (
              <p className="no-assets-text">No asset output found in database.</p>
            )}
          </div>
        )}
      </div>

      <div className="job-inspector-footer">
        {job.status === "completed" && onImport && (
          <button
            type="button"
            className="import-to-workspace-btn"
            onClick={() => onImport(job)}
          >
            Import to Workspace
          </button>
        )}

        {adminEnabled && !isTerminal && onCancel && (
          <button
            type="button"
            className="job-cancel-btn full-width"
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
