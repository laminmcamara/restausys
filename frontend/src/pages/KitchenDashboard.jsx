import { useEffect, useMemo, useState, useCallback } from "react";
import {
  ChefHat,
  Clock,
  RefreshCw,
  CheckCircle,
  Flame,
  PackageCheck,
  AlertTriangle,
  Receipt,
  FileText,
  UtensilsCrossed,
} from "lucide-react";
import api from "../services/api";
import PrintPreviewModal from "../components/printing/PrintPreviewModal";

const ORDER_STATUSES = {
  DRAFT: "DRAFT",
  PLACED: "PLACED",
  IN_PROGRESS: "IN_PROGRESS",
  READY: "READY",
  SERVED: "SERVED",
  COMPLETED: "COMPLETED",
  CANCELED: "CANCELED",
};

const TYPE_FILTERS = ["all", "dine_in", "takeout", "delivery"];

export default function KitchenDashboard() {
  const [orders, setOrders] = useState([]);
  const [activeType, setActiveType] = useState("all");
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [updatingOrderId, setUpdatingOrderId] = useState(null);
  const [error, setError] = useState("");

  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [printOrder, setPrintOrder] = useState(null);
  const [printType, setPrintType] = useState("receipt");

  // 1. FIXED REFRESH LOGIC
  const fetchOrders = useCallback(async (isManual = false) => {
    if (isManual) setIsRefreshing(true);
    try {
      setError("");
      const res = await api.get("/orders/");
      const data = Array.isArray(res.data)
        ? res.data
        : res.data?.results || res.data?.orders || res.data?.data || [];

      setOrders(data);
    } catch (err) {
      console.error("Failed to fetch kitchen orders:", err);
      setError("Failed to load kitchen orders.");
    } finally {
      setLoading(false);
      if (isManual) {
        // Artificial delay for visual feedback
        setTimeout(() => setIsRefreshing(false), 600);
      }
    }
  }, []);

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(() => fetchOrders(false), 10000); // Auto-refresh every 10s
    return () => clearInterval(interval);
  }, [fetchOrders]);

  const openPrintPreview = (order, type) => {
    setPrintOrder(order);
    setPrintType(type);
    setPrintModalOpen(true);
  };

  // 2. UPDATED STATUS ACTIONS (Using the new backend POST actions)
  const handleUpdateStatus = async (order, nextStatus) => {
    try {
      setUpdatingOrderId(order.id);
      setError("");

      // Map status to our new backend action endpoints
      let endpoint = "";
      if (nextStatus === ORDER_STATUSES.IN_PROGRESS)
        endpoint = "start_preparing";
      if (nextStatus === ORDER_STATUSES.READY) endpoint = "mark_ready";

      if (endpoint) {
        await api.post(`/orders/${order.id}/${endpoint}/`);
      } else {
        // Fallback to PATCH if no specific action exists
        await api.patch(`/orders/${order.id}/`, { status: nextStatus });
      }

      // Optimistic UI Update
      setOrders((prev) =>
        prev.map((item) =>
          item.id === order.id ? { ...item, status: nextStatus } : item
        )
      );
    } catch (err) {
      console.error("Failed to update order status:", err);
      setError("Failed to update order status.");
    } finally {
      setUpdatingOrderId(null);
    }
  };

  const visibleOrders = useMemo(() => {
    return orders
      .filter((order) =>
        [
          ORDER_STATUSES.PLACED,
          ORDER_STATUSES.IN_PROGRESS,
          ORDER_STATUSES.READY,
        ].includes(normalizeStatus(order.status))
      )
      .filter(isRecentKitchenOrder)
      .filter((order) => {
        if (activeType === "all") return true;
        const orderType = (
          order.order_type ||
          order.type ||
          "dine_in"
        ).toLowerCase();
        return orderType === activeType;
      })
      .sort(
        (a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
  }, [orders, activeType]);

  const pendingOrders = visibleOrders.filter(
    (o) => normalizeStatus(o.status) === ORDER_STATUSES.PLACED
  );
  const preparingOrders = visibleOrders.filter(
    (o) => normalizeStatus(o.status) === ORDER_STATUSES.IN_PROGRESS
  );
  const readyOrders = visibleOrders.filter(
    (o) => normalizeStatus(o.status) === ORDER_STATUSES.READY
  );

  const lateOrdersCount = visibleOrders.filter((order) => {
    const minutes = getMinutesSince(order.created_at);
    return (
      minutes > 15 && normalizeStatus(order.status) !== ORDER_STATUSES.READY
    );
  }).length;

  if (loading)
    return (
      <div className="flex items-center justify-center py-20 text-gray-500 animate-pulse font-bold">
        INITIALIZING KITCHEN DISPLAY...
      </div>
    );

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto p-4">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <div className="bg-orange-500 p-2 rounded-xl text-white">
              <ChefHat size={24} />
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">
              Kitchen Display System
            </h1>
          </div>
          <p className="mt-1 text-sm font-medium text-slate-500">
            Live order tracking and preparation management
          </p>
        </div>

        <button
          type="button"
          onClick={() => fetchOrders(true)}
          disabled={isRefreshing}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-6 py-3 text-sm font-black text-white hover:bg-slate-800 transition-all active:scale-95 disabled:opacity-50">
          <RefreshCw
            size={18}
            className={isRefreshing ? "animate-spin" : ""}
          />
          {isRefreshing ? "REFRESHING..." : "REFRESH BOARD"}
        </button>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KitchenStatCard
          title="New"
          value={pendingOrders.length}
          icon={<Clock />}
          color="yellow"
        />
        <KitchenStatCard
          title="Cooking"
          value={preparingOrders.length}
          icon={<Flame />}
          color="blue"
        />
        <KitchenStatCard
          title="Ready"
          value={readyOrders.length}
          icon={<PackageCheck />}
          color="green"
        />
        <KitchenStatCard
          title="Late"
          value={lateOrdersCount}
          icon={<AlertTriangle />}
          color="red"
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 bg-slate-100 p-1.5 rounded-2xl w-fit">
        {TYPE_FILTERS.map((type) => (
          <button
            key={type}
            onClick={() => setActiveType(type)}
            className={`rounded-xl px-6 py-2 text-xs font-black uppercase tracking-widest transition-all ${
              activeType === type
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}>
            {formatOrderType(type)}
          </button>
        ))}
      </div>

      {/* Columns */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <KitchenColumn
          title="NEW ORDERS"
          color="yellow"
          orders={pendingOrders}
          actionLabel="START COOKING"
          actionIcon={<Flame size={18} />}
          onAction={(order) =>
            handleUpdateStatus(order, ORDER_STATUSES.IN_PROGRESS)
          }
          onPrint={openPrintPreview}
          updatingOrderId={updatingOrderId}
        />
        <KitchenColumn
          title="PREPARING"
          color="blue"
          orders={preparingOrders}
          actionLabel="MARK AS READY"
          actionIcon={<CheckCircle size={18} />}
          onAction={(order) => handleUpdateStatus(order, ORDER_STATUSES.READY)}
          onPrint={openPrintPreview}
          updatingOrderId={updatingOrderId}
        />
        <KitchenColumn
          title="READY / SERVING"
          color="green"
          orders={readyOrders}
          actionLabel={null}
          onPrint={openPrintPreview}
          updatingOrderId={updatingOrderId}
        />
      </div>

      <PrintPreviewModal
        open={printModalOpen}
        onClose={() => setPrintModalOpen(false)}
        order={printOrder}
        type={printType}
      />
    </div>
  );
}

/* ================= Sub-Components ================= */

function KitchenStatCard({ title, value, icon, color }) {
  const colors = {
    yellow: "bg-yellow-500",
    blue: "bg-blue-500",
    green: "bg-emerald-500",
    red: "bg-rose-500",
  };
  return (
    <div className="bg-white p-5 rounded-3xl border border-slate-200 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">
          {title}
        </p>
        <p className="text-3xl font-black text-slate-900">{value}</p>
      </div>
      <div
        className={`${colors[color]} p-3 rounded-2xl text-white shadow-lg shadow-${color}-200`}>
        {icon}
      </div>
    </div>
  );
}

function KitchenColumn({
  title,
  color,
  orders,
  actionLabel,
  actionIcon,
  onAction,
  onPrint,
  updatingOrderId,
}) {
  const accents = {
    yellow: "border-t-yellow-500",
    blue: "border-t-blue-500",
    green: "border-t-emerald-500",
  };
  return (
    <div
      className={`bg-slate-100/50 rounded-3xl border-t-4 ${accents[color]} p-4 min-h-[70vh]`}>
      <div className="flex items-center justify-between mb-4 px-2">
        <h2 className="font-black text-slate-800 tracking-tight text-sm uppercase">
          {title}
        </h2>
        <span className="bg-white px-3 py-1 rounded-full text-xs font-black text-slate-500 shadow-sm border border-slate-200">
          {orders.length}
        </span>
      </div>
      <div className="space-y-4">
        {orders.map((order) => (
          <KitchenOrderCard
            key={order.id}
            order={order}
            onAction={onAction}
            actionLabel={actionLabel}
            actionIcon={actionIcon}
            onPrint={onPrint}
            isUpdating={updatingOrderId === order.id}
          />
        ))}
        {orders.length === 0 && (
          <div className="py-20 text-center text-slate-400 font-bold italic text-sm opacity-50">
            NO ORDERS IN THIS STAGE
          </div>
        )}
      </div>
    </div>
  );
}

function KitchenOrderCard({
  order,
  onAction,
  actionLabel,
  actionIcon,
  onPrint,
  isUpdating,
}) {
  const items = normalizeItems(order);
  const minutes = getMinutesSince(order.created_at);
  const isLate = minutes > 15;

  return (
    <div
      className={`bg-white rounded-2xl p-5 shadow-sm border-2 ${
        isLate ? "border-rose-200 animate-pulse" : "border-transparent"
      }`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">
            Order Ref
          </span>
          <h3 className="text-lg font-black text-slate-900 leading-none">
            #{String(order.display_id || order.id).slice(-5)}
          </h3>
        </div>
        <div
          className={`px-3 py-1 rounded-lg flex items-center gap-1.5 ${
            isLate ? "bg-rose-100 text-rose-600" : "bg-slate-100 text-slate-600"
          }`}>
          <Clock size={14} />
          <span className="text-xs font-black">{minutes}m</span>
        </div>
      </div>

      <div className="bg-slate-50 rounded-xl p-3 mb-4 space-y-3">
        {items.map((item, i) => (
          <div
            key={i}
            className="flex gap-3">
            <span className="bg-slate-900 text-white w-6 h-6 rounded flex items-center justify-center text-xs font-black shrink-0">
              {item.quantity}
            </span>
            <div>
              <p className="text-sm font-black text-slate-800 uppercase">
                {item.name}
              </p>
              {item.modifiers.map((m, idx) => (
                <p
                  key={idx}
                  className="text-[10px] text-slate-500 font-bold">
                  • {m}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 mb-3">
        <button
          onClick={() => onPrint(order, "kitchen")}
          className="flex-1 flex items-center justify-center gap-2 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-[10px] font-black text-slate-600 transition-colors">
          <UtensilsCrossed size={14} /> KITCHEN TICKET
        </button>
      </div>

      {onAction && (
        <button
          onClick={() => onAction(order)}
          disabled={isUpdating}
          className="w-full flex items-center justify-center gap-2 py-3 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white rounded-xl text-xs font-black transition-all active:scale-[0.98]">
          {isUpdating ? (
            <RefreshCw
              size={14}
              className="animate-spin"
            />
          ) : (
            actionIcon
          )}
          {isUpdating ? "UPDATING..." : actionLabel}
        </button>
      )}
    </div>
  );
}

/* ================= Helpers ================= */
function normalizeStatus(status) {
  return String(status || "").toUpperCase();
}

function normalizeItems(order) {
  // 1. Look for items in all possible field names
  const rawItems = order.items || order.order_items || order.orderItems || [];

  if (!Array.isArray(rawItems)) return [];

  return rawItems.map((item) => {
    // 2. Try to find the name in the item itself, then in a nested product object
    const name =
      item.product_name ||
      item.name ||
      (item.product && (item.product.name || item.product.title)) ||
      "Unknown Item";

    // 3. Try to find quantity (default to 1)
    const quantity = item.quantity || item.qty || 1;

    // 4. Handle modifiers/notes
    const modifiers = Array.isArray(item.modifiers)
      ? item.modifiers.map((m) =>
          typeof m === "string" ? m : m.name || m.label
        )
      : [];

    const note = item.note || item.notes || item.special_instructions || "";

    return {
      name,
      quantity,
      modifiers,
      note,
    };
  });
}


function getMinutesSince(dateValue) {
  if (!dateValue) return 0;
  const diff = Date.now() - new Date(dateValue).getTime();
  return Math.max(0, Math.floor(diff / 60000));
}

function isRecentKitchenOrder(order) {
  const ageHours =
    (Date.now() - new Date(order.created_at).getTime()) / (1000 * 60 * 60);
  return ageHours <= 24;
}

function formatOrderType(type) {
  return type.replace("_", " ");
}
