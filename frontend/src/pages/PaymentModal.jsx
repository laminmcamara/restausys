// PaymentModal.jsx
import React from "react";
import {
  X,
  CreditCard,
  Banknote,
  Smartphone,
  Loader2,
  AlertCircle,
} from "lucide-react";

const PaymentModal = ({
  isOpen,
  order,
  methods,
  onClose,
  onPaymentComplete,
}) => {
  if (!isOpen || !order) return null;

  const [isProcessing, setIsProcessing] = React.useState(false);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = React.useState("");
  const [error, setError] = React.useState(null);

  // Helper to find the right method ID by name/slug
  const getMethodId = (search) => {
    if (!methods || !Array.isArray(methods)) return null;

    const found = methods.find((m) =>
      m.name.toLowerCase().includes(search.toLowerCase())
    );
    return found ? found.id : null;
  };

  const handlePayment = async () => {
    if (!selectedPaymentMethod) {
      setError("Please select a payment method");
      return;
    }

    const methodId = getMethodId(selectedPaymentMethod);
    if (!methodId) {
      setError(
        `Payment method "${selectedPaymentMethod}" not configured in backend.`
      );
      return;
    }

    // Check which ID property exists
    const orderId = order.id || order.uuid;

    if (!orderId) {
      console.error("Order object missing ID:", order);
      setError("Error: Order ID is missing. Check console.");
      return;
    }

    setIsProcessing(true);
    try {
      await onPaymentComplete(orderId, methodId, selectedPaymentMethod);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-[32px] w-full max-w-md overflow-hidden shadow-2xl">
        <div className="p-6 border-b flex justify-between items-center bg-slate-50">
          <h2 className="text-xl font-black text-slate-900 uppercase tracking-tight text-center w-full">
            Finalize Bill
          </h2>
          <button
            onClick={onClose}
            className="absolute right-6 p-2 hover:bg-slate-200 rounded-full transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-8">
          <div className="text-center mb-8">
            <p className="text-slate-500 font-bold uppercase text-xs tracking-widest mb-1">
              Total Amount
            </p>
            <h3 className="text-5xl font-black text-slate-900">
              ${parseFloat(order.total_price || 0).toFixed(2)}
            </h3>
          </div>

          <div className="flex flex-col gap-4">
            <select
              value={selectedPaymentMethod}
              onChange={(e) => setSelectedPaymentMethod(e.target.value)}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-black text-slate-600 transition-colors">
              <option value="">Select Payment Method</option>
              {methods.map((method) => (
                <option
                  key={method.id}
                  value={method.name}>
                  {method.name}
                </option>
              ))}
            </select>

            <button
              disabled={isProcessing}
              onClick={handlePayment}
              className="flex items-center gap-2 px-6 py-3 rounded-xl font-black text-sm text-white shadow-lg transition-all active:scale-95 bg-emerald-500 hover:brightness-110">
              Pay Now
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>

          {isProcessing && (
            <div className="mt-6 flex items-center justify-center gap-2 text-indigo-600 font-bold">
              <Loader2
                className="animate-spin"
                size={20}
              />
              <span>Syncing with server...</span>
            </div>
          )}

          {error && (
            <div className="mt-6 flex items-center justify-center gap-2 text-red-600 font-bold">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PaymentModal;
