import React, { useState, useEffect } from "react";
import api from "../services/api";
import {
  DollarSign,
  CreditCard,
  Clock,
  AlertCircle,
  Smartphone,
  Wallet,
  ArrowUpRight,
} from "lucide-react";

export default function PaymentsPage() {
  const [data, setData] = useState({
    stats: {
      total_today: 0,
      total_paid: 0,
      pending: 0,
      cash_total: 0,
      card_total: 0,
      mobile_total: 0,
    },
    payments: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPayments = async () => {
      try {
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
    return (
      <div className="p-10 text-center font-medium animate-pulse">
        Loading Financial Data...
      </div>
    );

  if (error)
    return (
      <div className="p-10 flex flex-col items-center text-red-500 bg-red-50 rounded-3xl m-8 border border-red-100">
        <AlertCircle className="w-12 h-12 mb-4" />
        <h2 className="text-xl font-bold">Connection Error</h2>
        <p className="text-red-400">{error}</p>
      </div>
    );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50/50 min-h-screen">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">
            Financial Overview
          </h1>
          <p className="text-slate-500 font-medium">
            Real-time payment tracking and reconciliation
          </p>
        </div>
        <div className="text-right hidden md:block">
          <p className="text-xs font-bold text-slate-400 uppercase">
            Last Updated
          </p>
          <p className="text-sm font-bold text-slate-700">
            {new Date().toLocaleTimeString()}
          </p>
        </div>
      </div>

      {/* Top Level Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Revenue Today"
          value={data.stats.total_today}
          icon={<ArrowUpRight size={20} />}
          color="blue"
          subtitle="Gross sales volume"
        />
        <StatCard
          title="Settled Payments"
          value={data.stats.total_paid}
          icon={<DollarSign size={20} />}
          color="emerald"
          subtitle="Confirmed in bank/drawer"
        />
        <StatCard
          title="Unpaid / Pending"
          value={data.stats.pending}
          icon={<Clock size={20} />}
          color="amber"
          subtitle="Active table balances"
        />
      </div>

      {/* Payment Method Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MethodCard
          label="Cash"
          amount={data.stats.cash_total || 0}
          icon={<Wallet size={18} />}
          accent="orange"
        />
        <MethodCard
          label="Credit Card"
          amount={data.stats.card_total || 0}
          icon={<CreditCard size={18} />}
          accent="indigo"
        />
        <MethodCard
          label="Mobile / Digital"
          amount={data.stats.mobile_total || 0}
          icon={<Smartphone size={18} />}
          accent="cyan"
        />
      </div>

      {/* Detailed Transaction Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex justify-between items-center">
          <h3 className="font-bold text-slate-800">Recent Transactions</h3>
          <button className="text-xs font-bold text-blue-600 hover:text-blue-700 uppercase tracking-widest">
            Export CSV
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-slate-400 text-[11px] uppercase tracking-widest font-black bg-slate-50/50">
                <th className="px-6 py-4">Order Ref</th>
                <th className="px-6 py-4">Method</th>
                <th className="px-6 py-4 text-right">Amount</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.payments.length > 0 ? (
                data.payments.map((p) => (
                  <tr
                    key={p.id}
                    className="hover:bg-slate-50/80 transition-colors group">
                    <td className="px-6 py-4">
                      <span className="font-mono text-xs font-bold text-slate-500 group-hover:text-blue-600 transition-colors">
                        #{p.order_number || p.id.slice(0, 8)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-slate-300" />
                        <span className="text-sm font-bold text-slate-700 capitalize">
                          {p.method_name || p.method || "Unknown"}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right font-black text-slate-900">
                      ${Number(p.amount).toFixed(2)}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-tighter shadow-sm border ${
                          p.status?.toLowerCase() === "paid"
                            ? "bg-emerald-50 text-emerald-600 border-emerald-100"
                            : "bg-amber-50 text-amber-600 border-amber-100"
                        }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400 text-xs font-medium">
                      {p.date || new Date(p.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan="5"
                    className="p-20 text-center">
                    <div className="flex flex-col items-center opacity-20">
                      <DollarSign size={48} />
                      <p className="mt-2 font-bold italic">
                        No transactions recorded for this period
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const StatCard = ({ title, value, icon, color, subtitle }) => {
  const colors = {
    blue: "bg-blue-50 text-blue-600 border-blue-100",
    emerald: "bg-emerald-50 text-emerald-600 border-emerald-100",
    amber: "bg-amber-50 text-amber-600 border-amber-100",
  };

  return (
    <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
      <div
        className={`absolute top-0 right-0 p-8 opacity-5 group-hover:scale-110 transition-transform`}>
        {icon}
      </div>
      <div className="flex flex-col gap-1 relative z-10">
        <div className="flex items-center gap-2">
          <div className={`p-2 rounded-xl border ${colors[color]}`}>{icon}</div>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
            {title}
          </p>
        </div>
        <p className="text-3xl font-black text-slate-900 mt-2">
          ${Number(value || 0).toFixed(2)}
        </p>
        <p className="text-[10px] font-bold text-slate-400 italic">
          {subtitle}
        </p>
      </div>
    </div>
  );
};

const MethodCard = ({ label, amount, icon, accent }) => {
  const accents = {
    orange: "text-orange-600 bg-orange-50",
    indigo: "text-indigo-600 bg-indigo-50",
    cyan: "text-cyan-600 bg-cyan-50",
  };
  return (
    <div className="bg-white px-5 py-4 rounded-2xl border border-slate-200 flex items-center justify-between shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${accents[accent]}`}>{icon}</div>
        <span className="text-sm font-bold text-slate-600">{label}</span>
      </div>
      <span className="font-black text-slate-900">
        ${Number(amount).toFixed(2)}
      </span>
    </div>
  );
};
