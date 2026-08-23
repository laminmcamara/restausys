import { useState } from "react";

const INVOICES = [
  {
    id: "INV-2025-001",
    date: "2025-08-01",
    amount: "$49.00",
    status: "Paid",
  },
  {
    id: "INV-2025-002",
    date: "2025-09-01",
    amount: "$49.00",
    status: "Paid",
  },
  {
    id: "INV-2025-003",
    date: "2025-10-01",
    amount: "$49.00",
    status: "Pending",
  },
];

export default function BillingPage() {
  const [plan] = useState({ name: "Professional", price: "$49/month" });
  const [paymentMethod] = useState("Visa •••• 4242");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Billing</h1>

      {/* Plan & Payment */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            Current Plan
          </h2>
          <div className="text-2xl font-bold text-slate-900">{plan.name}</div>
          <div className="text-slate-600">{plan.price}</div>
          <button
            type="button"
            className="mt-4 bg-slate-800 hover:bg-slate-900 text-white font-semibold px-4 py-2 rounded-lg text-sm transition">
            Change Plan
          </button>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            Payment Method
          </h2>
          <div className="text-slate-800 font-medium">{paymentMethod}</div>
          <button
            type="button"
            className="mt-4 bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-semibold px-4 py-2 rounded-lg text-sm transition">
            Update Card
          </button>
        </div>
      </div>

      {/* Invoices */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800">Invoices</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">Invoice</th>
                <th className="text-left px-4 py-3 font-semibold">Date</th>
                <th className="text-left px-4 py-3 font-semibold">Amount</th>
                <th className="text-left px-4 py-3 font-semibold">Status</th>
                <th className="text-right px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {INVOICES.map((inv) => (
                <tr
                  key={inv.id}
                  className="border-t border-slate-100">
                  <td className="px-4 py-3 text-slate-800">{inv.id}</td>
                  <td className="px-4 py-3 text-slate-600">{inv.date}</td>
                  <td className="px-4 py-3 text-slate-800 font-medium">
                    {inv.amount}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        inv.status === "Paid"
                          ? "bg-green-100 text-green-700"
                          : "bg-amber-100 text-amber-700"
                      }`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <a
                      href="#"
                      className="text-amber-700 hover:text-amber-800 font-medium">
                      Download
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
