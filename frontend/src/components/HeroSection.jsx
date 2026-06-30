export default function HeroSection() {
  return (
    <section className="hero">
      <p className="eyebrow">
        <span>✦</span>
        React + FastAPI + WaveSpeed
      </p>
      <h1>Create short-form<br />video content</h1>
      <p className="lede">
        Generate scripts, voiceovers, background music, styled artwork, and
        burned-in captions for short-form videos.
      </p>

      {/* "How it works" mini flow */}
      <div className="flow-chips" aria-label="Recommended workflow">
        <span className="flow-chip"><span className="flow-chip-num">1</span>Script</span>
        <span className="flow-arrow">→</span>
        <span className="flow-chip"><span className="flow-chip-num">2</span>Voiceover</span>
        <span className="flow-arrow">→</span>
        <span className="flow-chip"><span className="flow-chip-num">3</span>Art</span>
        <span className="flow-arrow">→</span>
        <span className="flow-chip"><span className="flow-chip-num">4</span>Music</span>
        <span className="flow-arrow">→</span>
        <span className="flow-chip"><span className="flow-chip-num">5</span>Video</span>
      </div>
    </section>
  );
}
