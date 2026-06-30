// Pipeline step definitions — order defines the recommended workflow
const STEPS = [
  { id: "scripts",   num: 1, label: "Script",         hint: "Write your story" },
  { id: "voiceover", num: 2, label: "Voiceover",      hint: "Narrate the script" },
  { id: "art",       num: 3, label: "Art Style",       hint: "Generate visuals" },
  { id: "animation", num: 4, label: "Animate Scenes",  hint: "Add motion" },
  { id: "music",     num: 5, label: "Background Music", hint: "Set the mood" },
  { id: "video",     num: 6, label: "Video Creator",   hint: "Assemble the video" },
  // divider before utility
  { id: "captions",  num: 7, label: "Caption Style",   hint: "Burn-in captions", utility: true },
];

export default function GeneratorTabs({ activeTab, onChange, completedSteps = {} }) {
  return (
    <nav className="pipeline" aria-label="Generation pipeline">
      <span className="pipeline-label">Pipeline</span>

      {STEPS.map((step, i) => {
        const isDivider = step.utility && i > 0;
        const isDone = Boolean(completedSteps[step.id]);
        const isActive = activeTab === step.id;

        return (
          <div key={step.id}>
            {isDivider ? <div className="pipeline-divider" /> : null}
            <button
              type="button"
              className={`pipeline-step${isActive ? " is-active" : ""}${isDone ? " is-done" : ""}`}
              onClick={() => onChange(step.id)}
              aria-current={isActive ? "step" : undefined}
              title={step.hint}
            >
              <span className="step-num">{step.num}</span>
              <span className="step-info">
                <span className="step-name">{step.label}</span>
                {isDone ? <span className="step-done-badge" /> : null}
              </span>
            </button>
          </div>
        );
      })}
    </nav>
  );
}
