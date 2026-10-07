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
import api from "../services/api"; // adjust path if needed

const API_SUBSCRIPTION_URL = "/subscription/"; // matches core/urls.py

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

function SubscriptionPage() {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [paymentMethod, setPaymentMethod] = useState("");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function fetchSubscription() {
      try {
        setError("");
        const res = await api.get(API_SUBSCRIPTION_URL);
        if (!cancelled) {
          setSubscription(res.data);
        }
      } catch (err) {
        console.error("Failed to fetch subscription:", err);
        if (!cancelled) {
          setError(
            err?.response?.data?.message || "Failed to load subscription data."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchSubscription();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError("");
    setSubmitSuccess("");

    try {
      await api.post(API_SUBSCRIPTION_URL, {
        offline_payment_method: paymentMethod,
        offline_payment_reference: reference,
        offline_payment_notes: notes,
      });

      setSubmitSuccess(
        "Payment reference submitted! Your account will be updated once verified."
      );
      setPaymentMethod("");
      setReference("");
      setNotes("");
    } catch (err) {
      console.error("Subscription renewal error:", err);
      setSubmitError(
        err?.response?.data?.message ||
          "Failed to submit renewal request. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <p className="text-slate-500">Loading subscription…</p>
      </div>
    );
  }

  if (error || !subscription) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-4">
          {error || "No subscription data available."}
        </div>
      </div>
    );
  }

  const {
    plan_name = "No Plan",
    status = "unknown",
    days_remaining = 0,
    current_period_end,
  } = subscription;

  const expiryDate = current_period_end
    ? new Date(current_period_end).toLocaleDateString()
    : "—";

  const isExpiringSoon = days_remaining <= 7 && days_remaining > 0;
  const isExpired = days_remaining <= 0 || status === "expired";

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
            isExpired
              ? "bg-red-100 text-red-700"
              : isExpiringSoon
              ? "bg-amber-100 text-amber-700"
              : "bg-green-100 text-green-700"
          }`}>
          {isExpired ? (
            <AlertTriangle size={16} />
          ) : isExpiringSoon ? (
            <AlertTriangle size={16} />
          ) : (
            <ShieldCheck size={16} />
          )}
          {isExpired ? "Expired" : `${days_remaining} Days Remaining`}
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
              {plan_name}
            </div>
            <div className="mt-1 text-slate-500 text-sm">
              Expires on {expiryDate}
            </div>

            <div className="mt-6 pt-6 border-t border-slate-100">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-500">Status</span>
                <span className="font-bold capitalize text-slate-900">
                  {status}
                </span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    isExpired
                      ? "bg-red-500"
                      : isExpiringSoon
                      ? "bg-amber-500"
                      : "bg-green-500"
                  }`}
                  style={{
                    width: `${Math.min(100, (days_remaining / 30) * 100)}%`,
                  }}
                />
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
            {submitSuccess && (
              <div className="bg-green-50 border border-green-200 text-green-700 rounded-xl p-4 text-sm">
                {submitSuccess}
              </div>
            )}

            {submitError && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
                {submitError}
              </div>
            )}

            <div>
              <label className="text-sm font-semibold text-slate-700 block mb-3">
                Select Payment Method
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {offlineMethods.map((method) => (
                  <button
                    key={method.id}
                    type="button"
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

              <div>
                <label className="text-xs font-bold text-slate-500 uppercase block mb-1">
                  Notes (optional)
                </label>
                <textarea
                  placeholder="Any additional info for verification"
                  className="w-full bg-white border border-slate-300 rounded-lg p-3 outline-none focus:ring-2 focus:ring-amber-500 transition-all"
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>

              <div className="text-xs text-slate-500 italic">
                * Please ensure the reference matches your payment receipt
                exactly.
              </div>
            </div>

            <button
              type="button"
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
}

export default SubscriptionPage;
