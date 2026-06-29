export default function GeneratorTabs({ activeTab, onChange }) {
  return (
    <div className="tabs" role="tablist" aria-label="Generator tabs">
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "scripts"}
        className={`tab-button ${activeTab === "scripts" ? "is-active" : ""}`}
        onClick={() => onChange("scripts")}
      >
        60-Second Scripts
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "captions"}
        className={`tab-button ${activeTab === "captions" ? "is-active" : ""}`}
        onClick={() => onChange("captions")}
      >
        Caption Style
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "art"}
        className={`tab-button ${activeTab === "art" ? "is-active" : ""}`}
        onClick={() => onChange("art")}
      >
        Art Style
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "animation"}
        className={`tab-button ${activeTab === "animation" ? "is-active" : ""}`}
        onClick={() => onChange("animation")}
      >
        Animate Scenes
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "music"}
        className={`tab-button ${activeTab === "music" ? "is-active" : ""}`}
        onClick={() => onChange("music")}
      >
        Background Music
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "voiceover"}
        className={`tab-button ${activeTab === "voiceover" ? "is-active" : ""}`}
        onClick={() => onChange("voiceover")}
      >
        Voiceover
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "video"}
        className={`tab-button ${activeTab === "video" ? "is-active" : ""}`}
        onClick={() => onChange("video")}
      >
        Video Creator
      </button>
    </div>
  );
}
