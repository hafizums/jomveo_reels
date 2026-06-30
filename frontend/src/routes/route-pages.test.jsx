import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import JobDetailPage from "./JobDetailPage";
import { backend } from "../lib/api";

vi.mock("../lib/api", () => ({
  backend: {
    job: vi.fn(),
    jobAssets: vi.fn(),
  },
}));

beforeEach(() => vi.clearAllMocks());

function renderJobRoute() {
  return render(
    <MemoryRouter initialEntries={["/jobs/job_1"]}>
      <Routes><Route path="/jobs/:jobId" element={<JobDetailPage selectedProjectId="project_demo" />} /></Routes>
    </MemoryRouter>,
  );
}

test("job detail route moves from loading to loaded content", async () => {
  backend.job.mockResolvedValue({ job_id: "job_1", type: "script.generate", status: "completed", progress_current: 1, progress_total: 1, attempt_count: 1, max_attempts: 3 });
  backend.jobAssets.mockResolvedValue({ assets: [] });
  renderJobRoute();
  expect(screen.getByRole("status")).toHaveTextContent("Loading job details…");
  expect(await screen.findByText("Attempt 1/3")).toBeVisible();
  expect(screen.getByRole("link", { name: "Back to jobs" })).toHaveAttribute("href", "/projects/project_demo/jobs");
});

test("job detail route exposes friendly API errors", async () => {
  backend.job.mockRejectedValue(new Error("This item was not found."));
  backend.jobAssets.mockResolvedValue({ assets: [] });
  renderJobRoute();
  expect(await screen.findByRole("alert")).toHaveTextContent("This item was not found.");
});
