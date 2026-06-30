import Dashboard from "../components/Dashboard";
import HeroSection from "../components/HeroSection";

export default function DashboardPage({ projectId, onProjectChange, refreshToken }) {
  return (
    <>
      <HeroSection />
      <Dashboard projectId={projectId} onProjectChange={onProjectChange} refreshToken={refreshToken} />
    </>
  );
}
