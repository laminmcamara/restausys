import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  Landmark,
  Smartphone,
  Banknote,
  History,
  Info,
} from "lucide-react";

const SubscriptionPage = () => {
  const [subData, setSubData] = useState({
    plan_name: "Professional",
    status: "active",
    days_remaining: 12,
    expiry_date: "2026-09-10",
  });

  const [paymentMethod, setPaymentMethod] = useState("");
  const [reference, setReference] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const offlineMethods = [
    {
      id: "mobile_money",
      label: "Mobile Money",
      icon: <Smartphone size={18} />,
    },
    {
      id: "bank_transfer",
      label: "Bank Transfer",
      icon: <Landmark size={18} />,
    },
    { id: "cash", label: "Cash / Physical", icon: <Banknote size={18} /> },
    { id: "cheque", label: "Cheque", icon: <History size={18} /> },
  ];

  const handleSubmit = () => {
    setIsSubmitting(true);
    // API Call: axios.post('/api/v1/manager/subscription/', { offline_payment_method: paymentMethod, offline_payment_reference: reference })
    setTimeout(() => {
      alert(
        "Payment reference submitted! Your account will be updated once verified."
      );
      setIsSubmitting(false);
    }, 1500);
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Subscription</h1>
          <p className="text-slate-500">
            Manage your restaurant's access and plan.
          </p>
        </div>
        <div
          className={`px-4 py-2 rounded-full text-sm font-bold flex items-center gap-2 ${
            subData.days_remaining > 5
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}>
          {subData.days_remaining > 5 ? (
            <ShieldCheck size={16} />
          ) : (
            <AlertTriangle size={16} />
          )}
          {subData.days_remaining} Days Remaining
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Current Status Card */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
              Current Plan
            </h3>
            <div className="mt-2 text-3xl font-bold text-slate-900">
              {subData.plan_name}
            </div>
            <div className="mt-1 text-slate-500 text-sm">
              Expires on {new Date(subData.expiry_date).toLocaleDateString()}
            </div>

            <div className="mt-6 pt-6 border-t border-slate-100">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-500">Status</span>
                <span className="font-bold capitalize text-slate-900">
                  {subData.status}
                </span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    subData.days_remaining > 7 ? "bg-amber-500" : "bg-red-500"
                  }`}
                  style={{
                    width: `${(subData.days_remaining / 30) * 100}%`,
                  }}></div>
              </div>
            </div>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
            <div className="flex gap-3">
              <Info className="text-amber-600 shrink-0" />
              <p className="text-sm text-amber-800">
                Payments are processed manually. Please allow up to 24 hours for
                activation after submitting your reference.
              </p>
            </div>
          </div>
        </div>

        {/* Renewal Form */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100">
            <h3 className="text-lg font-bold text-slate-900">
              Renew Subscription
            </h3>
            <p className="text-sm text-slate-500">
              Submit payment details for manual verification.
            </p>
          </div>

          <div className="p-6 space-y-6">
            <div>
              <label className="text-sm font-semibold text-slate-700 block mb-3">
                Select Payment Method
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {offlineMethods.map((method) => (
                  <button
                    key={method.id}
                    onClick={() => setPaymentMethod(method.id)}
                    className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all gap-2 ${
                      paymentMethod === method.id
                        ? "border-amber-600 bg-amber-50 text-amber-700"
                        : "border-slate-100 hover:border-slate-200 text-slate-500"
                    }`}>
                    {method.icon}
                    <span className="text-xs font-bold">{method.label}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-4 bg-slate-50 p-6 rounded-xl border border-slate-200">
              <div>
                <label className="text-xs font-bold text-slate-500 uppercase block mb-1">
                  Transaction Reference
                </label>
                <input
                  type="text"
                  placeholder="e.g. TXN987654321 or Receipt #"
                  className="w-full bg-white border border-slate-300 rounded-lg p-3 outline-none focus:ring-2 focus:ring-amber-500 transition-all font-mono"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                />
              </div>

              <div className="text-xs text-slate-500 italic">
                * Please ensure the reference matches your payment receipt
                exactly.
              </div>
            </div>

            <button
              disabled={!paymentMethod || !reference || isSubmitting}
              onClick={handleSubmit}
              className="w-full bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2">
              {isSubmitting ? "Submitting..." : "Submit Renewal Request"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionPage;
