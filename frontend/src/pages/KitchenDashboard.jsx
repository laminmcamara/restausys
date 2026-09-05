import { useEffect, useMemo, useState, useCallback } from "react";
import {
  ChefHat,
  Clock,
  RefreshCw,
  CheckCircle,
  Flame,
  PackageCheck,
  AlertTriangle,
  UtensilsCrossed,
  Search,
  X,
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
  const [searchQuery, setSearchQuery] = useState("");

  // State to force re-render timers every minute
  const [now, setNow] = useState(Date.now());

  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [printOrder, setPrintOrder] = useState(null);
  const [printType, setPrintType] = useState("receipt");

  const fetchOrders = useCallback(async (isManual = false) => {
    if (isManual) setIsRefreshing(true);
    try {
      setError("");
      const res = await api.get("/orders/");
      const data = res.data.results || res.data || [];
      setOrders(data);
    } catch (err) {
      console.error("Kitchen fetch error:", err);
      setError("Connection Error");
      if (err.response?.status === 401) window.location.href = "/login";
    } finally {
      setLoading(false);
      if (isManual) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
    const pollInterval = setInterval(() => fetchOrders(false), 15000);
    const clockInterval = setInterval(() => setNow(Date.now()), 60000); // Refresh timers every minute
    return () => {
      clearInterval(pollInterval);
      clearInterval(clockInterval);
    };
  }, [fetchOrders]);

  // CONSISTENT ID LOGIC
  const formatOrderId = (order) => {
    if (order.display_id) return order.display_id;
    const idStr = String(order.id);
    return idStr.includes("-")
      ? idStr.split("-").pop()?.slice(-4).toUpperCase()
      : idStr.slice(-4).toUpperCase();
  };

  const handleUpdateStatus = async (order, nextStatus) => {
    try {
      setUpdatingOrderId(order.id);
      let endpoint =
        nextStatus === ORDER_STATUSES.IN_PROGRESS
          ? "start_preparing"
          : nextStatus === ORDER_STATUSES.READY
          ? "mark_ready"
          : "";

      if (endpoint) {
        await api.post(`/orders/${order.id}/${endpoint}/`);
      } else {
        await api.patch(`/orders/${order.id}/`, { status: nextStatus });
      }

      setOrders((prev) =>
        prev.map((item) =>
          item.id === order.id ? { ...item, status: nextStatus } : item
        )
      );
    } catch (err) {
      setError("Failed to update status.");
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
        const typeMatch =
          activeType === "all" ||
          (order.order_type || "dine_in").toLowerCase() === activeType;
        if (!typeMatch) return false;

        if (!searchQuery.trim()) return true;
        const query = searchQuery.toLowerCase();
        const shortId = formatOrderId(order).toLowerCase();
        const table = (order.table_name || "").toLowerCase();
        const customer = (order.customer_name || "").toLowerCase();
        return (
          shortId.includes(query) ||
          table.includes(query) ||
          customer.includes(query)
        );
      })
      .sort(
        (a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
  }, [orders, activeType, searchQuery]);

  const pendingOrders = visibleOrders.filter(
    (o) => normalizeStatus(o.status) === ORDER_STATUSES.PLACED
  );
  const preparingOrders = visibleOrders.filter(
    (o) => normalizeStatus(o.status) === ORDER_STATUSES.IN_PROGRESS
  );
  const readyOrders = visibleOrders.filter(
    (o) => normalizeStatus(o.status) === ORDER_STATUSES.READY
  );

  const lateOrdersCount = visibleOrders.filter(
    (o) =>
      getMinutesSince(o.created_at) > 15 &&
      normalizeStatus(o.status) !== ORDER_STATUSES.READY
  ).length;

  if (loading)
    return (
      <div className="flex items-center justify-center py-20 text-slate-500 animate-pulse font-black tracking-widest">
        INITIALIZING KITCHEN DISPLAY...
      </div>
    );

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto p-4">
      {/* Header & Search */}
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between bg-white p-6 rounded-[32px] border border-slate-200 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="bg-orange-500 p-3 rounded-2xl text-white shadow-lg shadow-orange-200">
            <ChefHat size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">
              Kitchen Display
            </h1>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              Live Prep Management
            </p>
          </div>
        </div>

        <div className="flex flex-col md:flex-row items-center gap-3">
          {/* Search Bar */}
          <div className="relative w-full md:w-80">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
              size={18}
            />
            <input
              type="text"
              placeholder="Search Order ID or Table..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-10 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-orange-500/20 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <X size={16} />
              </button>
            )}
          </div>

          <button
            onClick={() => fetchOrders(true)}
            disabled={isRefreshing}
            className="w-full md:w-auto inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-8 py-3 text-sm font-black text-white hover:bg-slate-800 transition-all active:scale-95 disabled:opacity-50">
            <RefreshCw
              size={18}
              className={isRefreshing ? "animate-spin" : ""}
            />
            {isRefreshing ? "SYNCING..." : "REFRESH"}
          </button>
        </div>
      </div>

      {/* Stats */}
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
          title="Late (>15m)"
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
            className={`rounded-xl px-6 py-2 text-[10px] font-black uppercase tracking-[0.2em] transition-all ${
              activeType === type
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}>
            {type.replace("_", " ")}
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
          onPrint={(o) => {
            setPrintOrder(o);
            setPrintType("kitchen");
            setPrintModalOpen(true);
          }}
          updatingOrderId={updatingOrderId}
          formatId={formatOrderId}
        />
        <KitchenColumn
          title="PREPARING"
          color="blue"
          orders={preparingOrders}
          actionLabel="MARK AS READY"
          actionIcon={<CheckCircle size={18} />}
          onAction={(order) => handleUpdateStatus(order, ORDER_STATUSES.READY)}
          onPrint={(o) => {
            setPrintOrder(o);
            setPrintType("kitchen");
            setPrintModalOpen(true);
          }}
          updatingOrderId={updatingOrderId}
          formatId={formatOrderId}
        />
        <KitchenColumn
          title="READY TO SERVE"
          color="green"
          orders={readyOrders}
          onPrint={(o) => {
            setPrintOrder(o);
            setPrintType("kitchen");
            setPrintModalOpen(true);
          }}
          updatingOrderId={updatingOrderId}
          formatId={formatOrderId}
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
    <div className="bg-white p-5 rounded-[32px] border border-slate-200 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">
          {title}
        </p>
        <p className="text-3xl font-black text-slate-900">{value}</p>
      </div>
      <div className={`${colors[color]} p-3 rounded-2xl text-white shadow-lg`}>
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
  formatId,
}) {
  const accents = {
    yellow: "border-t-yellow-500",
    blue: "border-t-blue-500",
    green: "border-t-emerald-500",
  };
  return (
    <div
      className={`bg-slate-100/50 rounded-[40px] border-t-8 ${accents[color]} p-5 min-h-[70vh]`}>
      <div className="flex items-center justify-between mb-6 px-2">
        <h2 className="font-black text-slate-800 tracking-tight text-sm uppercase">
          {title}
        </h2>
        <span className="bg-white px-4 py-1.5 rounded-full text-xs font-black text-slate-500 shadow-sm border border-slate-200">
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
            formatId={formatId}
          />
        ))}
        {orders.length === 0 && (
          <div className="py-20 text-center text-slate-400 font-bold italic text-sm opacity-50">
            NO ACTIVE ORDERS
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
  formatId,
}) {
  const items = normalizeItems(order);
  const minutes = getMinutesSince(order.created_at);
  const isLate = minutes > 15;

  return (
    <div
      className={`bg-white rounded-3xl p-5 shadow-sm border-2 transition-all ${
        isLate ? "border-rose-200 animate-pulse" : "border-transparent"
      }`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">
            ORDER
          </span>
          <h3 className="text-xl font-black text-slate-900 leading-none">
            #{formatId(order)}
          </h3>
          <p className="text-[10px] font-black text-orange-600 uppercase mt-1">
            {order.table_name
              ? `Table ${order.table_name}`
              : order.customer_name || "Takeaway"}
          </p>
        </div>
        <div
          className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 ${
            isLate ? "bg-rose-100 text-rose-600" : "bg-slate-100 text-slate-600"
          }`}>
          <Clock size={14} />
          <span className="text-xs font-black">{minutes}m</span>
        </div>
      </div>

      <div className="bg-slate-50 rounded-2xl p-4 mb-4 space-y-3">
        {items.map((item, i) => (
          <div
            key={i}
            className="flex gap-3">
            <span className="bg-slate-900 text-white w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-black shrink-0">
              {item.quantity}
            </span>
            <div>
              <p className="text-sm font-black text-slate-800 uppercase">
                {item.product_name}
              </p>
              {item.modifiers.map((m, idx) => (
                <p
                  key={idx}
                  className="text-[10px] text-slate-500 font-bold">
                  • {m}
                </p>
              ))}
              {item.note && (
                <p className="text-[10px] text-orange-600 font-bold mt-1 italic">
                  Note: {item.note}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 mb-3">
        <button
          onClick={() => onPrint(order)}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-[10px] font-black text-slate-600 transition-colors">
          <UtensilsCrossed size={14} /> TICKET
        </button>
      </div>

      {onAction && (
        <button
          onClick={() => onAction(order)}
          disabled={isUpdating}
          className="w-full flex items-center justify-center gap-2 py-3.5 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white rounded-2xl text-xs font-black transition-all active:scale-[0.98] shadow-lg shadow-slate-200">
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
  const rawItems = order.items || order.order_items || [];
  return rawItems.map((item) => ({
    product_name:
      item.product_name || item.name || item.product?.name || "Unknown Item",
    quantity: item.quantity || 1,
    modifiers: Array.isArray(item.modifiers)
      ? item.modifiers.map((m) => (typeof m === "string" ? m : m.name))
      : [],
    note: item.note || item.notes || "",
  }));
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
