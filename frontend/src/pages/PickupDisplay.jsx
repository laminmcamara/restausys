import React, { useEffect, useState } from "react";
import { CheckCircle2, Timer, Eye, EyeOff, Loader2 } from "lucide-react";
import api from "../services/api";
import { useAuth } from "../hooks/useAuth";
import useDisplaySocket from "../hooks/useDisplaySocket";

const ORDER_STATUSES = {
  PLACED: "PLACED",
  IN_PROGRESS: "IN_PROGRESS",
  READY: "READY",
  SERVED: "SERVED",
  COMPLETED: "COMPLETED",
  CANCELED: "CANCELED",
};

const normalizeStatus = (status) => {
  return String(status || "")
    .trim()
    .toUpperCase();
};

const getStatusLabel = (status) => {
  const s = normalizeStatus(status);
  if (s === ORDER_STATUSES.IN_PROGRESS) return "Preparing";
  if (s === ORDER_STATUSES.READY) return "Ready";
  if (s === ORDER_STATUSES.PLACED) return "New";
  return status || "Unknown";
};

export default function PickupDisplay() {
  const { user, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState([]);
  const [isStaffMode, setIsStaffMode] = useState(false);

  const fetchOrders = async () => {
    const restaurantId = user?.restaurant?.id || user?.restaurant;
    if (!restaurantId) return;

    try {
      const { data } = await api.get("/orders/");
      const ordersData = data.results || data || [];

      const processed = ordersData
        .filter((order) => {
          const s = normalizeStatus(order.status);
          return (
            s === ORDER_STATUSES.PLACED ||
            s === ORDER_STATUSES.IN_PROGRESS ||
            s === ORDER_STATUSES.READY
          );
        })
        .sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );

      setOrders(processed);
    } catch (error) {
      console.error("Fetch orders failed:", error);
    }
  };

  useEffect(() => {
    if (!authLoading && user) {
      fetchOrders();
      const interval = setInterval(fetchOrders, 10000);
      return () => clearInterval(interval);
    }
  }, [user, authLoading]);

  useDisplaySocket(
    user?.restaurant?.id || user?.restaurant,
    (data) => {
      if (data.event === "ORDER_STATUS_UPDATED") fetchOrders();
    },
    !!user?.restaurant
  );

  // Use the exact order_number as the ticket number
  const formatOrderId = (order) => {
    if (order.order_number !== undefined && order.order_number !== null) {
      return String(order.order_number);
    }
    if (order.display_id) {
      return String(order.display_id);
    }
    const idStr = String(order.id || "");
    return idStr.includes("-")
      ? idStr.split("-").pop()?.slice(-4).toUpperCase() || idStr
      : idStr;
  };

  const markServed = async (id) => {
    try {
      await api.post(`/orders/${id}/mark_served/`);
      fetchOrders();
    } catch (error) {
      console.error("Mark served failed:", error);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center text-white">
        <p className="text-xl font-bold">Not authenticated</p>
      </div>
    );
  }

  const preparingOrders = orders.filter(
    (o) => normalizeStatus(o.status) === ORDER_STATUSES.IN_PROGRESS
  );
  const readyOrders = orders.filter(
    (o) => normalizeStatus(o.status) === ORDER_STATUSES.READY
  );

  return (
    <div className="min-h-screen bg-[#0f172a] text-white p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-black uppercase tracking-tight">
              Pickup Display
            </h1>
            <p className="text-slate-400 text-sm font-bold mt-1">
              Live Order Status
            </p>
          </div>

          <button
            type="button"
            onClick={() => setIsStaffMode(!isStaffMode)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-sm font-black transition-all"
          >
            {isStaffMode ? <EyeOff size={18} /> : <Eye size={18} />}
            {isStaffMode ? "HIDE CONTROLS" : "STAFF MODE"}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* PREPARING */}
          <div className="bg-slate-800/50 rounded-3xl p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-black uppercase tracking-tight text-blue-400">
                Preparing
              </h2>
              <span className="bg-blue-500/20 text-blue-400 px-4 py-1.5 rounded-full text-xs font-black">
                {preparingOrders.length}
              </span>
            </div>

            {preparingOrders.length === 0 ? (
              <p className="text-slate-500 font-bold italic text-center py-12">
                No orders preparing
              </p>
            ) : (
              <div className="space-y-4">
                {preparingOrders.map((order) => (
                  <PickupOrderCard
                    key={String(order.id)}
                    order={order}
                    formatId={formatOrderId}
                    statusLabel={getStatusLabel(order.status)}
                    isStaffMode={isStaffMode}
                    onMarkServed={markServed}
                    highlightColor="blue"
                  />
                ))}
              </div>
            )}
          </div>

          {/* READY FOR PICKUP */}
          <div className="bg-slate-800/50 rounded-3xl p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-black uppercase tracking-tight text-emerald-400">
                Ready for Pickup
              </h2>
              <span className="bg-emerald-500/20 text-emerald-400 px-4 py-1.5 rounded-full text-xs font-black">
                {readyOrders.length}
              </span>
            </div>

            {readyOrders.length === 0 ? (
              <p className="text-slate-500 font-bold italic text-center py-12">
                No ready orders
              </p>
            ) : (
              <div className="space-y-4">
                {readyOrders.map((order) => (
                  <PickupOrderCard
                    key={String(order.id)}
                    order={order}
                    formatId={formatOrderId}
                    statusLabel={getStatusLabel(order.status)}
                    isStaffMode={isStaffMode}
                    onMarkServed={markServed}
                    highlightColor="emerald"
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PickupOrderCard({
  order,
  formatId,
  statusLabel,
  isStaffMode,
  onMarkServed,
  highlightColor = "blue",
}) {
  const minutesAgo = Math.max(
    0,
    Math.floor((Date.now() - new Date(order.created_at).getTime()) / 60000)
  );

  const isReady = normalizeStatus(order.status) === ORDER_STATUSES.READY;

  const colorClasses = {
    blue: {
      badge: "bg-blue-500/20 text-blue-400",
      border: "border-blue-500/30",
    },
    emerald: {
      badge: "bg-emerald-500/20 text-emerald-400",
      border: "border-emerald-500/50",
    },
  };

  const colors = colorClasses[highlightColor] || colorClasses.blue;

  return (
    <div
      className={`bg-slate-900/50 rounded-2xl p-5 border-2 transition-all ${colors.border}`}>
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl font-black text-white">
              #{formatId(order)}
            </span>
            <span
              className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider ${colors.badge}`}>
              {statusLabel}
            </span>
          </div>

          <p className="text-slate-400 text-sm font-bold">
            {order.order_type === "DINE_IN" || order.order_type === "dine_in"
              ? order.table?.table_number || order.table_number
                ? `Table ${order.table?.table_number || order.table_number}`
                : "Dine-in"
              : order.order_type === "DELIVERY" ||
                order.order_type === "delivery"
              ? order.customer?.name || order.customer_name || "Delivery"
              : order.customer?.name || order.customer_name || "Takeaway"}
          </p>
        </div>

        <div className="flex items-center gap-1.5 text-slate-400">
          <Timer size={14} />
          <span className="text-xs font-black">{minutesAgo}m</span>
        </div>
      </div>

      <div className="space-y-2 mb-4">
        {(order.items || order.order_items || [])
          .slice(0, 3)
          .map((item, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2">
              <span className="bg-slate-800 text-slate-300 w-5 h-5 rounded flex items-center justify-center text-[10px] font-black shrink-0">
                {item.quantity || 1}
              </span>
              <span className="text-sm font-bold text-slate-200">
                {item.product_name || item.product?.name || item.name || "Item"}
              </span>
            </div>
          ))}
      </div>

      {isStaffMode && isReady && (
        <button
          type="button"
          onClick={() => onMarkServed(order.id)}
          className="w-full flex items-center justify-center gap-2 py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-xl text-xs font-black transition-all">
          <CheckCircle2 size={16} />
          MARK AS PICKED UP
        </button>
      )}
    </div>
  );
}