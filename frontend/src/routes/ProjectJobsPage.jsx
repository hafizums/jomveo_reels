import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ProjectJobsPanel from "../components/dashboard/ProjectJobsPanel";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";
import { backend } from "../lib/api";

export default function ProjectJobsPage({ onProjectChange }) {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    onProjectChange(projectId);
    let active = true;
    setLoading(true);
    backend.jobs(projectId).then(data => { if (active) { setJobs(data.jobs); setError(""); } }).catch(loadError => { if (active) setError(loadError.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [onProjectChange, projectId]);

  return (
    <section className="route-page">
      <header className="page-header"><div><p className="eyebrow">Project workspace</p><h1>Project jobs</h1><p>Monitor queued and completed work for this project.</p></div></header>
      <ErrorBanner message={error} />
      {loading ? <LoadingState label="Loading project jobs…" /> : <ProjectJobsPanel jobs={jobs} onOpenJob={jobId => navigate(`/jobs/${jobId}`)} />}
    </section>
  );
}
