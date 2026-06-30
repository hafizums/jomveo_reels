export default function CreateReviewPanel({ summary }) {
  return (
    <div className="create-review-grid">
      {Object.entries(summary).map(([label, value]) => (
        <article key={label} className="create-summary-card">
          <small>{label}</small>
          <strong>{value || "Not selected"}</strong>
        </article>
      ))}
    </div>
  );
}
