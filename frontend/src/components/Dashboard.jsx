import { useCallback, useEffect, useState } from "react";
import { adminKey, backend } from "../lib/api";
import AdminTopUpForm from "./dashboard/AdminTopUpForm";
import AssetList from "./dashboard/AssetList";
import BillingSummaryCard from "./dashboard/BillingSummaryCard";
import CreateProjectForm from "./dashboard/CreateProjectForm";
import JobDetailPanel from "./dashboard/JobDetailPanel";
import ProjectJobsPanel from "./dashboard/ProjectJobsPanel";
import ProjectSelector from "./dashboard/ProjectSelector";
import QuotaSummaryCard from "./dashboard/QuotaSummaryCard";
import TransactionHistory from "./dashboard/TransactionHistory";

const terminal = new Set(["completed", "failed", "cancelled"]);

export default function Dashboard({ projectId, onProjectChange, refreshToken = 0 }) {
  const [me,setMe]=useState(null), [projects,setProjects]=useState([]), [jobs,setJobs]=useState([]), [assets,setAssets]=useState([]);
  const [billing,setBilling]=useState(null), [usage,setUsage]=useState(null), [quotas,setQuotas]=useState(null), [transactions,setTransactions]=useState([]);
  const [selectedJob,setSelectedJob]=useState(null), [jobAssets,setJobAssets]=useState([]), [error,setError]=useState(""), [topUp,setTopUp]=useState(1000);
  const loadProject=useCallback(async()=>{ if(!projectId)return; try { const [jobData,assetData,bill,tx,use,quota]=await Promise.all([backend.jobs(projectId),backend.assets(projectId),backend.billing(projectId),backend.transactions(projectId),backend.usage(projectId),backend.quotas(projectId)]); setJobs(jobData.jobs);setAssets(assetData.assets);setBilling(bill);setTransactions(tx.transactions);setUsage(use);setQuotas(quota);setError(""); } catch(e){setError(e.message);} },[projectId]);
  useEffect(()=>{Promise.all([backend.me(),backend.projects()]).then(([identity,data])=>{setMe(identity);setProjects(data.projects);if(!projectId&&data.projects[0])onProjectChange(data.projects[0].id);}).catch(e=>setError(e.message));},[]);
  useEffect(()=>{if(projectId){localStorage.setItem("jomveo.selectedProjectId",projectId);loadProject();}},[projectId,loadProject]);
  useEffect(()=>{if(refreshToken)loadProject();},[refreshToken,loadProject]);
  useEffect(()=>{if(!jobs.some(job=>!terminal.has(job.status)))return;const timer=setInterval(loadProject,4000);return()=>clearInterval(timer);},[jobs,loadProject]);
  const create=async name=>{try{const project=await backend.createProject({name});setProjects(current=>[project,...current]);onProjectChange(project.id);}catch(e){setError(e.message);}};
  const openJob=async id=>{try{const [job,data]=await Promise.all([backend.job(id),backend.jobAssets(id)]);setSelectedJob(job);setJobAssets(data.assets);}catch(e){setError(e.message);}};
  const submitTopUp=async event=>{event.preventDefault();try{await backend.topUp(projectId,{amount_credits:Number(topUp),description:"Local admin top-up"});loadProject();}catch(e){setError(e.message);}};
  return <section className="dashboard-shell"><header className="dashboard-header"><div><span className="eyebrow">Workspace dashboard</span><h2>Projects, jobs &amp; temporary assets</h2><p>{me?`${me.email||me.subject} · ${me.role}`:"Loading identity…"}</p></div><ProjectSelector projects={projects} value={projectId} onChange={onProjectChange}/></header><CreateProjectForm onSubmit={create}/>{error?<p className="error-message">{error}</p>:null}{projectId?<><div className="dashboard-grid"><BillingSummaryCard billing={billing}/><QuotaSummaryCard usage={usage} quotas={quotas}/><TransactionHistory transactions={transactions}/></div>{adminKey?<AdminTopUpForm amount={topUp} onAmountChange={setTopUp} onSubmit={submitTopUp}/>:null}<div className="dashboard-columns"><ProjectJobsPanel jobs={jobs} onOpenJob={openJob}/><JobDetailPanel job={selectedJob} assets={jobAssets}/></div><AssetList assets={assets}/></>:<p>Create or select a project to view SaaS workspace data. Demo generation below remains available.</p>}</section>;
}
