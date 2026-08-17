import React from "react";
import PrintableOrderDocument from "./PrintableOrderDocument";

const titleMap = {
  kitchen: "Kitchen Ticket",
  bar: "Bar Ticket",
  bill: "Customer Bill",
  receipt: "Customer Receipt",
  copy: "Order Copy",
};

const PrintPreviewModal = ({ open, onClose, order, type = "receipt" }) => {
  if (!open || !order) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="print-modal-backdrop">
      <div className="print-modal">
        <div className="print-modal-header no-print">
          <div>
            <h2>{titleMap[type] || "Print Preview"}</h2>
            <p>Preview before printing.</p>
          </div>

          <button
            type="button"
            className="close-btn"
            onClick={onClose}>
            ×
          </button>
        </div>

        <div className="print-modal-body">
          <PrintableOrderDocument
            order={order}
            type={type}
          />
        </div>

        <div className="print-modal-footer no-print">
          <button
            type="button"
            className="secondary-btn"
            onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="primary-btn"
            onClick={handlePrint}>
            Print
          </button>
        </div>
      </div>

      <style>{`
        .print-modal-backdrop {
          position: fixed;
          inset: 0;
          z-index: 9999;
          background: rgba(15, 23, 42, 0.65);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }

        .print-modal {
          width: 100%;
          max-width: 720px;
          max-height: 92vh;
          background: #f9fafb;
          border-radius: 18px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          box-shadow: 0 25px 60px rgba(0, 0, 0, 0.25);
        }

        .print-modal-header {
          padding: 18px 22px;
          background: #ffffff;
          border-bottom: 1px solid #e5e7eb;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
        }

        .print-modal-header h2 {
          margin: 0;
          font-size: 20px;
          color: #111827;
        }

        .print-modal-header p {
          margin: 4px 0 0;
          color: #6b7280;
          font-size: 13px;
        }

        .close-btn {
          width: 36px;
          height: 36px;
          border: none;
          border-radius: 999px;
          background: #f3f4f6;
          color: #111827;
          font-size: 24px;
          cursor: pointer;
          line-height: 1;
        }

        .close-btn:hover {
          background: #e5e7eb;
        }

        .print-modal-body {
          overflow-y: auto;
          padding: 24px;
        }

        .print-modal-footer {
          padding: 16px 22px;
          background: #ffffff;
          border-top: 1px solid #e5e7eb;
          display: flex;
          justify-content: flex-end;
          gap: 10px;
        }

        .secondary-btn,
        .primary-btn {
          border: none;
          border-radius: 10px;
          padding: 10px 16px;
          font-weight: 700;
          cursor: pointer;
        }

        .secondary-btn {
          background: #f3f4f6;
          color: #111827;
        }

        .primary-btn {
          background: #2563eb;
          color: #ffffff;
        }

        .secondary-btn:hover {
          background: #e5e7eb;
        }

        .primary-btn:hover {
          background: #1d4ed8;
        }

        @media print {
          .no-print,
          .print-modal-header,
          .print-modal-footer,
          .print-modal-backdrop,
          .print-modal {
            background: transparent !important;
            box-shadow: none !important;
            border: none !important;
          }

          .print-modal-backdrop {
            position: static !important;
            padding: 0 !important;
            display: block !important;
          }

          .print-modal {
            max-width: none !important;
            max-height: none !important;
            overflow: visible !important;
          }

          .print-modal-body {
            padding: 0 !important;
            overflow: visible !important;
          }
        }
      `}</style>
    </div>
  );
};

export default PrintPreviewModal;
