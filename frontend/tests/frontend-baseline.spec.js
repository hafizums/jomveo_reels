import { expect, test } from "@playwright/test";

const project = { id: "project_demo", name: "Demo Project", role: "owner" };
const job = { job_id: "job_1", type: "script.generate", status: "completed", progress_current: 1, progress_total: 1, attempt_count: 1, max_attempts: 3, created_at: "2026-06-30T00:00:00Z", error: null };
const asset = { id: "asset_1", project_id: project.id, job_id: job.job_id, asset_type: "video", provider: "wavespeed", storage_type: "provider_ephemeral", url: "https://provider.example/video.mp4", status: "available", expires_at: "2026-07-07T00:00:00Z", download_required: true, warning: "This file is temporarily hosted by the provider. Download it before the link expires.", created_at: "2026-06-30T00:00:00Z" };

async function mockApi(page, overrides = {}) {
  await page.route("**/api/**", async route => {
    const request = route.request(), url = new URL(request.url()), key = `${request.method()} ${url.pathname}`;
    if (overrides[key]) return overrides[key](route, request);
    const responses = {
      "GET /api/me": { subject: "user:demo", email: "demo@jomveo.local", role: "user" },
      "GET /api/projects": { projects: [project], count: 1 },
      [`GET /api/projects/${project.id}/jobs`]: { jobs: [job], count: 1 },
      [`GET /api/projects/${project.id}/assets`]: { assets: [asset], count: 1 },
      [`GET /api/projects/${project.id}/billing`]: { balance_credits: 1000, reserved_credits: 100, available_credits: 900, lifetime_purchased_credits: 1000, lifetime_used_credits: 0 },
      [`GET /api/projects/${project.id}/billing/transactions`]: { transactions: [{ id: "tx1", type: "top_up", amount_credits: 1000 }], count: 1 },
      [`GET /api/projects/${project.id}/billing/usage`]: { daily_jobs: 1, monthly_jobs: 2, daily_credits: 5, monthly_credits: 10 },
      [`GET /api/projects/${project.id}/quotas`]: { daily_job_limit: 100, monthly_job_limit: 1000, max_concurrent_jobs: 3 },
      [`GET /api/jobs/${job.job_id}`]: job,
      [`GET /api/jobs/${job.job_id}/assets`]: { assets: [asset], count: 1 },
    };
    return route.fulfill({ status: responses[key] ? 200 : 404, contentType: "application/json", body: JSON.stringify(responses[key] || { error: { code: "not_found", message: key } }) });
  });
}

test.beforeEach(async ({ page }) => { await mockApi(page); });

test("loads baseline dashboard and default generator", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Create short-form video content" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Projects, jobs & temporary assets" })).toBeVisible();
  await expect(page.getByText("demo@jomveo.local · user")).toBeVisible();
  await expect(page.getByText("900", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate script" })).toBeVisible();
  await expect(page.getByText("This file is temporarily hosted by the provider. Download it before the link expires.").first()).toBeVisible();
});

test("project selection persists across reload", async ({ page }) => {
  await page.goto("/"); await page.getByLabel("Project").selectOption(project.id);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("jomveo.selectedProjectId"))).toBe(project.id);
  await page.reload(); await expect(page.getByLabel("Project")).toHaveValue(project.id);
});

test("creates and selects a project", async ({ page }) => {
  await page.unroute("**/api/**");
  await mockApi(page, { "POST /api/projects": route => route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ ...project, id: "new_project", name: "New Project" }) }) });
  await page.goto("/"); await page.getByPlaceholder("New project name").fill("New Project"); await page.getByRole("button", { name: "Create project" }).click();
  await expect(page.getByLabel("Project")).toHaveValue("new_project");
});

test("queue button sends project and idempotency headers", async ({ page }) => {
  let headers;
  await page.unroute("**/api/**");
  await mockApi(page, { "POST /api/jobs/scripts/generate": (route, request) => { headers = request.headers(); return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ job_id: "new_job" }) }); } });
  await page.goto("/"); await page.getByRole("button", { name: "Queue script job" }).click();
  await expect.poll(() => headers?.["x-project-id"]).toBe(project.id);
  expect(headers["idempotency-key"]).toBeTruthy(); expect(headers["content-type"]).toContain("application/json");
});

test("opens job details and direct asset link", async ({ page }) => {
  await page.goto("/"); await page.getByRole("button", { name: /script.generate/ }).click();
  await expect(page.getByText("Attempt 1/3")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open / Download" }).last()).toHaveAttribute("href", asset.url);
});

test("all generator tabs retain their baseline controls", async ({ page }) => {
  await page.goto("/");
  for (const name of ["Caption Style", "Art Style", "Animate Scenes", "Background Music", "Voiceover", "Video Creator", "60-Second Scripts"]) {
    await page.getByRole("tab", { name }).click(); await expect(page.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true");
  }
});

test("polls nonterminal jobs and stops after completion", async ({ page }) => {
  let calls = 0;
  await page.unroute("**/api/**");
  await mockApi(page, { [`GET /api/projects/${project.id}/jobs`]: route => { calls += 1; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ jobs: [{ ...job, status: calls === 1 ? "queued" : "completed" }], count: 1 }) }); } });
  await page.goto("/"); await expect(page.getByText("queued", { exact: true })).toBeVisible();
  await expect(page.getByText("completed", { exact: true })).toBeVisible({ timeout: 6000 });
  const completedCalls = calls; await page.waitForTimeout(4500); expect(calls).toBe(completedCalls);
});

test("synchronous script generation still renders its result", async ({ page }) => {
  await page.unroute("**/api/**");
  await mockApi(page, { "POST /api/scripts/generate": route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ title: "Baseline title", event_name: "Baseline event", script: "Baseline generated script text.", factual_basis: "Fixture", duration_seconds: 60, language: "English" }) }) });
  await page.goto("/"); await page.getByRole("button", { name: "Generate script" }).click();
  await expect(page.getByRole("heading", { name: "Baseline title" })).toBeVisible(); await expect(page.getByText("Baseline generated script text.")).toBeVisible();
});

test("synchronous music generation still renders audio output", async ({ page }) => {
  await page.unroute("**/api/**");
  await mockApi(page, { "POST /api/background-music/generate": route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ prompt: "fixture", style_name: "Fixture", number_of_songs: 1, output_format: "mp3", model: "fixture", audio_urls: ["https://provider.example/music.mp3"], raw_output: {} }) }) });
  await page.goto("/"); await page.getByRole("tab", { name: "Background Music" }).click(); await page.getByRole("button", { name: "Generate background music" }).click();
  await expect(page.getByRole("heading", { name: "Music Result" })).toBeVisible();
});

test("synchronous art generation still renders image output", async ({ page }) => {
  await page.unroute("**/api/**");
  await mockApi(page, { "POST /api/art-style/generate": route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ prompt: "fixture prompt", style_name: "Fixture", art_direction: "Fixture direction", styled_prompt: "fixture", model: "fixture", enable_safety_checker: false, safety_output: null, image_url: "https://provider.example/image.png", raw_output: {} }) }) });
  await page.goto("/"); await page.getByRole("tab", { name: "Art Style" }).click(); await page.getByRole("button", { name: "Generate art-style image" }).click();
  await expect(page.getByRole("heading", { name: "Art Result" })).toBeVisible(); await expect(page.getByRole("img")).toHaveAttribute("src", "https://provider.example/image.png");
});

test("persistent controls use exact routes, project, and idempotency headers", async ({ page }) => {
  const requests = [];
  let jobRefreshes = 0;
  await page.unroute("**/api/**");
  const handlers = {};
  handlers[`GET /api/projects/${project.id}/jobs`] = route => { jobRefreshes += 1; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ jobs: [job], count: 1 }) }); };
  for (const path of ["scripts", "voiceovers", "background-music", "art-style"]) handlers[`POST /api/jobs/${path}/generate`] = (route, request) => { requests.push({ path: new URL(request.url()).pathname, headers: request.headers() }); return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ job_id: `queued_${path}`, status: "queued" }) }); };
  await mockApi(page, handlers); await page.goto("/");
  for (const [tab, button] of [["60-Second Scripts", "Queue script job"], ["Voiceover", "Queue voiceover job"], ["Background Music", "Queue music job"], ["Art Style", "Queue art job"]]) {
    await page.getByRole("tab", { name: tab }).click();
    if (tab === "Voiceover") await page.getByLabel("Voiceover Text").fill("Narration for the persistent voiceover job.");
    await page.getByRole("button", { name: button }).click();
  }
  await expect.poll(() => requests.length).toBe(4);
  await expect(page.getByText(/Queued project job queued_art-style/)).toBeVisible();
  expect(jobRefreshes).toBeGreaterThanOrEqual(5);
  expect(requests.map(item => item.path)).toEqual(["/api/jobs/scripts/generate", "/api/jobs/voiceovers/generate", "/api/jobs/background-music/generate", "/api/jobs/art-style/generate"]);
  for (const request of requests) { expect(request.headers["x-project-id"]).toBe(project.id); expect(request.headers["idempotency-key"]).toBeTruthy(); }
});

test("empty voiceover text blocks persistent request with a friendly message", async ({ page }) => {
  let voiceoverRequests = 0;
  await page.unroute("**/api/**");
  await mockApi(page, { "POST /api/jobs/voiceovers/generate": route => { voiceoverRequests += 1; return route.abort(); } });
  await page.goto("/"); await page.getByRole("tab", { name: "Voiceover" }).click(); await page.getByRole("button", { name: "Queue voiceover job" }).click();
  await expect(page.getByText("Enter voiceover text before queueing this project job.")).toBeVisible();
  expect(voiceoverRequests).toBe(0);
});

test("scene sequence uses slash route after synchronous script prerequisite", async ({ page }) => {
  let queued;
  await page.unroute("**/api/**");
  await mockApi(page, {
    "POST /api/scripts/generate": route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ title: "Story", event_name: "Event", script: "A sufficiently long fixture script for scenes.", factual_basis: "Fixture", duration_seconds: 60, language: "English" }) }),
    "POST /api/jobs/art-style/scenes/generate": (route, request) => { queued = request; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ job_id: "scene_job", status: "queued" }) }); },
  });
  await page.goto("/"); await page.getByRole("button", { name: "Generate script" }).click(); await page.getByRole("tab", { name: "Art Style" }).click(); await page.getByRole("button", { name: "Queue scene sequence job" }).click();
  await expect.poll(() => queued && new URL(queued.url()).pathname).toBe("/api/jobs/art-style/scenes/generate");
});

test("missing project and prerequisites show friendly errors without wrong requests", async ({ page }) => {
  let queueCalls = 0; await page.unroute("**/api/**");
  await mockApi(page, { "POST /api/jobs/scene-animations/generate": route => { queueCalls += 1; return route.abort(); }, "POST /api/jobs/videos/generate": route => { queueCalls += 1; return route.abort(); } });
  await page.goto("/"); await page.getByLabel("Project").selectOption(""); await page.getByRole("button", { name: "Queue script job" }).click();
  await expect(page.getByText("Please select or create a project before queueing a project job.")).toBeVisible();
  await page.getByLabel("Project").selectOption(project.id); await page.getByRole("tab", { name: "Animate Scenes" }).click(); await page.getByRole("button", { name: "Queue animation job" }).click();
  await expect(page.getByText("Generate the required source content before queueing this project job.")).toBeVisible(); expect(queueCalls).toBe(0);
  await page.getByRole("tab", { name: "Caption Style" }).click(); await expect(page.getByText("Caption rendering currently runs synchronously.")).toBeVisible(); await expect(page.getByRole("button", { name: /Queue/ })).toHaveCount(0);
});
