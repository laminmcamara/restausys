import React, { useEffect, useState, useMemo } from "react";
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
  RefreshCw,
  Search,
  X,
} from "lucide-react";

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [printOrder, setPrintOrder] = useState(null);
  const [printType, setPrintType] = useState("receipt");

  // Search state
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchOrders = async () => {
    setIsRefreshing(true);
    try {
      const res = await api.get("/orders/");
      const data = Array.isArray(res.data) ? res.data : res.data.results || [];

      // SORTING LOGIC: Newest first
      const sortedOrders = [...data].sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setOrders(sortedOrders);
    } catch (err) {
      console.error("Fetch failed:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  // CONSISTENT ID LOGIC: Matches Pickup Display
  const formatOrderId = (order) => {
    if (order.display_id) return order.display_id;
    const idStr = String(order.id);
    return idStr.includes("-")
      ? idStr.split("-").pop()?.slice(-4).toUpperCase()
      : idStr.slice(-4).toUpperCase();
  };

  // Filtered Orders Logic
  const filteredOrders = useMemo(() => {
    if (!searchQuery.trim()) return orders;

    const query = searchQuery.toLowerCase();
    return orders.filter((order) => {
      const shortId = formatOrderId(order).toLowerCase();
      const tableName = (order.table_name || "").toLowerCase();
      const customerName = (order.customer_name || "").toLowerCase();

      return (
        shortId.includes(query) ||
        tableName.includes(query) ||
        customerName.includes(query)
      );
    });
  }, [orders, searchQuery]);

  const triggerAction = async (orderId, actionName) => {
    try {
      await api.post(`/orders/${orderId}/${actionName}/`);
      fetchOrders();
    } catch (err) {
      alert(err.response?.data?.error || `Failed to perform ${actionName}`);
    }
  };

  const formatMoney = (value) => Number(value || 0).toFixed(2);

  const statusConfig = {
    DRAFT: {
      color: "bg-slate-400",
      border: "border-l-slate-400",
      label: "Draft",
      action: "send_to_kitchen",
      btnText: "Send to Kitchen",
      icon: Send,
    },
    PLACED: {
      color: "bg-blue-500",
      border: "border-l-blue-500",
      label: "Placed",
      action: "start_preparing",
      btnText: "Start Cooking",
      icon: Clock,
    },
    IN_PROGRESS: {
      color: "bg-amber-500",
      border: "border-l-amber-500",
      label: "Cooking",
      action: "mark_ready",
      btnText: "Mark Ready",
      icon: UtensilsCrossed,
    },
    READY: {
      color: "bg-emerald-500",
      border: "border-l-emerald-500",
      label: "Ready",
      action: "mark_served",
      btnText: "Mark Served",
      icon: CheckCircle2,
    },
    SERVED: {
      color: "bg-purple-600",
      border: "border-l-purple-600",
      label: "Served",
      action: "mark_paid",
      btnText: "Settle Payment",
      icon: Receipt,
    },
    PAID: {
      color: "bg-black",
      border: "border-l-black",
      label: "Paid",
      action: null,
      btnText: null,
      icon: CheckCircle2,
    },
    CANCELED: {
      color: "bg-red-500",
      border: "border-l-red-500",
      label: "Canceled",
      action: null,
      btnText: null,
      icon: AlertCircle,
    },
  };

  if (loading && orders.length === 0) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2
          className="animate-spin text-indigo-600"
          size={40}
        />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6 min-h-screen bg-slate-50/30">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">
            Orders
          </h1>
          <p className="text-slate-500 font-medium">
            Live kitchen and payment flow
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          {/* Search Input */}
          <div className="relative flex-1 md:w-64">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              size={18}
            />
            <input
              type="text"
              placeholder="Search ID or Table..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-10 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <X size={16} />
              </button>
            )}
          </div>

          <button
            onClick={fetchOrders}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-50 transition-all shadow-sm active:scale-95 disabled:opacity-50">
            <RefreshCw
              size={16}
              className={isRefreshing ? "animate-spin" : ""}
            />
            {isRefreshing ? "..." : "Refresh"}
          </button>
        </div>
      </div>

      {filteredOrders.length === 0 ? (
        <div className="bg-white border-2 border-dashed border-slate-200 rounded-[32px] p-20 text-center">
          <UtensilsCrossed
            className="mx-auto text-slate-200 mb-4"
            size={64}
          />
          <p className="text-slate-400 text-lg font-bold">
            {searchQuery
              ? `No orders matching "${searchQuery}"`
              : "No active orders right now."}
          </p>
        </div>
      ) : (
        <div className="grid gap-6">
          {filteredOrders.map((order) => {
            const config = statusConfig[order.status] || statusConfig.DRAFT;
            const Icon = config.icon;
            const shortId = formatOrderId(order);

            return (
              <div
                key={order.id}
                className={`bg-white border border-slate-200 border-l-[6px] ${config.border} rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all animate-in fade-in slide-in-from-top-2`}>
                <div className="p-5">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex gap-4">
                      <div
                        className={`p-3 rounded-2xl text-white ${config.color} shadow-lg`}>
                        <Icon size={24} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-black text-slate-900">
                            #{shortId}
                          </h2>
                          <span
                            className={`text-[10px] font-black text-white px-2.5 py-1 rounded-full uppercase tracking-wider ${config.color}`}>
                            {config.label}
                          </span>
                        </div>
                        <p className="text-sm text-slate-500 font-bold uppercase tracking-tight mt-0.5">
                          {order.table_name
                            ? `Table ${order.table_name}`
                            : order.customer_name || "Takeaway"}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-black text-slate-900">
                        ${formatMoney(order.total_price || order.total)}
                      </p>
                      <div className="flex items-center justify-end gap-1 text-slate-400 font-bold text-[11px]">
                        <Clock size={12} />
                        {new Date(order.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 space-y-2">
                    {order.items?.map((item) => (
                      <div
                        key={item.id}
                        className="flex justify-between items-center text-sm">
                        <div className="flex items-center gap-3">
                          <span className="w-6 h-6 bg-slate-200 text-slate-600 rounded-md flex items-center justify-center text-[10px] font-black">
                            {item.quantity}
                          </span>
                          <span className="text-slate-800 font-bold">
                            {item.product?.name || item.product_name}
                          </span>
                        </div>
                        <span className="text-slate-500 font-mono font-bold">
                          ${formatMoney(item.final_price)}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-between items-center pt-5 mt-2 border-t border-slate-50">
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setPrintOrder(order);
                          setPrintType("bill");
                          setPrintModalOpen(true);
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-black text-slate-600 transition-colors">
                        <Printer size={14} /> BILL
                      </button>
                      <button
                        onClick={() => {
                          setPrintOrder(order);
                          setPrintType("receipt");
                          setPrintModalOpen(true);
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-black text-slate-600 transition-colors">
                        <Receipt size={14} /> RECEIPT
                      </button>
                    </div>

                    {config.action && (
                      <button
                        onClick={() => triggerAction(order.id, config.action)}
                        className={`flex items-center gap-2 px-6 py-3 rounded-xl font-black text-sm text-white shadow-lg transition-all active:scale-95 ${config.color} hover:brightness-110`}>
                        {config.btnText}
                        <ChevronRight size={18} />
                      </button>
                    )}
                  </div>
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
