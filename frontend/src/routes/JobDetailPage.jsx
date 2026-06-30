import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import JobInspector from "../components/queue/JobInspector";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";
import { adminKey, backend } from "../lib/api";

export default function JobDetailPage({ selectedProjectId }) {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);

    const loadJobDetails = async () => {
      try {
        const [jobData, assetData] = await Promise.all([
          backend.job(jobId),
          backend.jobAssets(jobId),
        ]);
        if (active) {
          setJob(jobData);
          setAssets(assetData.assets || []);
          setError("");
        }
      } catch (loadError) {
        if (active) setError(loadError.message);
      } finally {
        if (active) setLoading(false);
      }
    };

    loadJobDetails();

    // Auto-poll job state in detail view if it's not finished
    let interval;
    if (job && !["completed", "failed", "cancelled"].includes(job.status)) {
      interval = setInterval(async () => {
        try {
          const jobData = await backend.job(jobId);
          if (active) {
            setJob(jobData);
            if (jobData.status === "completed") {
              const assetData = await backend.jobAssets(jobId);
              setAssets(assetData.assets || []);
            }
          }
        } catch (e) {
          console.error("Poll job detail error:", e);
        }
      }, 4000);
    }

    return () => {
      active = false;
      if (interval) clearInterval(interval);
    };
  }, [jobId, job?.status]);

  const handleCancelJob = async (id) => {
    setCancelling(true);
    try {
      await backend.cancelJob(id);
      const updated = await backend.job(id);
      setJob(updated);
    } catch (err) {
      setError("Failed to cancel job: " + err.message);
    } finally {
      setCancelling(false);
    }
  };

  const backTo = selectedProjectId ? `/projects/${selectedProjectId}/jobs` : "/dashboard";

  return (
    <section className="route-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Job details</p>
          <h1>Project job</h1>
          <p>Inspect progress, attempts, errors, and registered assets.</p>
        </div>
        <Link className="secondary-link" to={backTo}>
          Back to jobs
        </Link>
      </header>

      <ErrorBanner message={error} />

      {loading ? (
        <LoadingState label="Loading job details…" />
      ) : job ? (
        <div className="dashboard-card" style={{ maxWidth: 800, margin: "0 auto", padding: "0 20px" }}>
          <JobInspector
            job={job}
            assets={assets}
            adminEnabled={Boolean(adminKey)}
            onCancel={handleCancelJob}
            cancelLoading={cancelling}
          />
        </div>
      ) : (
        <div className="empty-state">
          <p>Job not found.</p>
        </div>
      )}
    </section>
  );
}
