import React, { useCallback, useEffect, useState } from "react";

import api from "../services/api";

import {
  AlertCircle,
  ArrowUpRight,
  CreditCard,
  DollarSign,
  Download,
  RefreshCw,
  Smartphone,
} from "lucide-react";

const ICON_SIZE = 20;
const METHOD_ICON_SIZE = 18;

const DEFAULT_STATS = {
  total_today: 0,
  total_paid: 0,
  total_paid_today: 0,
  pending: 0,
  unpaid_pending: 0,
  active_table_balances: 0,
  total_count: 0,
  total_amount: 0,
  gross_sales_volume: 0,
  confirmed_in_bank_drawer: 0,
  cash: 0,
  credit_card: 0,
  card: 0,
  mobile: 0,
  mobile_pay: 0,
};

const formatCurrency = (value) => {
  const number = Number(value);

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(number) ? number : 0);
};

const formatDateTime = (value) => {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const getErrorMessage = (error, fallback) => {
  const data = error?.response?.data;

  if (typeof data === "string") {
    return data;
  }

  if (data?.detail) {
    return data.detail;
  }

  if (data?.error) {
    return data.error;
  }

  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([key, value]) => {
        const message = Array.isArray(value) ? value.join(" ") : String(value);

        return `${key}: ${message}`;
      })
      .join(" | ");
  }

  return error?.message || fallback;
};

const getPaymentMethod = (payment) => {
  return payment?.method_name || payment?.method || "Not selected";
};

const normalizeMethodName = (method) => {
  const value = String(method || "Not selected")
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .trim();

  return value.replace(/\b\w/g, (character) => character.toUpperCase());
};

const getPaymentStatus = (payment) => {
  return String(payment?.status || "unknown").toLowerCase();
};

const getReadableStatus = (status) => {
  return String(status || "unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
};

const isPaid = (payment) => {
  return ["paid", "completed", "settled", "success", "successful"].includes(
    getPaymentStatus(payment)
  );
};

const Card = ({ title, value, icon, color, subtitle }) => {
  const colors = {
    blue: "bg-blue-50 text-blue-600 border-blue-100",
    emerald: "bg-emerald-50 text-emerald-600 border-emerald-100",
    amber: "bg-amber-50 text-amber-600 border-amber-100",
  };

  return (
    <div className="relative overflow-hidden bg-white p-6 rounded-3xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow group">
      <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:scale-110 transition-transform">
        {icon}
      </div>

      <div className="relative z-10 flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <div className={`p-2 rounded-xl border ${colors[color]}`}>{icon}</div>

          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
            {title}
          </p>
        </div>

        <p className="text-3xl font-black text-slate-900 mt-2">
          {formatCurrency(value)}
        </p>

        <p className="text-[10px] font-bold text-slate-400 italic">
          {subtitle}
        </p>
      </div>
    </div>
  );
};

const StatCard = (props) => {
  return <Card {...props} />;
};

const Stats = ({ stats }) => {
  const pendingAmount = Number(
    stats.unpaid_pending ?? stats.active_table_balances ?? stats.pending ?? 0
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <StatCard
        title="Revenue Today"
        value={stats.total_today}
        icon={<ArrowUpRight size={ICON_SIZE} />}
        color="blue"
        subtitle="Gross sales volume today"
      />

      <StatCard
        title="Settled Payments"
        value={stats.total_paid_today ?? stats.total_paid ?? 0}
        icon={<DollarSign size={ICON_SIZE} />}
        color="emerald"
        subtitle="Confirmed paid orders today"
      />

      <StatCard
        title="Unpaid / Pending"
        value={pendingAmount}
        icon={<ArrowUpRight size={ICON_SIZE} />}
        color="amber"
        subtitle="Active unpaid balances"
      />
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
        {formatCurrency(amount)}
      </span>
    </div>
  );
};

const PaymentMethods = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <MethodCard
        label="Cash"
        amount={stats.cash ?? 0}
        icon={<DollarSign size={METHOD_ICON_SIZE} />}
        accent="orange"
      />

      <MethodCard
        label="Card"
        amount={stats.credit_card ?? stats.card ?? 0}
        icon={<CreditCard size={METHOD_ICON_SIZE} />}
        accent="indigo"
      />

      <MethodCard
        label="Mobile Pay"
        amount={stats.mobile ?? stats.mobile_pay ?? 0}
        icon={<Smartphone size={METHOD_ICON_SIZE} />}
        accent="cyan"
      />
    </div>
  );
};

const TransactionRow = ({ payment }) => {
  const paymentId = String(payment?.id ?? "");

  const orderReference =
    payment?.order_number ||
    payment?.order_ref ||
    `ORD-${paymentId.slice(0, 6).toUpperCase()}`;

  const method = getPaymentMethod(payment);

  const status = getPaymentStatus(payment);

  const paid = isPaid(payment);

  return (
    <tr className="hover:bg-slate-50/80 transition-colors group">
      <td className="px-6 py-4">
        <span className="font-mono text-xs font-bold text-slate-500 group-hover:text-blue-600 transition-colors">
          #{orderReference}
        </span>
      </td>

      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              paid ? "bg-emerald-500" : "bg-amber-400"
            }`}
          />

          <span className="text-sm font-bold text-slate-700">
            {normalizeMethodName(method)}
          </span>
        </div>
      </td>

      <td className="px-6 py-4 text-right font-black text-slate-900">
        {formatCurrency(payment?.amount ?? payment?.total)}
      </td>

      <td className="px-6 py-4">
        <span
          className={`px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-tighter shadow-sm border ${
            paid
              ? "bg-emerald-50 text-emerald-600 border-emerald-100"
              : "bg-amber-50 text-amber-600 border-amber-100"
          }`}>
          {getReadableStatus(status)}
        </span>
      </td>

      <td className="px-6 py-4 text-slate-400 text-xs font-medium">
        {formatDateTime(payment?.created_at || payment?.date)}
      </td>
    </tr>
  );
};

const downloadCsv = (payments) => {
  if (!payments.length) {
    return;
  }

  const headers = ["Order Ref", "Method", "Amount", "Status", "Timestamp"];

  const rows = payments.map((payment) => {
    const paymentId = String(payment?.id ?? "");

    const orderReference =
      payment?.order_number ||
      payment?.order_ref ||
      `ORD-${paymentId.slice(0, 6).toUpperCase()}`;

    const amount = Number(payment?.amount ?? payment?.total ?? 0);

    return [
      orderReference,
      normalizeMethodName(getPaymentMethod(payment)),
      Number.isFinite(amount) ? amount.toFixed(2) : "0.00",
      getReadableStatus(getPaymentStatus(payment)),
      formatDateTime(payment?.created_at || payment?.date),
    ];
  });

  const csvContent = [headers, ...rows]
    .map((row) =>
      row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")
    )
    .join("\n");

  const blob = new Blob([csvContent], {
    type: "text/csv;charset=utf-8;",
  });

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");

  link.href = url;
  link.download = `payments-${new Date().toISOString().slice(0, 10)}.csv`;

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
};

const TransactionTable = ({ payments = [] }) => {
  return (
    <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
      <div className="p-6 border-b border-slate-100 flex justify-between items-center">
        <h3 className="font-bold text-slate-800">Recent Orders</h3>

        <button
          type="button"
          onClick={() => {
            downloadCsv(payments);
          }}
          disabled={!payments.length}
          className="inline-flex items-center gap-2 text-xs font-bold text-blue-600 hover:text-blue-700 disabled:text-slate-300 disabled:cursor-not-allowed uppercase tracking-widest">
          <Download size={14} />
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
            {payments.length > 0 ? (
              payments.map((payment) => (
                <TransactionRow
                  key={String(payment?.id)}
                  payment={payment}
                />
              ))
            ) : (
              <tr>
                <td
                  colSpan={5}
                  className="p-20 text-center">
                  <div className="flex flex-col items-center opacity-20">
                    <DollarSign size={48} />

                    <p className="mt-2 font-bold italic">
                      No orders recorded for this period
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const Header = ({ title, subtitle, lastUpdated }) => {
  return (
    <div className="flex justify-between items-end">
      <div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">
          {title}
        </h1>

        <p className="text-slate-500 font-medium">{subtitle}</p>
      </div>

      <div className="text-right hidden md:block">
        <p className="text-xs font-bold text-slate-400 uppercase">
          Last Updated
        </p>

        <p className="text-sm font-bold text-slate-700">
          {lastUpdated ? formatDateTime(lastUpdated) : "—"}
        </p>
      </div>
    </div>
  );
};

export default function PaymentsPage() {
  const [data, setData] = useState({
    stats: DEFAULT_STATS,
    payments: [],
  });

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchPayments = useCallback(async (signal) => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get("/payments/summary/", {
        signal,
        params: {
          _: Date.now(),
        },
      });

      const payload = response.data || {};

      setData({
        stats: {
          ...DEFAULT_STATS,
          ...(payload.stats || {}),
        },
        payments: Array.isArray(payload.payments) ? payload.payments : [],
      });

      setLastUpdated(new Date());
    } catch (requestError) {
      if (
        requestError?.code === "ERR_CANCELED" ||
        requestError?.name === "CanceledError"
      ) {
        return;
      }

      console.error("Fetch payment summary failed:", requestError);

      setError(getErrorMessage(requestError, "Failed to load payments."));
    } finally {
      if (!signal || !signal.aborted) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchPayments(controller.signal);

    const interval = setInterval(() => {
      fetchPayments();
    }, 30000);

    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, [fetchPayments]);

  if (loading && !lastUpdated) {
    return (
      <div className="p-10 text-center font-medium animate-pulse">
        Loading Financial Data...
      </div>
    );
  }

  if (error && !lastUpdated) {
    return (
      <div className="p-10 flex flex-col items-center text-red-500 bg-red-50 rounded-3xl m-8 border border-red-100">
        <AlertCircle
          size={48}
          className="mb-4"
        />

        <h2 className="text-xl font-bold">Connection Error</h2>

        <p className="text-red-400 mt-2 text-center">{error}</p>

        <button
          type="button"
          onClick={() => {
            fetchPayments();
          }}
          className="mt-5 px-4 py-2 bg-red-600 text-white rounded-xl font-bold">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50/50 min-h-screen">
      <Header
        title="Financial Overview"
        subtitle="Real-time payment tracking and reconciliation"
        lastUpdated={lastUpdated}
      />

      {error && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-100 text-amber-700 rounded-2xl p-4">
          <AlertCircle size={20} />

          <p className="text-sm font-semibold">Refresh failed: {error}</p>
        </div>
      )}

      <Stats stats={data.stats} />

      <PaymentMethods stats={data.stats} />

      <TransactionTable payments={data.payments} />
    </div>
  );
}
