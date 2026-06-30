/**
 * ProjectActionCard — "Save to Project" section shown at the bottom of every
 * generator form. Clearly separates the async project-job action from the
 * synchronous "Generate" button above it.
 */
export default function ProjectActionCard({
  label,          // e.g. "Save script to project"
  onQueue,        // () => void
  loading,        // bool
  message,        // success string
  error,          // error string
  extraButton,    // optional: { label, onClick } for art "Save scene sequence"
}) {
  return (
    <div className="project-action-card">
      <div className="project-action-card-header">
        <strong>Save to Project</strong>
        <span className="project-action-badge">Async · Uses Credits</span>
      </div>
      <p className="project-action-desc">
        <span>⏱ Runs in background</span>
        <span>💳 Uses billing credits</span>
        <span>📋 Tracked in Dashboard</span>
      </p>

      <button
        type="button"
        className="project-action-btn"
        onClick={onQueue}
        disabled={loading}
      >
        {loading ? "Saving…" : (label || "Save to Project")}
      </button>

      {extraButton ? (
        <button
          type="button"
          className="project-action-btn"
          style={{ marginTop: 8 }}
          onClick={extraButton.onClick}
          disabled={loading}
        >
          {loading ? "Saving…" : extraButton.label}
        </button>
      ) : null}

      {message ? (
        <p className="project-action-feedback success">{message}</p>
      ) : null}
      {error ? (
        <p className="project-action-feedback error">{error}</p>
      ) : null}
    </div>
  );
}
