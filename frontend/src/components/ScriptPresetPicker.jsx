export default function ScriptPresetPicker({ presets, selectedPresetId, onSelect }) {
  return (
    <section className="preset-grid" aria-label="Script presets">
      {presets.map((preset) => {
        const isActive = preset.id === selectedPresetId;
        return (
          <button
            key={preset.id}
            type="button"
            className={`preset-card${isActive ? " is-selected" : ""}`}
            onClick={() => onSelect(preset)}
            aria-pressed={isActive}
          >
            <div className="preset-copy">
              <strong>{preset.title}</strong>
              <span>{preset.description}</span>
            </div>
            <span className={`preset-check${isActive ? " is-visible" : ""}`}>
              ✓
            </span>
          </button>
        );
      })}
    </section>
  );
}
