import { NavLink } from "react-router-dom";

export default function Sidebar({
  projects = [],
  selectedProjectId = "",
  onProjectChange,
  onCreateProjectClick,
  me,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span>🎬</span> Jomveo Studio
      </div>

      <div className="project-selector-box">
        <label>Active Project</label>
        <div className="project-dropdown-row">
          <select
            className="project-dropdown"
            value={selectedProjectId}
            onChange={(e) => onProjectChange(e.target.value)}
          >
            <option value="">-- Select Project --</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="new-project-btn"
            title="Create New Project"
            onClick={onCreateProjectClick}
          >
            +
          </button>
        </div>
      </div>

      <nav className="nav-menu-box">
        <ul className="nav-menu">
          <li>
            <NavLink to="/orchestrator" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <span>🚀</span> Video Stepper
            </NavLink>
          </li>
          <li>
            <NavLink to="/projects" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <span>📋</span> Projects CRUD
            </NavLink>
          </li>
          <li>
            <NavLink to="/assets" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <span>📂</span> Assets Library
            </NavLink>
          </li>
          <li>
            <NavLink to="/billing" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <span>💳</span> Billing & Quotas
            </NavLink>
          </li>
          <li>
            <NavLink to="/jobs" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <span>⚙️</span> Background Jobs
            </NavLink>
          </li>
        </ul>
      </nav>

      <div className="sidebar-footer">
        {me ? (
          <div>
            <p style={{ fontWeight: 700, color: "#e2e8f0" }}>{me.display_name || me.email}</p>
            <p style={{ fontSize: "10px", textTransform: "uppercase" }}>{me.role}</p>
          </div>
        ) : (
          <p>Loading identity...</p>
        )}
      </div>
    </aside>
  );
}
