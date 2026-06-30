import AssetCard from "./AssetCard";
import EmptyState from "../ui/EmptyState";
import ErrorBanner from "../ui/ErrorBanner";
export default function JobDetailPanel({ job, assets }) { return <article className="dashboard-card"><h3>Job detail</h3>{job?<><p className="dashboard-row"><strong>{job.type}</strong><span className={`status-badge ${job.status}`}>{job.status}</span></p><p>Progress {job.progress_current}/{job.progress_total}</p><p>Attempt {job.attempt_count}/{job.max_attempts}</p><ErrorBanner message={job.error?.message}/>{assets.map(asset=><AssetCard key={asset.id} asset={asset}/>)}</>:<EmptyState title="Select a job" description="Choose a job to inspect status, attempts, errors, and assets."/>}</article>; }
