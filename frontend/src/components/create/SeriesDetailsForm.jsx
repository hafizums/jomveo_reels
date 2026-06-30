import CreateProjectForm from "../dashboard/CreateProjectForm";
import ProjectSelector from "../dashboard/ProjectSelector";

export default function SeriesDetailsForm({ form, onChange, projects, projectId, onProjectChange, onCreateProject, creatingProject, languages, tones, durations }) {
  return (
    <div className="create-form-grid">
      <div className="create-field-wide">
        <ProjectSelector projects={projects} value={projectId} onChange={onProjectChange} />
      </div>
      <div className="create-field-wide create-project-row">
        <span className="helper-text">Need a workspace first?</span>
        <CreateProjectForm onSubmit={onCreateProject} submitting={creatingProject} />
      </div>
      <label>
        Series name
        <input name="seriesName" value={form.seriesName} onChange={onChange} placeholder="Midnight Malaysia" />
      </label>
      <label>
        Topic
        <input name="topic" value={form.topic} onChange={onChange} placeholder="A case, idea, person, or theme" />
      </label>
      <label>
        Language
        <select name="language" value={form.language} onChange={onChange}>{languages.map(value => <option key={value}>{value}</option>)}</select>
      </label>
      <label>
        Tone
        <select name="tone" value={form.tone} onChange={onChange}>{tones.map(value => <option key={value}>{value}</option>)}</select>
      </label>
      <label>
        Duration
        <select name="duration" value={form.duration} onChange={onChange}>{durations.map(value => <option key={value} value={value}>{value} seconds</option>)}</select>
      </label>
      {form.nicheId === "custom" ? (
        <label className="create-field-wide">
          Custom niche prompt
          <textarea name="customNiche" rows="4" value={form.customNiche} onChange={onChange} placeholder="Describe the stories this series should create." />
        </label>
      ) : null}
    </div>
  );
}
