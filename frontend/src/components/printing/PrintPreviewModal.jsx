import React, { useState } from "react";
import { X, Printer, Loader2 } from "lucide-react";
import api from "../../services/api"; // This is your Axios instance

const PrintPreviewModal = ({ open, onClose, order, type = "receipt" }) => {
  const [isPrinting, setIsPrinting] = useState(false);

  if (!open || !order) return null;

  const handleBackendPrint = async () => {
    try {
      setIsPrinting(true);
      const action = type === "kitchen" ? "print-kitchen" : "print-receipt";

      // 1. Use Axios to fetch the HTML with the Authorization header
      // Your 'api' instance should already have the interceptor for the token,
      // but we can also be explicit:
      const token = localStorage.getItem("token");

      const response = await api.get(`/orders/${order.id}/${action}/`, {
        responseType: "text", // We want the raw HTML string from the backend
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "text/html",
        },
      });

      // 2. Open a blank window
      const printWindow = window.open("", "_blank", "width=450,height=600");

      if (printWindow) {
        // 3. Inject the HTML we just fetched into the new window
        printWindow.document.open();
        printWindow.document.write(response.data);
        printWindow.document.close();
        // The <script> window.print() inside the HTML will now trigger automatically
      } else {
        alert("Popup blocked! Please allow popups to print.");
      }

      onClose();
    } catch (err) {
      console.error("Print Error:", err);
      alert("Authentication failed or server error. Please try again.");
    } finally {
      setIsPrinting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
      <div className="bg-white rounded-[32px] shadow-2xl w-full max-w-lg overflow-hidden flex flex-col">
        <div className="p-6 border-b border-slate-100 flex justify-between items-center">
          <h3 className="text-xl font-black text-slate-900 uppercase">
            Print {type}
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-full transition-colors">
            <X
              size={24}
              className="text-slate-400"
            />
          </button>
        </div>

        <div className="p-12 flex flex-col items-center justify-center text-center">
          <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-4">
            <Printer
              size={40}
              className="text-slate-900"
            />
          </div>
          <h4 className="text-lg font-bold text-slate-900">Ready to Print?</h4>
          <p className="text-slate-500 max-w-[280px]">
            This will generate a thermal-optimized ticket for the {type}.
          </p>
        </div>

        <div className="p-6 border-t border-slate-100 bg-white flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-6 py-3 border-2 border-slate-200 rounded-2xl font-black text-slate-600 hover:bg-slate-50">
            CANCEL
          </button>
          <button
            onClick={handleBackendPrint}
            disabled={isPrinting}
            className="flex-[2] flex items-center justify-center gap-2 px-6 py-3 bg-slate-900 text-white rounded-2xl font-black hover:bg-slate-800 shadow-lg disabled:opacity-50">
            {isPrinting ? (
              <Loader2
                className="animate-spin"
                size={20}
              />
            ) : (
              <Printer size={20} />
            )}
            {isPrinting ? "PREPARING..." : "PRINT NOW"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PrintPreviewModal;
