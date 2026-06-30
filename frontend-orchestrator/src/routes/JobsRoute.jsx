import { useEffect, useState, useMemo } from "react";
import { adminKey, backend } from "../lib/api";
import JobCard from "../components/JobCard";
import JobInspector from "../components/JobInspector";

export default function JobsRoute({ projectId }) {
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

  useEffect(() => {
    if (!projectId) return undefined;
    let active = true;

    const fetchJobs = async (showLoading = false) => {
      if (showLoading) setLoading(true);
      try {
        const data = await backend.jobs(projectId);
        if (active) {
          setJobs(data.jobs || []);
          setError("");

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

    if (!hasActiveJobs) return undefined;

    const interval = setInterval(() => {
      fetchJobs(false);
    }, 4000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [projectId, hasActiveJobs, selectedJob?.job_id]);

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

  if (!projectId) {
    return (
      <div className="empty-state">
        <p>Please select a project workspace to monitor jobs.</p>
      </div>
    );
  }

  return (
    <div className="stepper-step-container">
      <header className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "none", border: "none", padding: 0, boxShadow: "none" }}>
        <div>
          <span className="eyebrow">Project queue</span>
          <h1>Background Jobs</h1>
          <p>Inspect progress, attempts, parameters, and generated assets in real-time.</p>
        </div>
        {adminKey && (
          <button
            type="button"
            className="btn-secondary"
            disabled={recovering}
            onClick={handleRecoverStale}
            style={{ fontSize: 12, padding: "8px 16px" }}
          >
            {recovering ? "Recovering..." : "Recover Stale Jobs"}
          </button>
        )}
      </header>

      {error && <div className="message error" style={{ marginBottom: 20 }}>{error}</div>}

      {loading && jobs.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center" }}>
          <div className="spinner" /> Loading project jobs...
        </div>
      ) : (
        <div className="grid-cols-2">
          {/* Left: list */}
          <div className="dashboard-card" style={{ display: "flex", flexDirection: "column", gap: 12, margin: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0 }}>Queue Runs</h3>
              {activeJobsCount > 0 && (
                <span className="badge running">
                  {activeJobsCount} Running
                </span>
              )}
            </div>

            {/* Filter buttons */}
            <div className="drawer-filters" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: 10 }}>
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

            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: "580px", overflowY: "auto" }}>
              {filteredJobs.length === 0 ? (
                <div className="empty-state" style={{ minHeight: 200 }}>
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

          {/* Right: details */}
          <div className="dashboard-card" style={{ margin: 0 }}>
            {assetsLoading ? (
              <div style={{ display: "grid", placeContent: "center", minHeight: 300, gap: 10, color: "#6b7280" }}>
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
    </div>
  );
}
