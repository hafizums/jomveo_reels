export default function LoadingState({ label }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 40, gap: 12, color: "#9ca3af" }}>
      <div className="spinner" style={{ width: 24, height: 24 }} />
      <span>{label || "Loading..."}</span>
    </div>
  );
}
