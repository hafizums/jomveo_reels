import { NavLink, useLocation } from "react-router-dom";

const navClass = ({ isActive }) => `app-nav-link${isActive ? " is-active" : ""}`;

export default function AppShell({ selectedProjectId, children }) {
  const location = useLocation();
  const projectBase = selectedProjectId ? `/projects/${selectedProjectId}` : "/dashboard";
  const projectNavClass = (section) => ({ isActive }) => {
    const jobDetailActive = section === "jobs" && location.pathname.startsWith("/jobs/");
    return navClass({ isActive: Boolean(selectedProjectId) && (isActive || jobDetailActive) });
  };

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <NavLink className="app-brand" to="/dashboard">Jomveo</NavLink>
        <nav className="app-nav" aria-label="Workspace navigation">
          <NavLink className={navClass} to="/dashboard">Dashboard</NavLink>
          <NavLink className={navClass} to="/generate">Generate</NavLink>
          <NavLink className={projectNavClass("jobs")} to={`${projectBase}${selectedProjectId ? "/jobs" : ""}`}>Jobs</NavLink>
          <NavLink className={projectNavClass("assets")} to={`${projectBase}${selectedProjectId ? "/assets" : ""}`}>Assets</NavLink>
          <NavLink className={projectNavClass("billing")} to={`${projectBase}${selectedProjectId ? "/billing" : ""}`}>Billing</NavLink>
        </nav>
      </header>
      <main className="page">{children}</main>
    </div>
  );
}
