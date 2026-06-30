export default function ProjectSelector({ projects, value, onChange }) {
  return <label>Project<select value={value} onChange={event => onChange(event.target.value)}><option value="">Select a project</option>{projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>;
}
