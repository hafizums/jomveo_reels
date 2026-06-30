import AssetCard from "./AssetCard";
export default function AssetList({ assets }) { return <article className="dashboard-card"><h3>Project assets</h3><p className="download-warning">Generated files are temporarily hosted by the provider. Please download them before the link expires.</p><div className="asset-grid">{assets.map(asset=><AssetCard key={asset.id} asset={asset}/>)}</div></article>; }
