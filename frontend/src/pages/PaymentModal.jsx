import React, { useEffect, useMemo, useState } from "react";

import {
  AlertCircle,
  Banknote,
  CreditCard,
  Loader2,
  Smartphone,
  X,
} from "lucide-react";

const normalizeMethod = (method) => {
  const value = String(method || "")
    .trim()
    .toLowerCase()
    .replaceAll("_", " ")
    .replaceAll("-", " ");

  if (value.includes("cash")) {
    return "cash";
  }

  if (
    value.includes("card") ||
    value.includes("credit") ||
    value.includes("debit") ||
    value.includes("visa") ||
    value.includes("master")
  ) {
    return "card";
  }

  if (
    value.includes("mobile") ||
    value.includes("momo") ||
    value.includes("mtn") ||
    value.includes("airtel") ||
    value.includes("orange")
  ) {
    return "mobile";
  }

  return value;
};

const getMethodLabel = (method) => {
  const normalized = normalizeMethod(method?.slug || method?.name || method);

  if (normalized === "cash") {
    return "Cash";
  }

  if (normalized === "card") {
    return "Card";
  }

  if (normalized === "mobile") {
    return "Mobile Pay";
  }

  return method?.display_name || method?.name || "Payment Method";
};

const getMethodIcon = (method) => {
  const normalized = normalizeMethod(method?.slug || method?.name || method);

  if (normalized === "cash") {
    return Banknote;
  }

  if (normalized === "card") {
    return CreditCard;
  }

  if (normalized === "mobile") {
    return Smartphone;
  }

  return CreditCard;
};

const getOrderTotal = (order) => {
  const value = order?.total ?? order?.total_price ?? order?.total_amount ?? 0;

  const number = Number(value);

  return Number.isFinite(number) ? number : 0;
};

const getErrorMessage = (error) => {
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

  return error?.message || "Payment failed.";
};

const PaymentModal = ({
  isOpen,
  order,
  methods = [],
  onClose,
  onPaymentComplete,
}) => {
  const [isProcessing, setIsProcessing] = useState(false);

  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState("");

  const [error, setError] = useState("");

  const orderTotal = getOrderTotal(order);

  const activeMethods = useMemo(() => {
    if (!Array.isArray(methods)) {
      return [];
    }

    return methods.filter(
      (method) => method?.is_active !== false && method?.active !== false
    );
  }, [methods]);

  useEffect(() => {
    if (!isOpen) {
      setIsProcessing(false);
      setSelectedPaymentMethod("");
      setError("");
      return;
    }

    setError("");
    setSelectedPaymentMethod("");
  }, [isOpen, order?.id]);

  if (!isOpen || !order) {
    return null;
  }

  const handlePayment = async () => {
    setError("");

    if (!order.id) {
      setError("Order ID is missing.");
      return;
    }

    if (orderTotal <= 0) {
      setError("This order has a zero total and cannot be paid.");
      return;
    }

    if (!selectedPaymentMethod) {
      setError("Please select a payment method.");
      return;
    }

    const selectedMethod = activeMethods.find(
      (method) => String(method.id) === String(selectedPaymentMethod)
    );

    if (!selectedMethod) {
      setError("The selected payment method is unavailable.");
      return;
    }

    setIsProcessing(true);

    try {
      /*
       * The parent POS component calls:
       *
       * POST /orders/<uuid>/mark_paid/
       *
       * The method ID is passed first. The method
       * object is also passed for compatibility.
       */
      await onPaymentComplete(order.id, selectedMethod.id, selectedMethod);
    } catch (paymentError) {
      console.error("Payment modal error:", paymentError);

      setError(getErrorMessage(paymentError));
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-[32px] w-full max-w-md overflow-hidden shadow-2xl">
        <div className="relative p-6 border-b bg-slate-50 flex justify-between items-center">
          <h2 className="text-xl font-black text-slate-900 uppercase tracking-tight text-center w-full">
            Finalize Bill
          </h2>

          <button
            type="button"
            onClick={onClose}
            disabled={isProcessing}
            className="absolute right-6 p-2 hover:bg-slate-200 rounded-full transition-colors disabled:opacity-50">
            <X size={20} />
          </button>
        </div>

        <div className="p-8">
          <div className="text-center mb-8">
            <p className="text-slate-500 font-bold uppercase text-xs tracking-widest mb-1">
              Total Amount
            </p>

            <h3 className="text-5xl font-black text-slate-900">
              ${orderTotal.toFixed(2)}
            </h3>
          </div>

          {activeMethods.length === 0 ? (
            <div className="rounded-2xl bg-amber-50 border border-amber-100 p-5 text-amber-700">
              <div className="flex items-center gap-2 font-black">
                <AlertCircle size={20} />
                No payment methods available
              </div>

              <p className="mt-2 text-sm font-medium">
                Create or activate a payment method for this restaurant before
                accepting payment.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3">
                {activeMethods.map((method) => {
                  const Icon = getMethodIcon(method);

                  const selected =
                    String(selectedPaymentMethod) === String(method.id);

                  return (
                    <button
                      type="button"
                      key={String(method.id)}
                      onClick={() => {
                        setSelectedPaymentMethod(String(method.id));
                        setError("");
                      }}
                      disabled={isProcessing}
                      className={`flex items-center gap-4 p-4 rounded-2xl border-2 text-left transition-all ${
                        selected
                          ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                          : "border-slate-200 bg-white text-slate-700 hover:border-indigo-300"
                      } disabled:opacity-50`}>
                      <span
                        className={`p-3 rounded-xl ${
                          selected
                            ? "bg-indigo-600 text-white"
                            : "bg-slate-100 text-slate-500"
                        }`}>
                        <Icon size={22} />
                      </span>

                      <span className="flex-1">
                        <span className="block font-black">
                          {getMethodLabel(method)}
                        </span>

                        {method.requires_reference && (
                          <span className="block mt-1 text-xs font-medium text-slate-400">
                            Reference may be required
                          </span>
                        )}
                      </span>

                      <span
                        className={`w-5 h-5 rounded-full border-2 ${
                          selected
                            ? "border-indigo-600 bg-indigo-600"
                            : "border-slate-300"
                        }`}
                      />
                    </button>
                  );
                })}
              </div>

              <button
                type="button"
                disabled={isProcessing || !selectedPaymentMethod}
                onClick={handlePayment}
                className="w-full flex items-center justify-center gap-2 px-6 py-4 rounded-2xl font-black text-sm text-white shadow-lg transition-all active:scale-95 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed">
                {isProcessing ? (
                  <>
                    <Loader2
                      className="animate-spin"
                      size={20}
                    />
                    Processing...
                  </>
                ) : (
                  <>Pay ${orderTotal.toFixed(2)}</>
                )}
              </button>
            </div>
          )}

          {error && (
            <div className="mt-6 flex items-start gap-2 text-red-600 bg-red-50 border border-red-100 rounded-xl p-4 font-bold text-sm">
              <AlertCircle
                size={20}
                className="shrink-0"
              />

              <span>{error}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PaymentModal;
