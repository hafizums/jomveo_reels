import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AdminTopUpForm from "./AdminTopUpForm";
import AssetCard from "./AssetCard";
import BillingSummaryCard from "./BillingSummaryCard";
import CreateProjectForm from "./CreateProjectForm";
import JobDetailPanel from "./JobDetailPanel";
import ProjectJobsPanel from "./ProjectJobsPanel";
import ProjectSelector from "./ProjectSelector";
import QuotaSummaryCard from "./QuotaSummaryCard";
import TransactionHistory from "./TransactionHistory";

test("project selector and create form emit user choices",async()=>{const change=vi.fn(),create=vi.fn();render(<><ProjectSelector projects={[{id:"p",name:"Project"}]} value="" onChange={change}/><CreateProjectForm onSubmit={create}/></>);await userEvent.selectOptions(screen.getByLabelText("Project"),"p");expect(change).toHaveBeenCalledWith("p");await userEvent.type(screen.getByPlaceholderText("New project name"),"New");await userEvent.click(screen.getByRole("button",{name:"Create project"}));expect(create).toHaveBeenCalledWith("New");});
test("billing quota and transactions render summaries",()=>{render(<><BillingSummaryCard billing={{available_credits:90,balance_credits:100,reserved_credits:10,lifetime_used_credits:5}}/><QuotaSummaryCard usage={{daily_jobs:1,monthly_jobs:2}} quotas={{daily_job_limit:10,monthly_job_limit:20,max_concurrent_jobs:3}}/><TransactionHistory transactions={[{id:"t",type:"top_up",amount_credits:100}]}/></>);expect(screen.getByText("90")).toBeVisible();expect(screen.getByText(/100 balance/)).toBeVisible();expect(screen.getByText("1 / 10 daily jobs")).toBeVisible();expect(screen.getByText(/top_up/)).toBeVisible();});
test("asset card renders warning status and direct link",()=>{render(<AssetCard asset={{asset_type:"video",status:"expired",warning:"Expired warning",url:"https://provider.test/v.mp4"}}/>);expect(screen.getByText("expired")).toBeVisible();expect(screen.getByText("Expired warning")).toBeVisible();expect(screen.getByRole("link",{name:"Open / Download"})).toHaveAttribute("href","https://provider.test/v.mp4");});
test("job list opens rows and detail renders assets",async()=>{const open=vi.fn();const job={job_id:"j",type:"script.generate",status:"completed",progress_current:1,progress_total:1,attempt_count:1,max_attempts:3,created_at:"2026-06-30T00:00:00Z"};render(<><ProjectJobsPanel jobs={[job]} onOpenJob={open}/><JobDetailPanel job={job} assets={[]}/></>);await userEvent.click(screen.getByRole("button",{name:/script.generate/}));expect(open).toHaveBeenCalledWith("j");expect(screen.getByText("Attempt 1/3")).toBeVisible();});
test("admin top-up submits numeric control",()=>{const submit=vi.fn(event=>event.preventDefault()),change=vi.fn();render(<AdminTopUpForm amount={100} onAmountChange={change} onSubmit={submit}/>);fireEvent.change(screen.getByLabelText("Top-up amount"),{target:{value:"200"}});expect(change).toHaveBeenCalledWith("200");fireEvent.click(screen.getByRole("button",{name:"Admin top-up"}));expect(submit).toHaveBeenCalled();});
