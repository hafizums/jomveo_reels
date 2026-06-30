import { useEffect, useState, useCallback } from "react";
import { adminKey, backend } from "../lib/api";

export default function BillingRoute({ projectId }) {
  const [billing, setBilling] = useState(null);
  const [quotas, setQuotas] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [topUpAmount, setTopUpAmount] = useState(1000);
  const [toppingUp, setToppingUp] = useState(false);

  const loadBillingData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [billData, quotaData, txData] = await Promise.all([
        backend.billing(projectId),
        backend.quotas(projectId),
        backend.transactions(projectId),
      ]);
      setBilling(billData);
      setQuotas(quotaData);
      setTransactions(txData.transactions || []);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadBillingData();
  }, [loadBillingData]);

  const handleTopUpSubmit = async (e) => {
    e.preventDefault();
    if (!projectId || toppingUp) return;

    setToppingUp(true);
    try {
      await backend.topUp(projectId, {
        amount_credits: Number(topUpAmount),
        description: "Admin workflow top-up",
      });
      await loadBillingData();
      alert(`Successfully added ${topUpAmount} credits!`);
    } catch (err) {
      alert("Top-up failed: " + err.message);
    } finally {
      setToppingUp(false);
    }
  };

  if (!projectId) {
    return (
      <div className="empty-state">
        <p>Please select a project workspace to view billing & credit data.</p>
      </div>
    );
  }

  return (
    <div className="stepper-step-container">
      <header style={{ marginBottom: 24 }}>
        <span className="eyebrow">Project billing</span>
        <h1>Credits & Quotas</h1>
        <p>Manage API credits, check limits, and view transaction history.</p>
      </header>

      {error && <div className="message error" style={{ marginBottom: 20 }}>{error}</div>}

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}>
          <div className="spinner" /> Loading billing info...
        </div>
      ) : (
        <>
          {/* Metrics Grid */}
          <div className="grid-cols-3" style={{ marginBottom: 24 }}>
            <div className="dashboard-card" style={{ margin: 0 }}>
              <h3>Available Balance</h3>
              <p className="metric" style={{ fontSize: "2.5rem" }}>
                {billing?.balance_credits || 0}
              </p>
              <p style={{ fontSize: 12 }}>Credits available for generation</p>
            </div>

            <div className="dashboard-card" style={{ margin: 0 }}>
              <h3>Reserved Balance</h3>
              <p className="metric" style={{ fontSize: "2.5rem", background: "linear-gradient(135deg, var(--accent-indigo) 0%, var(--accent-violet) 100%)" }}>
                {billing?.reserved_credits || 0}
              </p>
              <p style={{ fontSize: 12 }}>Credits locked in queued runs</p>
            </div>

            <div className="dashboard-card" style={{ margin: 0 }}>
              <h3>Lifetime Spend</h3>
              <p className="metric" style={{ fontSize: "2.5rem", background: "linear-gradient(135deg, var(--accent-emerald) 0%, var(--accent-indigo) 100%)" }}>
                {billing?.lifetime_used_credits || 0}
              </p>
              <p style={{ fontSize: 12 }}>Total credits consumed by project</p>
            </div>
          </div>

          <div className="grid-cols-2" style={{ marginBottom: 24, alignItems: "start" }}>
            {/* Quotas Details */}
            <div className="dashboard-card" style={{ margin: 0 }}>
              <h3>Project Quota Limits</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-light)", paddingBottom: 6 }}>
                  <span style={{ fontSize: 13, color: "#9ca3af" }}>Daily Job Limit</span>
                  <strong style={{ fontSize: 13 }}>{quotas?.daily_job_limit || "Unlimited"}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-light)", paddingBottom: 6 }}>
                  <span style={{ fontSize: 13, color: "#9ca3af" }}>Monthly Job Limit</span>
                  <strong style={{ fontSize: 13 }}>{quotas?.monthly_job_limit || "Unlimited"}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-light)", paddingBottom: 6 }}>
                  <span style={{ fontSize: 13, color: "#9ca3af" }}>Daily Credit Limit</span>
                  <strong style={{ fontSize: 13 }}>{quotas?.daily_credit_limit || "Unlimited"}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-light)", paddingBottom: 6 }}>
                  <span style={{ fontSize: 13, color: "#9ca3af" }}>Monthly Credit Limit</span>
                  <strong style={{ fontSize: 13 }}>{quotas?.monthly_credit_limit || "Unlimited"}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 13, color: "#9ca3af" }}>Max Concurrency Limit</span>
                  <strong style={{ fontSize: 13 }}>{quotas?.max_concurrent_jobs || "Unlimited"}</strong>
                </div>
              </div>
            </div>

            {/* Admin top-up (only if adminKey is defined) */}
            {adminKey && (
              <div className="dashboard-card" style={{ margin: 0 }}>
                <h3>Credit Top-Up (Admin)</h3>
                <p style={{ fontSize: 12, marginBottom: 16 }}>Simulate credit top-ups in this workspace project.</p>
                
                <form onSubmit={handleTopUpSubmit} style={{ display: "flex", gap: 10 }}>
                  <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                    <input
                      type="number"
                      min="10"
                      max="10000"
                      required
                      placeholder="Credits (e.g. 1000)"
                      value={topUpAmount}
                      onChange={(e) => setTopUpAmount(e.target.value)}
                      disabled={toppingUp}
                    />
                  </div>
                  <button type="submit" className="btn-primary" disabled={toppingUp}>
                    {toppingUp ? "Adding..." : "Add Credits"}
                  </button>
                </form>
              </div>
            )}
          </div>

          {/* Transactions List */}
          <div className="dashboard-card" style={{ margin: 0 }}>
            <h3>Recent Transactions</h3>
            <div style={{ marginTop: 14, overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid var(--color-border)", color: "#9ca3af" }}>
                    <th style={{ padding: "8px 12px" }}>Date</th>
                    <th style={{ padding: "8px 12px" }}>Type</th>
                    <th style={{ padding: "8px 12px" }}>Description</th>
                    <th style={{ padding: "8px 12px", textAlign: "right" }}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => {
                    const isConsumed = tx.amount_credits < 0;
                    return (
                      <tr key={tx.id} style={{ borderBottom: "1px solid var(--color-border-light)" }}>
                        <td style={{ padding: "10px 12px" }}>{new Date(tx.created_at).toLocaleString()}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <span className="badge completed" style={{ fontSize: 9, background: isConsumed ? "rgba(244,63,94,0.1)" : "rgba(16,185,129,0.1)", color: isConsumed ? "var(--accent-coral)" : "var(--accent-emerald)" }}>
                            {tx.type}
                          </span>
                        </td>
                        <td style={{ padding: "10px 12px", color: "#d1d5db" }}>{tx.description}</td>
                        <td style={{ padding: "10px 12px", textAlign: "right", fontWeight: 700, color: isConsumed ? "var(--accent-coral)" : "var(--accent-emerald)" }}>
                          {isConsumed ? "" : "+"}{tx.amount_credits}
                        </td>
                      </tr>
                    );
                  })}
                  {transactions.length === 0 && (
                    <tr>
                      <td colSpan="4" style={{ padding: "20px", textAlign: "center", color: "#6b7280" }}>
                        No transactions found for this project.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
