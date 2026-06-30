import { useEffect, useState } from "react";
import { backend } from "../lib/api";

export default function AssetsRoute({ projectId }) {
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!projectId) return;

    let active = true;
    setLoading(true);
    backend
      .assets(projectId)
      .then((data) => {
        if (active) {
          setAssets(data.assets || []);
          setError("");
        }
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [projectId]);

  if (!projectId) {
    return (
      <div className="empty-state">
        <p>Please select a project workspace to view assets.</p>
      </div>
    );
  }

  return (
    <div className="stepper-step-container">
      <header style={{ marginBottom: 24 }}>
        <span className="eyebrow">Project storage</span>
        <h1>Temporary Assets</h1>
        <p>Browse and download files generated for this project in the last 7 days.</p>
      </header>

      {error && <div className="message error" style={{ marginBottom: 20 }}>{error}</div>}

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}>
          <div className="spinner" /> Loading assets...
        </div>
      ) : assets.length === 0 ? (
        <div className="empty-state">
          <p>No assets generated for this project yet. Start a video creation stepper!</p>
        </div>
      ) : (
        <div className="asset-grid">
          {assets.map((asset) => {
            const isImage = ["image", "art"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(jpeg|jpg|png|webp)/i);
            const isAudio = ["audio", "voiceover", "music"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(mp3|wav|ogg)/i);
            const isVideo = ["video", "clip"].includes(asset.asset_type.toLowerCase()) || asset.url.match(/\.(mp4|webm)/i);

            // Compute expiry warning
            const expires = asset.expires_at ? new Date(asset.expires_at) : null;
            const hoursLeft = expires ? (expires.getTime() - Date.now()) / (1000 * 60 * 60) : 999;
            const expiringSoon = expires && hoursLeft > 0 && hoursLeft <= 24;
            const expired = expires && hoursLeft <= 0;

            return (
              <div
                key={asset.id}
                className="asset-card"
                style={{
                  opacity: expired ? 0.5 : 1,
                  borderColor: expiringSoon ? "var(--accent-amber)" : "var(--color-border)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="badge completed" style={{ fontSize: 10 }}>
                    {asset.asset_type}
                  </span>
                  {!expired && (
                    <a href={asset.url} target="_blank" rel="noreferrer" download style={{ fontSize: 12 }}>
                      Download ↗
                    </a>
                  )}
                </div>

                <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {isImage && !expired && (
                    <img src={asset.url} alt="asset preview" className="asset-preview-thumb" />
                  )}
                  {isVideo && !expired && (
                    <video src={asset.url} controls className="asset-preview-thumb" style={{ objectFit: "contain" }} />
                  )}
                  {isAudio && !expired && (
                    <audio src={asset.url} controls style={{ width: "100%" }} />
                  )}
                  {(!isImage && !isVideo && !isAudio) || expired ? (
                    <div
                      style={{
                        padding: "20px 10px",
                        textAlign: "center",
                        fontSize: 12,
                        color: "#6b7280",
                        width: "100%",
                      }}
                    >
                      {expired ? "CDN Asset Expired" : asset.filename || "Binary Data File"}
                    </div>
                  ) : null}
                </div>

                <div style={{ fontSize: 11, color: "#6b7280", marginTop: 4 }}>
                  <p style={{ wordBreak: "break-all" }}>{asset.filename || "unnamed-asset"}</p>
                  {expires && (
                    <p style={{ color: expiringSoon ? "var(--accent-amber)" : expired ? "var(--accent-coral)" : "#6b7280", fontWeight: expiringSoon || expired ? 700 : 500, marginTop: 2 }}>
                      {expired
                        ? "Expired"
                        : expiringSoon
                        ? `Expiring in ${Math.round(hoursLeft)} hrs`
                        : `Expires: ${expires.toLocaleDateString()}`}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
