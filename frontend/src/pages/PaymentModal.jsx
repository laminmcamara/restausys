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

  // Helper to find the right method ID by name/slug
  const getMethodId = (search) => {
    if (!methods || !Array.isArray(methods)) return null;

    const found = methods.find((m) =>
      m.name.toLowerCase().includes(search.toLowerCase())
    );
    return found ? found.id : null;
  };
  
  const handlePayment = async (searchName) => {
    const methodId = getMethodId(searchName);
    if (!methodId) {
      alert(`Payment method "${searchName}" not configured in backend.`);
      return;
    }
    setIsProcessing(true);
    try {
      await onPaymentComplete(order.id, methodId);
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

          <div className="grid grid-cols-1 gap-3">
            {/* CASH */}
            <button
              disabled={isProcessing}
              onClick={() => handlePayment("cash")}
              className="flex items-center gap-4 p-4 rounded-2xl border-2 border-slate-100 hover:border-green-500 hover:bg-green-50 transition-all group">
              <div className="w-12 h-12 bg-green-100 text-green-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <Banknote size={24} />
              </div>
              <div className="text-left">
                <div className="font-black text-slate-900 uppercase text-sm">
                  Cash
                </div>
                <div className="text-xs text-slate-500 font-medium">
                  Pay with physical currency
                </div>
              </div>
            </button>

            {/* CARD */}
            <button
              disabled={isProcessing}
              onClick={() => handlePayment("card")}
              className="flex items-center gap-4 p-4 rounded-2xl border-2 border-slate-100 hover:border-indigo-500 hover:bg-indigo-50 transition-all group">
              <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <CreditCard size={24} />
              </div>
              <div className="text-left">
                <div className="font-black text-slate-900 uppercase text-sm">
                  Credit Card
                </div>
                <div className="text-xs text-slate-500 font-medium">
                  Visa, Mastercard, Amex
                </div>
              </div>
            </button>

            {/* MOBILE */}
            <button
              disabled={isProcessing}
              onClick={() => handlePayment("mobile")}
              className="flex items-center gap-4 p-4 rounded-2xl border-2 border-slate-100 hover:border-orange-500 hover:bg-orange-50 transition-all group">
              <div className="w-12 h-12 bg-orange-100 text-orange-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <Smartphone size={24} />
              </div>
              <div className="text-left">
                <div className="font-black text-slate-900 uppercase text-sm">
                  Mobile Pay
                </div>
                <div className="text-xs text-slate-500 font-medium">
                  QR Code, Apple Pay, Google Pay
                </div>
              </div>
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
        </div>
      </div>
    </div>
  );
};

export default PaymentModal;
