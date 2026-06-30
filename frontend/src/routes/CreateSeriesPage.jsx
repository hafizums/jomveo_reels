import { useEffect, useState } from "react";
import CreateSeriesWizard from "../components/create/CreateSeriesWizard";
import { backend } from "../lib/api";

export default function CreateSeriesPage({ projectId, onProjectChange, api = backend }) {
  const [projects, setProjects] = useState([]);
  const [creatingProject, setCreatingProject] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api.projects().then(data => {
      if (!active) return;
      setProjects(data.projects);
      if (!projectId && data.projects[0]) onProjectChange(data.projects[0].id);
      setError("");
    }).catch(loadError => { if (active) setError(loadError.message); });
    return () => { active = false; };
  }, [api, onProjectChange, projectId]);

  const createProject = async name => {
    setCreatingProject(true);
    try {
      const project = await api.createProject({ name });
      setProjects(current => [project, ...current]);
      onProjectChange(project.id);
      setError("");
    } catch (createError) {
      setError(createError.message);
    } finally {
      setCreatingProject(false);
    }
  };

  return (
    <section className="create-series-page">
      <header className="create-series-hero">
        <p className="eyebrow">Guided creation</p>
        <h1>Create New Series</h1>
        <p className="lede">Turn one niche idea into a repeatable faceless video series.</p>
        <p className="helper-text">Generate a script, visuals, voiceover, captions, and final video from one guided flow.</p>
      </header>
      <CreateSeriesWizard projects={projects} projectId={projectId} onProjectChange={onProjectChange} onCreateProject={createProject} creatingProject={creatingProject} onQueueFirstVideo={payload => api.createJob("scripts", payload, projectId)} externalError={error} />
    </section>
  );
}
