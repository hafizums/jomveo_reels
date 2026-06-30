import AssetCard from "./AssetCard";
import EmptyState from "../ui/EmptyState";
import ErrorBanner from "../ui/ErrorBanner";
export default function JobDetailPanel({ job, assets }) { return <article className="dashboard-card"><h3>Job detail</h3>{job?<><p><strong>{job.type}</strong> · {job.status}</p><p>Attempt {job.attempt_count}/{job.max_attempts}</p><ErrorBanner message={job.error?.message}/>{assets.map(asset=><AssetCard key={asset.id} asset={asset}/>)}</>:<EmptyState title="Select a job" description="Choose a job to inspect status, attempts, errors, and assets."/>}</article>; }
