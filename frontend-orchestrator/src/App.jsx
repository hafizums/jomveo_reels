import { useState, useEffect, useCallback } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { backend, defaultProjectId } from "./lib/api";
import Sidebar from "./components/Sidebar";
import ProjectModal from "./components/ProjectModal";
import OrchestratorRoute from "./routes/OrchestratorRoute";
import ProjectsRoute from "./routes/ProjectsRoute";
import AssetsRoute from "./routes/AssetsRoute";
import BillingRoute from "./routes/BillingRoute";
import JobsRoute from "./routes/JobsRoute";
import "./styles.css";

export default function App() {
  const [me, setMe] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(
    localStorage.getItem("jomveo.selectedProjectId") || defaultProjectId
  );
  
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const selectProject = useCallback((projectId) => {
    setSelectedProjectId(projectId);
    if (projectId) {
      localStorage.setItem("jomveo.selectedProjectId", projectId);
    } else {
      localStorage.removeItem("jomveo.selectedProjectId");
    }
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [identity, projectData] = await Promise.all([
        backend.me(),
        backend.projects(),
      ]);
      setMe(identity);
      setProjects(projectData.projects || []);

      // Pre-select first project if none is selected
      if (!selectedProjectId && projectData.projects?.[0]) {
        selectProject(projectData.projects[0].id);
      }
    } catch (err) {
      setError(err.message);
    }
  }, [selectedProjectId, selectProject]);

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateProject = async (projectName) => {
    setSubmitting(true);
    try {
      const newProj = await backend.createProject({ name: projectName });
      setProjects((current) => [newProj, ...current]);
      selectProject(newProj.id);
      return newProj;
    } catch (err) {
      alert("Failed to create project: " + err.message);
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="app-layout">
      {/* Sidebar with selection controls */}
      <Sidebar
        projects={projects}
        selectedProjectId={selectedProjectId}
        onProjectChange={selectProject}
        onCreateProjectClick={() => setModalOpen(true)}
        me={me}
      />

      {/* Main viewport */}
      <main className="main-content">
        {error && <div className="message error">{error}</div>}

        <Routes>
          <Route
            path="/orchestrator"
            element={<OrchestratorRoute projectId={selectedProjectId} />}
          />
          <Route
            path="/projects"
            element={
              <ProjectsRoute
                selectedProjectId={selectedProjectId}
                onProjectChange={selectProject}
                triggerRefreshProjects={loadData}
              />
            }
          />
          <Route
            path="/assets"
            element={<AssetsRoute projectId={selectedProjectId} />}
          />
          <Route
            path="/billing"
            element={<BillingRoute projectId={selectedProjectId} />}
          />
          <Route
            path="/jobs"
            element={<JobsRoute projectId={selectedProjectId} />}
          />
          <Route path="*" element={<Navigate to="/orchestrator" replace />} />
        </Routes>
      </main>

      {/* Modal Dialog */}
      <ProjectModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleCreateProject}
        submitting={submitting}
      />
    </div>
  );
}
