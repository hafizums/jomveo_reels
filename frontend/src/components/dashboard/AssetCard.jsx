export default function AssetCard({ asset }) {
  return <article className={`asset-card asset-${asset.status}`}><div className="dashboard-row"><strong>{asset.asset_type}</strong><span className="status-badge">{asset.status}</span></div>{asset.expires_at ? <small>May expire: {new Date(asset.expires_at).toLocaleString()}</small> : null}{asset.warning ? <p className="download-warning">{asset.warning}</p> : null}<a href={asset.url} target="_blank" rel="noreferrer">Open / Download</a></article>;
}
