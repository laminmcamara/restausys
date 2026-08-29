import React, { useEffect, useState } from "react";
import api from "../services/api";
import PrintPreviewModal from "../components/printing/PrintPreviewModal";
import {
  Printer,
  ChevronRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  Receipt,
  UtensilsCrossed,
  Send,
  Loader2,
} from "lucide-react";

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [printOrder, setPrintOrder] = useState(null);
  const [printType, setPrintType] = useState("receipt");

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchOrders = async () => {
    try {
      const res = await api.get("/orders/");
      const normalizedOrders = Array.isArray(res.data)
        ? res.data
        : res.data.results || [];
      setOrders(normalizedOrders);
    } catch (err) {
      console.error("Fetch failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const triggerAction = async (orderId, actionName) => {
    try {
      await api.post(`/orders/${orderId}/${actionName}/`);
      fetchOrders();
    } catch (err) {
      alert(err.response?.data?.error || `Failed to perform ${actionName}`);
    }
  };

  const formatMoney = (value) => Number(value || 0).toFixed(2);

  // Status configuration mapping backend status to UI elements
  const statusConfig = {
    DRAFT: {
      color: "bg-slate-400",
      label: "Draft",
      action: "send_to_kitchen",
      btnText: "Send to Kitchen",
      icon: Send,
    },
    PLACED: {
      color: "bg-blue-500",
      label: "Placed",
      action: "start_preparing",
      btnText: "Start Cooking",
      icon: Clock,
    },
    IN_PROGRESS: {
      color: "bg-amber-500",
      label: "Cooking",
      action: "mark_ready",
      btnText: "Mark Ready",
      icon: UtensilsCrossed,
    },
    READY: {
      color: "bg-emerald-500",
      label: "Ready",
      action: "mark_served",
      btnText: "Mark Served",
      icon: CheckCircle2,
    },
    SERVED: {
      color: "bg-purple-600",
      label: "Served",
      action: "mark_paid",
      btnText: "Settle Payment",
      icon: Receipt,
    },
    PAID: {
      color: "bg-black",
      label: "Paid",
      action: null,
      btnText: null,
      icon: CheckCircle2,
    },
    CANCELED: {
      color: "bg-red-500",
      label: "Canceled",
      action: null,
      btnText: null,
      icon: AlertCircle,
    },
  };

  if (loading && orders.length === 0) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2
          className="animate-spin text-indigo-600"
          size={32}
        />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-black text-slate-900">
            Orders Dashboard
          </h1>
          <p className="text-slate-500 text-sm">
            Manage live order flow and status transitions.
          </p>
        </div>
        <button
          onClick={fetchOrders}
          className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-50 transition-colors shadow-sm">
          Refresh
        </button>
      </div>

      {orders.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded-3xl p-20 text-center">
          <UtensilsCrossed
            className="mx-auto text-slate-200 mb-4"
            size={48}
          />
          <p className="text-slate-400 font-medium">No active orders found.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {orders.map((order) => {
            const config = statusConfig[order.status] || statusConfig.DRAFT;
            const Icon = config.icon;

            return (
              <div
                key={order.id}
                className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex gap-4">
                    <div
                      className={`p-3 rounded-xl text-white ${config.color} shadow-inner`}>
                      <Icon size={24} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-black text-slate-900">
                          Order #{order.display_id || order.id}
                        </h2>
                        <span
                          className={`text-[10px] font-bold text-white px-2 py-0.5 rounded-full uppercase ${config.color}`}>
                          {config.label}
                        </span>
                      </div>
                      <p className="text-sm text-slate-500 font-medium">
                        {order.table_name
                          ? `Table ${order.table_name}`
                          : "Walk-in / Takeaway"}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-black text-slate-900">
                      ${formatMoney(order.total_price || order.total)}
                    </p>
                    <p className="text-[10px] text-slate-400 uppercase font-bold">
                      {new Date(order.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>

                {/* Items List */}
                <div className="bg-slate-50/50 rounded-xl p-3 my-3 space-y-1">
                  {order.items?.map((item) => (
                    <div
                      key={item.id}
                      className="flex justify-between text-sm">
                      <span className="text-slate-700 font-medium">
                        {item.quantity}x {item.product?.name || item.name}
                        {item.modifiers?.length > 0 && (
                          <span className="text-[10px] text-slate-400 block ml-4">
                            {item.modifiers.map((m) => m.name).join(", ")}
                          </span>
                        )}
                      </span>
                      <span className="text-slate-600 font-bold">
                        ${formatMoney(item.final_price)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Actions Footer */}
                <div className="flex justify-between items-center pt-2">
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setPrintOrder(order);
                        setPrintType("bill");
                        setPrintModalOpen(true);
                      }}
                      className="flex items-center gap-2 px-3 py-2 border border-slate-200 rounded-lg hover:bg-slate-50 text-xs font-bold text-slate-600 transition-colors">
                      <Printer size={14} /> Bill
                    </button>
                    <button
                      onClick={() => {
                        setPrintOrder(order);
                        setPrintType("receipt");
                        setPrintModalOpen(true);
                      }}
                      className="flex items-center gap-2 px-3 py-2 border border-slate-200 rounded-lg hover:bg-slate-50 text-xs font-bold text-slate-600 transition-colors">
                      <Receipt size={14} /> Receipt
                    </button>
                  </div>

                  {config.action && (
                    <button
                      onClick={() => triggerAction(order.id, config.action)}
                      className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-black text-sm text-white shadow-lg transition-all active:scale-95 ${config.color} hover:brightness-110`}>
                      {config.btnText}
                      <ChevronRight size={16} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {printOrder && (
        <PrintPreviewModal
          open={printModalOpen}
          onClose={() => setPrintModalOpen(false)}
          order={printOrder}
          type={printType}
        />
      )}
    </div>
  );
}
