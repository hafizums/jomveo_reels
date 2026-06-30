import { useEffect, useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import { adminKey, backend } from "../lib/api";
import JobCard from "../components/queue/JobCard";
import JobInspector from "../components/queue/JobInspector";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";

export default function ProjectJobsPage({ onProjectChange }) {
  const { projectId } = useParams();
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobAssets, setJobAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");

  const [recovering, setRecovering] = useState(false);
  const [cancellingId, setCancellingId] = useState(null);

  const activeJobsCount = useMemo(() => {
    return jobs.filter((j) => ["queued", "running", "retrying"].includes(j.status)).length;
  }, [jobs]);

  const hasActiveJobs = activeJobsCount > 0;

  // Poll project jobs
  useEffect(() => {
    onProjectChange(projectId);
    let active = true;

    const fetchJobs = async (showLoading = false) => {
      if (showLoading) setLoading(true);
      try {
        const data = await backend.jobs(projectId);
        if (active) {
          setJobs(data.jobs || []);
          setError("");

          // Update currently inspected job
          if (selectedJob) {
            const updated = data.jobs.find((j) => j.job_id === selectedJob.job_id);
            if (updated) {
              setSelectedJob(updated);
            }
          }
        }
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (showLoading && active) setLoading(false);
      }
    };

    fetchJobs(true);

    // Auto-poll if there are active (queued/running) jobs
    if (!hasActiveJobs) return undefined;

    const interval = setInterval(() => {
      fetchJobs(false);
    }, 4000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [onProjectChange, projectId, hasActiveJobs, selectedJob?.job_id]);

  // Load assets when inspecting a completed job
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
      setError("Failed to cancel job: " + err.message);
    } finally {
      setCancellingId(null);
    }
  };

  const handleRecoverStale = async () => {
    if (!window.confirm("Are you sure you want to recover stale queue jobs?")) return;
    setRecovering(true);
    try {
      const res = await backend.recoverStale();
      alert(`Stale jobs recovered: ${res.recovered_stale}, requeued: ${res.requeued_due}`);
      // Refresh jobs list
      const data = await backend.jobs(projectId);
      setJobs(data.jobs || []);
    } catch (err) {
      setError("Failed to recover stale jobs: " + err.message);
    } finally {
      setRecovering(false);
    }
  };

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
    <section className="route-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Project workspace</p>
          <h1>Project queue</h1>
          <p>Monitor, inspect, and manage queued and completed background runs.</p>
        </div>
        {adminKey && (
          <button
            type="button"
            className="secondary-button"
            style={{ borderColor: "var(--accent-violet)", color: "var(--accent-violet)" }}
            disabled={recovering}
            onClick={handleRecoverStale}
          >
            {recovering ? "Recovering..." : "Recover Stale Jobs (Admin)"}
          </button>
        )}
      </header>

      <ErrorBanner message={error} />

      {loading && jobs.length === 0 ? (
        <LoadingState label="Loading project queue..." />
      ) : (
        <div className="dashboard-columns">
          {/* Left Column: Jobs List */}
          <div className="dashboard-card" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0 }}>Queue Runs</h3>
              {activeJobsCount > 0 && (
                <span className="status-badge running" style={{ animation: "pulse 2s infinite" }}>
                  {activeJobsCount} Active
                </span>
              )}
            </div>

            {/* Filter buttons */}
            <div className="drawer-filters" style={{ borderBottom: "1px solid rgba(0,0,0,0.06)", paddingBottom: "12px", marginBottom: "4px" }}>
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

            <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "680px", overflowY: "auto" }}>
              {filteredJobs.length === 0 ? (
                <div className="empty-state" style={{ minHeight: "200px" }}>
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

          {/* Right Column: Job Inspector */}
          <div className="dashboard-card" style={{ padding: "0 20px" }}>
            {assetsLoading ? (
              <div style={{ display: "grid", placeContent: "center", minHeight: "300px", gap: "10px", color: "#94a3b8" }}>
                <div className="spinner" />
                <span>Loading assets...</span>
              </div>
            ) : (
              <JobInspector
                job={selectedJob}
                assets={jobAssets}
                adminEnabled={Boolean(adminKey)}
                onCancel={handleCancelJob}
                cancelLoading={cancellingId === selectedJob?.job_id}
              />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
