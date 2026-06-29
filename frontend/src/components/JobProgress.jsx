import React from "react";

export default function JobProgress({ job, onCancel }) {
  if (!job) return null;

  const { status, progress_current = 0, progress_total = 100 } = job;
  const isIndeterminate = progress_total === 0 || progress_total === 100 && progress_current === 0;
  
  const progressPercent = isIndeterminate 
    ? 0 
    : Math.min(100, Math.round((progress_current / progress_total) * 100));

  return (
    <div className="job-progress-container">
      <div className="job-progress-pulse">
        {status === "queued" ? "Q" : Math.round(progressPercent) + "%"}
      </div>
      
      <div className="job-status-text">
        {status === "queued" ? "Queued in background..." : `Status: ${status}`}
      </div>

      <div className="job-progress-bar-wrapper">
        {isIndeterminate && status !== "queued" ? (
          <div className="job-progress-bar-indeterminate" />
        ) : (
          <div
            className="job-progress-bar-fill"
            style={{ width: `${status === "queued" ? 0 : progressPercent}%` }}
          />
        )}
      </div>

      {(status === "queued" || status === "running" || status === "retrying") && (
        <button
          type="button"
          className="job-cancel-button"
          onClick={onCancel}
        >
          Cancel Job
        </button>
      )}
    </div>
  );
}
