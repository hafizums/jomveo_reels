import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import CreateSeriesWizard from "./CreateSeriesWizard";
import CreateSeriesPage from "../../routes/CreateSeriesPage";

const project = { id: "project_demo", name: "Demo Project" };

function renderWizard(overrides = {}) {
  const props = {
    projects: [project],
    projectId: project.id,
    onProjectChange: vi.fn(),
    onCreateProject: vi.fn(),
    creatingProject: false,
    onQueueFirstVideo: vi.fn().mockResolvedValue({ job_id: "job_123" }),
    ...overrides,
  };
  render(<MemoryRouter><CreateSeriesWizard {...props} /></MemoryRouter>);
  return props;
}

beforeEach(() => localStorage.clear());

test("create wizard renders and review shows configured defaults", () => {
  renderWizard();
  expect(screen.getByRole("heading", { name: "Choose niche" })).toBeVisible();
  for (const value of ["Malaysian true crime", "English", "60 seconds", "Cinematic Realism", "Calm Narrator", "Minimalist", "Demo Project"]) {
    expect(screen.getAllByText(value).length).toBeGreaterThan(0);
  }
  expect(screen.getByRole("link", { name: "Open Advanced Generator" })).toHaveAttribute("href", "/generate");
});

test("niche selection and custom niche update the wizard", async () => {
  renderWizard();
  await userEvent.click(screen.getByRole("button", { name: /Mythology/ }));
  expect(screen.getByRole("button", { name: /Mythology/ })).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(screen.getByRole("button", { name: /Custom niche/ }));
  await userEvent.type(screen.getByLabelText("Custom niche prompt"), "Unusual Malaysian food history");
  expect(screen.getAllByText("Unusual Malaysian food history")).toHaveLength(2);
});

test("missing project blocks queue with friendly error", async () => {
  const props = renderWizard({ projects: [], projectId: "" });
  await userEvent.click(screen.getByRole("button", { name: "Queue First Video" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Select or create a project before queueing the first video.");
  expect(props.onQueueFirstVideo).not.toHaveBeenCalled();
});

test("create page queues a script job through the existing API client", async () => {
  const api = {
    projects: vi.fn().mockResolvedValue({ projects: [project], count: 1 }),
    createProject: vi.fn(),
    createJob: vi.fn().mockResolvedValue({ job_id: "queued_script" }),
  };
  render(<MemoryRouter><CreateSeriesPage projectId={project.id} onProjectChange={vi.fn()} api={api} /></MemoryRouter>);
  await screen.findByRole("heading", { name: "Create New Series" });
  await userEvent.click(screen.getByRole("button", { name: "Queue First Video" }));
  expect(api.createJob).toHaveBeenCalledWith("scripts", expect.objectContaining({ duration_seconds: 60, language: "English" }), project.id);
  expect(await screen.findByText("Queued first video script job queued_script.")).toBeVisible();
});
