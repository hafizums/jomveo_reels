export default function VoiceStylePicker({
  styles,
  selectedStyleId,
  onSelect,
}) {
  return (
    <section className="preset-grid" aria-label="Voice styles">
      {styles.map((style) => {
        const isActive = style.id === selectedStyleId;

        return (
          <button
            key={style.id}
            type="button"
            className={`preset-card ${isActive ? "is-selected" : ""}`}
            onClick={() => onSelect(style)}
            aria-pressed={isActive}
          >
            <div className="preset-copy">
              <strong>{style.name}</strong>
              <span>{style.description}</span>
            </div>
            <span className={`preset-check ${isActive ? "is-visible" : ""}`}>
              &#10003;
            </span>
          </button>
        );
      })}
    </section>
  );
}
