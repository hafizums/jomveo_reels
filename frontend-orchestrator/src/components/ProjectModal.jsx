import { useState } from "react";

export default function ProjectModal({ isOpen, onClose, onSubmit, submitting }) {
  const [name, setName] = useState("");

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit(name.trim()).then(() => {
      setName("");
      onClose();
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h3>Create New Project</h3>
          <button
            type="button"
            className="drawer-close-btn"
            style={{ fontSize: 16, padding: "2px 6px" }}
            onClick={onClose}
          >
            ✕
          </button>
        </header>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="modal-project-name">Project Name</label>
            <input
              id="modal-project-name"
              type="text"
              required
              placeholder="e.g. Niche Malay Reels"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting || !name.trim()}
            >
              {submitting ? "Creating..." : "Create Project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
