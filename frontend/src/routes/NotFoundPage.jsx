import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="panel not-found">
      <p className="eyebrow">404</p>
      <h1>This page does not exist.</h1>
      <Link to="/dashboard">Back to dashboard</Link>
    </section>
  );
}
