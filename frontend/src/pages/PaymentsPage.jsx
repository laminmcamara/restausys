import React, { useState, useEffect } from "react";
import api from "../services/api"; // Import your axios instance
import { DollarSign, CreditCard, Clock, AlertCircle } from "lucide-react";

export default function PaymentsPage() {
  const [data, setData] = useState({
    stats: { total_today: 0, total_paid: 0, pending: 0 },
    payments: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPayments = async () => {
      try {
        // Correct URL: /api/v1/payments/summary/
        // Since baseURL is /api/v1, we use /payments/summary/
        const res = await api.get("/payments/summary/");
        setData(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load payments");
      } finally {
        setLoading(false);
      }
    };

    fetchPayments();
  }, []);

  if (loading)
    return <div className="p-10 text-center">Loading Payments...</div>;
  if (error)
    return (
      <div className="p-10 flex flex-col items-center text-red-500">
        <AlertCircle className="w-10 h-10 mb-2" />
        <p>Unable to load payments: {error}</p>
      </div>
    );

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">Payments</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Total Today"
          value={data.stats.total_today}
          icon={<DollarSign />}
          color="blue"
        />
        <StatCard
          title="Total Paid"
          value={data.stats.total_paid}
          icon={<CreditCard />}
          color="green"
        />
        <StatCard
          title="Pending"
          value={data.stats.pending}
          icon={<Clock />}
          color="amber"
        />
      </div>

      <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b text-slate-500 text-sm">
            <tr>
              <th className="p-4">Order ID</th>
              <th className="p-4">Amount</th>
              <th className="p-4">Status</th>
              <th className="p-4">Date</th>
            </tr>
          </thead>
          <tbody>
            {data.payments.length > 0 ? (
              data.payments.map((p) => (
                <tr
                  key={p.id}
                  className="border-b last:border-0 hover:bg-slate-50 transition">
                  <td className="p-4 font-medium text-slate-700">
                    {p.order_number}
                  </td>
                  <td className="p-4 font-semibold text-slate-900">
                    ${p.amount.toFixed(2)}
                  </td>
                  <td className="p-4">
                    <span
                      className={`px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                        p.status === "paid"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-700"
                      }`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="p-4 text-slate-500 text-sm">{p.date}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan="4"
                  className="p-10 text-center text-slate-400 italic">
                  No payment history found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const StatCard = ({ title, value, icon, color }) => (
  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
    <div className={`p-3 rounded-lg bg-${color}-50 text-${color}-600`}>
      {icon}
    </div>
    <div>
      <p className="text-xs font-bold text-slate-400 uppercase tracking-tight">
        {title}
      </p>
      <p className="text-2xl font-black text-slate-900">${value?.toFixed(2)}</p>
    </div>
  </div>
);
