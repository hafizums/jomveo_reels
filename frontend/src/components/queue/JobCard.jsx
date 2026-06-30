import { useMemo } from "react";

export function getFriendlyJobType(type) {
  switch (type) {
    case "script.generate":
      return "Script Generation";
    case "voiceover.generate":
      return "Voiceover Generation";
    case "background_music.generate":
      return "Background Music";
    case "art_style.generate":
      return "Art Style Reference";
    case "scene_sequence.generate":
      return "Art Scenes Sequence";
    case "scene_animation.generate":
      return "Scene Animation";
    case "video.generate":
      return "Video Assembly";
    default:
      return type;
  }
}

export default function JobCard({
  job,
  onClick,
  adminEnabled = false,
  onCancel = null,
  cancelLoading = false,
}) {
  const isTerminal = ["completed", "failed", "cancelled"].includes(job.status);
  const friendlyType = getFriendlyJobType(job.type);

  // Compute progress percentage
  const progressPercent = useMemo(() => {
    if (!job.progress_total) return 0;
    return Math.min(100, Math.round((job.progress_current / job.progress_total) * 100));
  }, [job.progress_current, job.progress_total]);

  const handleCancelClick = (e) => {
    e.stopPropagation();
    if (onCancel && window.confirm(`Are you sure you want to cancel job ${job.job_id}?`)) {
      onCancel(job.job_id);
    }
  };

  const formattedTime = useMemo(() => {
    try {
      return new Date(job.created_at).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  }, [job.created_at]);

  return (
    <div
      className={`queue-job-card ${job.status}`}
      onClick={() => onClick?.(job)}
    >
      <div className="job-card-header">
        <div className="job-card-meta">
          <strong className="job-card-title">{friendlyType}</strong>
          <span className="job-card-time">{formattedTime}</span>
        </div>
        <span className={`status-badge ${job.status}`}>
          {job.status === "running" && <span className="spinner-indicator" />}
          {job.status}
        </span>
      </div>

      <div className="job-card-progress-section">
        <div className="progress-labels">
          <span className="progress-fraction">
            Step {job.progress_current} of {job.progress_total}
          </span>
          <span className="progress-percent">{progressPercent}%</span>
        </div>
        <div className="job-progress-bar-bg">
          <div
            className="job-progress-bar-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      <div className="job-card-footer">
        <div className="job-card-attempts">
          <span>Attempt {job.attempt_count}/{job.max_attempts}</span>
          {job.status === "retrying" && job.next_retry_at && (
            <span className="retry-label"> · Retrying soon</span>
          )}
        </div>

        {adminEnabled && !isTerminal && onCancel && (
          <button
            type="button"
            className="job-cancel-btn"
            disabled={cancelLoading}
            onClick={handleCancelClick}
          >
            {cancelLoading ? "..." : "Cancel"}
          </button>
        )}
      </div>

      {job.error && (
        <div className="job-card-error-preview">
          <span className="error-icon">⚠️</span>
          <p className="error-message-text">{job.error.message}</p>
        </div>
      )}
    </div>
  );
}
