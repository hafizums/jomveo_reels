export default function WarningCallout({children,tone="warning"}) { return <div className={`warning-callout warning-${tone}`}>{children}</div>; }
