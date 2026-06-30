import HeroSection from "../components/HeroSection";

export default function GeneratePage({ children }) {
  return (
    <>
      <HeroSection />
      <header className="page-header">
        <div>
          <p className="eyebrow">Generator Studio</p>
          <h2>Generate project media</h2>
          <p>Use the synchronous tools or queue supported work for the selected project.</p>
        </div>
      </header>
      {children}
    </>
  );
}
