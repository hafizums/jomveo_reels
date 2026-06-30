export default function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="message error" role="alert" style={{ marginBottom: 16 }}>
      {message}
    </div>
  );
}
