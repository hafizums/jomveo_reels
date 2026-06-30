import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";
import AppShell from "./AppShell";
import NotFoundPage from "./NotFoundPage";

describe("workspace routing", () => {
  test("app shell links selected-project workspace pages", () => {
    render(<MemoryRouter initialEntries={["/dashboard"]}><AppShell selectedProjectId="project_demo"><p>Content</p></AppShell></MemoryRouter>);
    expect(screen.getByRole("navigation", { name: "Workspace navigation" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("link", { name: "Generate" })).toHaveAttribute("href", "/generate");
    expect(screen.getByRole("link", { name: "Jobs" })).toHaveAttribute("href", "/projects/project_demo/jobs");
    expect(screen.getByRole("link", { name: "Assets" })).toHaveAttribute("href", "/projects/project_demo/assets");
    expect(screen.getByRole("link", { name: "Billing" })).toHaveAttribute("href", "/projects/project_demo/billing");
  });

  test("project navigation safely falls back to dashboard", () => {
    render(<MemoryRouter><AppShell selectedProjectId=""><p>Content</p></AppShell></MemoryRouter>);
    for (const name of ["Jobs", "Assets", "Billing"]) expect(screen.getByRole("link", { name })).toHaveAttribute("href", "/dashboard");
  });

  test("not found page links back to dashboard", () => {
    render(<MemoryRouter><NotFoundPage /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "This page does not exist." })).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to dashboard" })).toHaveAttribute("href", "/dashboard");
  });
});
