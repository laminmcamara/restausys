import { useState, useEffect, useCallback } from "react";
import {
  CircleDollarSign,
  TrendingUp,
  Clock,
  CheckCircle2,
  X,
} from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getAuthHeaders() {
  const token =
    localStorage.getItem("accessToken") || localStorage.getItem("access");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

const PAYMENT_METHODS = ["cash", "card", "mobile", "online"];

function methodBadge(method) {
  const colors = {
    cash: "bg-emerald-100 text-emerald-800",
    card: "bg-blue-100 text-blue-800",
    mobile: "bg-violet-100 text-violet-800",
    online: "bg-amber-100 text-amber-800",
  };
  return colors[method] || "bg-slate-100 text-slate-700";
}

function statusBadge(status) {
  const colors = {
    paid: "bg-emerald-100 text-emerald-800",
    pending: "bg-amber-100 text-amber-800",
    partial: "bg-orange-100 text-orange-800",
    refunded: "bg-red-100 text-red-800",
  };
  return colors[status] || "bg-slate-100 text-slate-700";
}

export default function PaymentsPage() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterMethod, setFilterMethod] = useState("all");
  const [markingId, setMarkingId] = useState(null);
  const [markMethod, setMarkMethod] = useState("cash");
  const [showMarkModal, setShowMarkModal] = useState(false);

  const fetchPayments = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/manager/payments/`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load payments");
      const data = await res.json();
      setPayments(Array.isArray(data) ? data : data.results || []);
    } catch {
      setError("Unable to load payments. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  async function handleMarkPaid(orderId) {
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/manager/orders/${orderId}/mark-paid/`,
        {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({ payment_method: markMethod }),
        }
      );
      if (!res.ok) throw new Error("Failed to mark as paid");
      setShowMarkModal(false);
      setMarkingId(null);
      fetchPayments();
    } catch {
      setError("Unable to update payment status.");
    }
  }

  const filtered = payments.filter((p) => {
    if (filterStatus !== "all" && p.status !== filterStatus) return false;
    if (filterMethod !== "all" && p.payment_method !== filterMethod)
      return false;
    return true;
  });

  const totalPaid = payments
    .filter((p) => p.status === "paid")
    .reduce((sum, p) => sum + parseFloat(p.amount || 0), 0);

  const totalPending = payments
    .filter((p) => p.status === "pending")
    .reduce((sum, p) => sum + parseFloat(p.amount || 0), 0);

  const totalToday = payments
    .filter((p) => {
      const d = new Date(p.created_at || p.date || "");
      const today = new Date();
      return d.toDateString() === today.toDateString();
    })
    .reduce((sum, p) => sum + parseFloat(p.amount || 0), 0);

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-black text-slate-900">Payments</h1>
        <p className="text-sm text-slate-500 mt-1">
          Track bills, mark orders paid, and view payment history.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Total Today
              </p>
              <p className="mt-1 text-2xl font-black text-slate-900">
                ${totalToday.toFixed(2)}
              </p>
            </div>
            <div className="rounded-xl bg-amber-100 p-2.5 text-amber-700">
              <TrendingUp size={22} />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Total Paid
              </p>
              <p className="mt-1 text-2xl font-black text-emerald-600">
                ${totalPaid.toFixed(2)}
              </p>
            </div>
            <div className="rounded-xl bg-emerald-100 p-2.5 text-emerald-700">
              <CheckCircle2 size={22} />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Pending
              </p>
              <p className="mt-1 text-2xl font-black text-amber-600">
                ${totalPending.toFixed(2)}
              </p>
            </div>
            <div className="rounded-xl bg-amber-100 p-2.5 text-amber-700">
              <Clock size={22} />
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none">
          <option value="all">All Status</option>
          <option value="paid">Paid</option>
          <option value="pending">Pending</option>
          <option value="partial">Partial</option>
          <option value="refunded">Refunded</option>
        </select>

        <select
          value={filterMethod}
          onChange={(e) => setFilterMethod(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none">
          <option value="all">All Methods</option>
          {PAYMENT_METHODS.map((m) => (
            <option
              key={m}
              value={m}>
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Mark paid modal */}
      {showMarkModal && markingId && (
        <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-bold text-slate-900">
              Mark Order #{markingId} as Paid
            </h3>
            <button
              onClick={() => {
                setShowMarkModal(false);
                setMarkingId(null);
              }}
              className="text-slate-400 hover:text-slate-700">
              <X size={20} />
            </button>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Payment Method
              </label>
              <select
                value={markMethod}
                onChange={(e) => setMarkMethod(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none">
                {PAYMENT_METHODS.map((m) => (
                  <option
                    key={m}
                    value={m}>
                    {m.charAt(0).toUpperCase() + m.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={() => handleMarkPaid(markingId)}
              className="rounded-lg bg-amber-400 px-5 py-2 text-sm font-bold text-slate-950 transition hover:bg-amber-300">
              Confirm Payment
            </button>
          </div>
        </div>
      )}

      {/* Payments table */}
      {loading ? (
        <p className="text-center text-slate-500 py-10">Loading payments...</p>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <CircleDollarSign
            size={48}
            className="mx-auto text-slate-300 mb-3"
          />
          <p className="text-slate-500">No payments found.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Method</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((p) => (
                <tr
                  key={p.id}
                  className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold text-slate-900">
                    #{p.order_id || p.order || p.id}
                  </td>
                  <td className="px-4 py-3 font-bold text-slate-900">
                    ${parseFloat(p.amount || 0).toFixed(2)}
                  </td>
                  <td className="px-4 py-3">
                    {p.payment_method && (
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${methodBadge(
                          p.payment_method
                        )}`}>
                        {p.payment_method}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${statusBadge(
                        p.status
                      )}`}>
                      {p.status || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {p.created_at || p.date
                      ? new Date(p.created_at || p.date).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {p.status !== "paid" && p.status !== "refunded" && (
                      <button
                        onClick={() => {
                          setMarkingId(p.order_id || p.order || p.id);
                          setShowMarkModal(true);
                        }}
                        className="rounded-lg bg-amber-400 px-3 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-amber-300">
                        Mark Paid
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
