import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Dashboard from "../components/Dashboard";

export default function ProjectPage({ onProjectChange, refreshToken }) {
  const { projectId } = useParams();
  const navigate = useNavigate();

  useEffect(() => onProjectChange(projectId), [onProjectChange, projectId]);

  return (
    <>
      <header className="page-header">
        <div><p className="eyebrow">Project workspace</p><h1>Project overview</h1></div>
      </header>
      <Dashboard
        projectId={projectId}
        onProjectChange={(nextProjectId) => {
          onProjectChange(nextProjectId);
          if (nextProjectId) navigate(`/projects/${nextProjectId}`);
        }}
        refreshToken={refreshToken}
      />
    </>
  );
}
