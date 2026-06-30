import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import JobDetailPanel from "../components/dashboard/JobDetailPanel";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";
import { backend } from "../lib/api";

export default function JobDetailPage({ selectedProjectId }) {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([backend.job(jobId), backend.jobAssets(jobId)]).then(([jobData, assetData]) => { if (active) { setJob(jobData); setAssets(assetData.assets); setError(""); } }).catch(loadError => { if (active) setError(loadError.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [jobId]);

  const backTo = selectedProjectId ? `/projects/${selectedProjectId}/jobs` : "/dashboard";
  return (
    <section className="route-page">
      <header className="page-header"><div><p className="eyebrow">Job details</p><h1>Project job</h1><p>Inspect progress, attempts, errors, and registered assets.</p></div><Link className="secondary-link" to={backTo}>Back to jobs</Link></header>
      <ErrorBanner message={error} />
      {loading ? <LoadingState label="Loading job details…" /> : job ? <JobDetailPanel job={job} assets={assets} /> : null}
    </section>
  );
}
