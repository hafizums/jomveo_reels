export default function NichePresetGrid({ presets, selectedId, onSelect }) {
  return (
    <div className="create-niche-grid" aria-label="Niche presets">
      {presets.map((preset) => (
        <button
          key={preset.id}
          type="button"
          className={`create-choice-card${selectedId === preset.id ? " is-selected" : ""}`}
          aria-pressed={selectedId === preset.id}
          onClick={() => onSelect(preset.id)}
        >
          <span>{preset.title}</span>
          <small>{selectedId === preset.id ? "Selected" : "Choose niche"}</small>
        </button>
      ))}
    </div>
  );
}
