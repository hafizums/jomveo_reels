import { useEffect, useState, useMemo } from "react";
import { adminKey, backend } from "../../lib/api";
import JobCard from "./JobCard";
import JobInspector from "./JobInspector";

export default function QueueMonitorDrawer({
  projectId,
  onImportResult,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobAssets, setJobAssets] = useState([]);
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [filter, setFilter] = useState("all"); // 'all' | 'active' | 'completed' | 'failed'

  const [recovering, setRecovering] = useState(false);
  const [cancellingId, setCancellingId] = useState(null);

  // Derive active jobs count (queued, running, retrying)
  const activeJobsCount = useMemo(() => {
    return jobs.filter((j) => ["queued", "running", "retrying"].includes(j.status)).length;
  }, [jobs]);

  const hasActiveJobs = activeJobsCount > 0;

  // Poll jobs list
  useEffect(() => {
    if (!projectId) return undefined;

    let active = true;
    const fetchJobs = async (showLoading = false) => {
      if (showLoading) setLoading(true);
      try {
        const data = await backend.jobs(projectId);
        if (active) {
          setJobs(data.jobs || []);
          // Update selected job detail in real time if open
          if (selectedJob) {
            const updated = data.jobs.find((j) => j.job_id === selectedJob.job_id);
            if (updated) {
              setSelectedJob(updated);
            }
          }
        }
      } catch (err) {
        console.error("Error polling queue jobs:", err);
      } finally {
        if (showLoading && active) setLoading(false);
      }
    };

    fetchJobs(true);

    // Poll if drawer is open OR if there are active jobs in the project
    const shouldPoll = isOpen || hasActiveJobs;
    if (!shouldPoll) return undefined;

    const intervalId = setInterval(() => {
      fetchJobs(false);
    }, 4000);

    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, [projectId, isOpen, hasActiveJobs, selectedJob?.job_id]);

  // Load assets when a completed job is selected
  const handleInspectJob = async (job) => {
    setSelectedJob(job);
    setJobAssets([]);
    if (job.status === "completed") {
      setAssetsLoading(true);
      try {
        const data = await backend.jobAssets(job.job_id);
        setJobAssets(data.assets || []);
      } catch (err) {
        console.error("Error loading job assets:", err);
      } finally {
        setAssetsLoading(false);
      }
    }
  };

  const handleCancelJob = async (jobId) => {
    setCancellingId(jobId);
    try {
      await backend.cancelJob(jobId);
      setJobs((current) =>
        current.map((j) => (j.job_id === jobId ? { ...j, status: "cancelled" } : j))
      );
      if (selectedJob && selectedJob.job_id === jobId) {
        setSelectedJob((prev) => ({ ...prev, status: "cancelled" }));
      }
    } catch (err) {
      alert("Failed to cancel job: " + err.message);
    } finally {
      setCancellingId(null);
    }
  };

  const handleRecoverStale = async () => {
    if (!window.confirm("Are you sure you want to recover stale/hanging queue jobs?")) return;
    setRecovering(true);
    try {
      const res = await backend.recoverStale();
      alert(`Stale jobs recovered: ${res.recovered_stale}, requeued: ${res.requeued_due}`);
      // Refresh jobs list
      const data = await backend.jobs(projectId);
      setJobs(data.jobs || []);
    } catch (err) {
      alert("Failed to recover stale jobs: " + err.message);
    } finally {
      setRecovering(false);
    }
  };

  const handleImport = (job) => {
    if (onImportResult && job.result) {
      onImportResult(job.type, job.result);
      setIsOpen(false); // Auto close drawer after importing
    }
  };

  // Filtered jobs
  const filteredJobs = useMemo(() => {
    switch (filter) {
      case "active":
        return jobs.filter((j) => ["queued", "running", "retrying"].includes(j.status));
      case "completed":
        return jobs.filter((j) => j.status === "completed");
      case "failed":
        return jobs.filter((j) => ["failed", "cancelled"].includes(j.status));
      default:
        return jobs;
    }
  }, [jobs, filter]);

  return (
    <>
      {/* Floating Glowing Button */}
      <button
        type="button"
        className={`queue-monitor-toggle-btn ${hasActiveJobs ? "has-active" : ""}`}
        onClick={() => setIsOpen(true)}
      >
        <span className="queue-btn-icon">📋</span>
        <span className="queue-btn-text">Queue Monitor</span>
        {activeJobsCount > 0 && (
          <span className="queue-active-badge">{activeJobsCount}</span>
        )}
      </button>

      {/* Drawer Overlay */}
      {isOpen && (
        <div className="drawer-overlay" onClick={() => setIsOpen(false)}>
          {/* Drawer Container */}
          <div className="drawer-container" onClick={(e) => e.stopPropagation()}>
            {selectedJob ? (
              /* Detail Inspector View */
              <div className="drawer-view-inspector">
                <button
                  type="button"
                  className="secondary-button back-to-list-btn"
                  onClick={() => setSelectedJob(null)}
                >
                  ← Back to Queue List
                </button>
                {assetsLoading ? (
                  <div className="assets-spinner-container">
                    <div className="spinner" />
                    <span>Loading assets...</span>
                  </div>
                ) : (
                  <JobInspector
                    job={selectedJob}
                    assets={jobAssets}
                    onImport={handleImport}
                    adminEnabled={Boolean(adminKey)}
                    onCancel={handleCancelJob}
                    cancelLoading={cancellingId === selectedJob.job_id}
                    onClose={() => setSelectedJob(null)}
                  />
                )}
              </div>
            ) : (
              /* List View */
              <div className="drawer-view-list">
                <div className="drawer-header">
                  <div>
                    <h2>Project Queue</h2>
                    <p className="helper-text">Monitor workspace background jobs</p>
                  </div>
                  <button
                    type="button"
                    className="drawer-close-btn"
                    onClick={() => setIsOpen(false)}
                  >
                    ✕
                  </button>
                </div>

                {/* Admin Actions */}
                {adminKey && (
                  <div className="drawer-admin-section">
                    <button
                      type="button"
                      className="secondary-button admin-recover-btn"
                      disabled={recovering}
                      onClick={handleRecoverStale}
                    >
                      {recovering ? "Recovering..." : "Recover Stale Jobs (Admin)"}
                    </button>
                  </div>
                )}

                {/* Filters */}
                <div className="drawer-filters">
                  <button
                    type="button"
                    className={`filter-chip ${filter === "all" ? "active" : ""}`}
                    onClick={() => setFilter("all")}
                  >
                    All ({jobs.length})
                  </button>
                  <button
                    type="button"
                    className={`filter-chip ${filter === "active" ? "active" : ""}`}
                    onClick={() => setFilter("active")}
                  >
                    Active ({jobs.filter((j) => ["queued", "running", "retrying"].includes(j.status)).length})
                  </button>
                  <button
                    type="button"
                    className={`filter-chip ${filter === "completed" ? "active" : ""}`}
                    onClick={() => setFilter("completed")}
                  >
                    Done ({jobs.filter((j) => j.status === "completed").length})
                  </button>
                  <button
                    type="button"
                    className={`filter-chip ${filter === "failed" ? "active" : ""}`}
                    onClick={() => setFilter("failed")}
                  >
                    Failed ({jobs.filter((j) => ["failed", "cancelled"].includes(j.status)).length})
                  </button>
                </div>

                {/* Jobs List */}
                <div className="drawer-jobs-list">
                  {loading && jobs.length === 0 ? (
                    <div className="drawer-loading-state">
                      <div className="spinner" />
                      <p>Loading jobs...</p>
                    </div>
                  ) : filteredJobs.length === 0 ? (
                    <div className="drawer-empty-state">
                      <p>No jobs found matching "{filter}".</p>
                    </div>
                  ) : (
                    filteredJobs.map((job) => (
                      <JobCard
                        key={job.job_id}
                        job={job}
                        onClick={handleInspectJob}
                        adminEnabled={Boolean(adminKey)}
                        onCancel={handleCancelJob}
                        cancelLoading={cancellingId === job.job_id}
                      />
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
