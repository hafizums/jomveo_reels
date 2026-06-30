import AssetCard from "./AssetCard";
import EmptyState from "../ui/EmptyState";
import WarningCallout from "../ui/WarningCallout";
export default function AssetList({ assets }) { return <article className="dashboard-card"><h3>Project assets</h3><WarningCallout>Generated files are temporarily hosted by the provider. Please download them before the link expires.</WarningCallout>{assets.length?<div className="asset-grid">{assets.map(asset=><AssetCard key={asset.id} asset={asset}/>)}</div>:<EmptyState title="No assets yet" description="Completed jobs will register temporary provider assets here."/>}</article>; }
