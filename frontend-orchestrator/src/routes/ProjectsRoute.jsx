import { useEffect, useState } from "react";
import { backend } from "../lib/api";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";

export default function ProjectsRoute({ selectedProjectId, onProjectChange, triggerRefreshProjects }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadProjects = async () => {
    setLoading(true);
    try {
      const data = await backend.projects();
      setProjects(data.projects || []);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <div className="stepper-step-container">
      <header style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <span className="eyebrow">Studio workspaces</span>
          <h1>Projects Management</h1>
          <p>Organize generation configurations, assets, and billing isolation.</p>
        </div>
      </header>

      {error && <div className="message error" style={{ marginBottom: 20 }}>{error}</div>}

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}>
          <div className="spinner" /> Loading projects...
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {projects.map((p) => {
            const isSelected = p.id === selectedProjectId;
            return (
              <div
                key={p.id}
                className="dashboard-card"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  borderColor: isSelected ? "var(--accent-violet)" : "var(--color-border)",
                  boxShadow: isSelected ? "var(--shadow-violet)" : "none",
                  margin: 0,
                }}
              >
                <div>
                  <h3 style={{ margin: 0 }}>{p.name}</h3>
                  <code style={{ fontSize: 11, background: "rgba(255,255,255,0.03)" }}>{p.id}</code>
                  <p style={{ fontSize: 12, marginTop: 4 }}>
                    Slug: <code>{p.slug}</code> · Created: {new Date(p.created_at).toLocaleString()}
                  </p>
                </div>

                <div style={{ display: "flex", gap: 10 }}>
                  {isSelected ? (
                    <span className="badge completed">Selected Workspace</span>
                  ) : (
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ padding: "6px 16px", fontSize: 12 }}
                      onClick={() => {
                        onProjectChange(p.id);
                        triggerRefreshProjects();
                      }}
                    >
                      Select Workspace
                    </button>
                  )}
                </div>
              </div>
            );
          })}

          {projects.length === 0 && (
            <div className="empty-state">
              <p>No projects found. Click the "+" button in the sidebar to create one!</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
