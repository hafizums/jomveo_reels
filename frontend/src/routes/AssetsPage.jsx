import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import AssetList from "../components/dashboard/AssetList";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";
import { backend } from "../lib/api";

export default function AssetsPage({ onProjectChange }) {
  const { projectId } = useParams();
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    onProjectChange(projectId);
    let active = true;
    setLoading(true);
    backend.assets(projectId).then(data => { if (active) { setAssets(data.assets); setError(""); } }).catch(loadError => { if (active) setError(loadError.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [onProjectChange, projectId]);

  return (
    <section className="route-page">
      <header className="page-header"><div><p className="eyebrow">Project workspace</p><h1>Project assets</h1><p>Review and download temporary provider-hosted output.</p></div></header>
      <ErrorBanner message={error} />
      {loading ? <LoadingState label="Loading project assets…" /> : <AssetList assets={assets} />}
    </section>
  );
}
