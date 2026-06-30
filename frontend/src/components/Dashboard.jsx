import { useCallback, useEffect, useState } from "react";
import { adminKey, backend, defaultProjectId } from "../lib/api";

const terminal = new Set(["completed", "failed", "cancelled"]);
const creditsUsd = (value) => `$${(value / 100).toFixed(2)}`;

function AssetCard({ asset }) {
  return <article className={`asset-card asset-${asset.status}`}>
    <div className="dashboard-row"><strong>{asset.asset_type}</strong><span className="status-badge">{asset.status}</span></div>
    {asset.expires_at ? <small>May expire: {new Date(asset.expires_at).toLocaleString()}</small> : null}
    {asset.warning ? <p className="download-warning">{asset.warning}</p> : null}
    <a href={asset.url} target="_blank" rel="noreferrer">Open / Download</a>
  </article>;
}

export default function Dashboard({ jobDrafts = {} }) {
  const [me, setMe] = useState(null), [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(localStorage.getItem("jomveo.selectedProjectId") || defaultProjectId);
  const [name, setName] = useState(""), [jobs, setJobs] = useState([]), [assets, setAssets] = useState([]);
  const [billing, setBilling] = useState(null), [usage, setUsage] = useState(null), [quotas, setQuotas] = useState(null), [transactions, setTransactions] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null), [jobAssets, setJobAssets] = useState([]), [error, setError] = useState("");
  const [topUp, setTopUp] = useState(1000);

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const [jobData, assetData, bill, tx, use, quota] = await Promise.all([backend.jobs(projectId), backend.assets(projectId), backend.billing(projectId), backend.transactions(projectId), backend.usage(projectId), backend.quotas(projectId)]);
      setJobs(jobData.jobs); setAssets(assetData.assets); setBilling(bill); setTransactions(tx.transactions); setUsage(use); setQuotas(quota); setError("");
    } catch (e) { setError(e.message); }
  }, [projectId]);

  useEffect(() => { Promise.all([backend.me(), backend.projects()]).then(([identity, data]) => { setMe(identity); setProjects(data.projects); if (!projectId && data.projects[0]) setProjectId(data.projects[0].id); }).catch(e => setError(e.message)); }, []);
  useEffect(() => { if (projectId) { localStorage.setItem("jomveo.selectedProjectId", projectId); loadProject(); } }, [projectId, loadProject]);
  useEffect(() => { if (!jobs.some(job => !terminal.has(job.status))) return; const timer = setInterval(loadProject, 4000); return () => clearInterval(timer); }, [jobs, loadProject]);

  const create = async (event) => { event.preventDefault(); try { const project = await backend.createProject({ name }); setProjects(current => [project, ...current]); setProjectId(project.id); setName(""); } catch (e) { setError(e.message); } };
  const openJob = async (id) => { try { const [job, data] = await Promise.all([backend.job(id), backend.jobAssets(id)]); setSelectedJob(job); setJobAssets(data.assets); } catch (e) { setError(e.message); } };
  const submitTopUp = async (event) => { event.preventDefault(); try { await backend.topUp(projectId, { amount_credits: Number(topUp), description: "Local admin top-up" }); loadProject(); } catch (e) { setError(e.message); } };
  const queueJob = async (kind) => { if (!projectId) return setError("Please select or create a project first."); try { await backend.createJob(kind, jobDrafts[kind] || {}, projectId); await loadProject(); } catch (e) { setError(e.message); } };

  return <section className="dashboard-shell">
    <header className="dashboard-header"><div><span className="eyebrow">Workspace dashboard</span><h2>Projects, jobs &amp; temporary assets</h2><p>{me ? `${me.email || me.subject} · ${me.role}` : "Loading identity…"}</p></div>
      <label>Project<select value={projectId} onChange={e => setProjectId(e.target.value)}><option value="">Select a project</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label></header>
    <form className="inline-form" onSubmit={create}><input value={name} onChange={e => setName(e.target.value)} placeholder="New project name" required/><button>Create project</button></form>
    {error ? <p className="error-message">{error}</p> : null}
    {projectId ? <><div className="dashboard-grid">
      <article className="dashboard-card"><h3>Internal credits</h3>{billing ? <><strong className="metric">{billing.available_credits}</strong><p>Available · {creditsUsd(billing.available_credits)} internal value</p><small>{billing.balance_credits} balance · {billing.reserved_credits} reserved · {billing.lifetime_used_credits} used</small></> : null}</article>
      <article className="dashboard-card"><h3>Quota usage</h3>{usage && quotas ? <><p>{usage.daily_jobs} / {quotas.daily_job_limit ?? "∞"} daily jobs</p><p>{usage.monthly_jobs} / {quotas.monthly_job_limit ?? "∞"} monthly jobs</p><small>Max concurrent: {quotas.max_concurrent_jobs ?? "Unlimited"}</small></> : null}</article>
      <article className="dashboard-card"><h3>Transactions</h3>{transactions.slice(0,4).map(tx => <p key={tx.id}>{tx.type} · {tx.amount_credits} credits</p>)}</article>
    </div>
    <div className="inline-form"><button onClick={() => queueJob("scripts")}>Queue script job</button><button onClick={() => queueJob("art-style")}>Queue art job</button><button onClick={() => queueJob("background-music")}>Queue music job</button></div>
    {adminKey ? <form className="inline-form" onSubmit={submitTopUp}><input type="number" min="1" value={topUp} onChange={e => setTopUp(e.target.value)}/><button>Admin top-up</button></form> : null}
    <div className="dashboard-columns"><article className="dashboard-card"><h3>Project jobs</h3>{jobs.map(job => <button className="job-row" key={job.job_id} onClick={() => openJob(job.job_id)}><span>{job.type}</span><span className="status-badge">{job.status}</span><small>{job.progress_current}/{job.progress_total} · {new Date(job.created_at).toLocaleString()}</small>{job.error ? <em>{job.error.message}</em> : null}</button>)}</article>
      <article className="dashboard-card"><h3>Job detail</h3>{selectedJob ? <><p><strong>{selectedJob.type}</strong> · {selectedJob.status}</p><p>Attempt {selectedJob.attempt_count}/{selectedJob.max_attempts}</p>{selectedJob.error ? <p className="error-message">{selectedJob.error.message}</p> : null}{jobAssets.map(asset => <AssetCard key={asset.id} asset={asset}/>)}</> : <p>Select a job to inspect it.</p>}</article></div>
    <article className="dashboard-card"><h3>Project assets</h3><p className="download-warning">Generated files are temporarily hosted by the provider. Please download them before the link expires.</p><div className="asset-grid">{assets.map(asset => <AssetCard key={asset.id} asset={asset}/>)}</div></article></> : <p>Create or select a project to view SaaS workspace data. Demo generation below remains available.</p>}
  </section>;
}
