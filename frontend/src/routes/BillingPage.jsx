import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import AdminTopUpForm from "../components/dashboard/AdminTopUpForm";
import BillingSummaryCard from "../components/dashboard/BillingSummaryCard";
import QuotaSummaryCard from "../components/dashboard/QuotaSummaryCard";
import TransactionHistory from "../components/dashboard/TransactionHistory";
import ErrorBanner from "../components/ui/ErrorBanner";
import LoadingState from "../components/ui/LoadingState";
import { adminKey, backend } from "../lib/api";

export default function BillingPage({ onProjectChange }) {
  const { projectId } = useParams();
  const [data, setData] = useState(null);
  const [topUp, setTopUp] = useState(1000);
  const [loading, setLoading] = useState(true);
  const [toppingUp, setToppingUp] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [billing, transactions, usage, quotas] = await Promise.all([backend.billing(projectId), backend.transactions(projectId), backend.usage(projectId), backend.quotas(projectId)]);
      setData({ billing, transactions: transactions.transactions, usage, quotas });
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { onProjectChange(projectId); load(); }, [projectId]);

  const submitTopUp = async event => {
    event.preventDefault();
    setToppingUp(true);
    try {
      await backend.topUp(projectId, { amount_credits: Number(topUp), description: "Local admin top-up" });
      await load();
    } catch (topUpError) {
      setError(topUpError.message);
    } finally {
      setToppingUp(false);
    }
  };

  return (
    <section className="route-page">
      <header className="page-header"><div><p className="eyebrow">Project workspace</p><h1>Billing and quotas</h1><p>Review internal credits, usage limits, and recent transactions.</p></div></header>
      <ErrorBanner message={error} />
      {loading ? <LoadingState label="Loading billing data…" /> : data ? <><div className="dashboard-grid"><BillingSummaryCard billing={data.billing} /><QuotaSummaryCard usage={data.usage} quotas={data.quotas} /><TransactionHistory transactions={data.transactions} /></div>{adminKey ? <AdminTopUpForm amount={topUp} onAmountChange={setTopUp} onSubmit={submitTopUp} submitting={toppingUp} /> : null}</> : null}
    </section>
  );
}
