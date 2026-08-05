import { useEffect, useMemo, useState } from "react";
import {
  ChefHat,
  Clock,
  RefreshCw,
  CheckCircle,
  Flame,
  PackageCheck,
  AlertTriangle,
} from "lucide-react";
import api from "../services/api";

const ORDER_STATUSES = {
  DRAFT: "DRAFT",
  PLACED: "PLACED",
  IN_PROGRESS: "IN_PROGRESS",
  READY: "READY",
  COMPLETED: "COMPLETED",
  CANCELLED: "CANCELLED",
};

const TYPE_FILTERS = ["all", "dine_in", "takeout", "delivery"];

export default function KitchenDashboard() {
  const [orders, setOrders] = useState([]);
  const [activeType, setActiveType] = useState("all");
  const [loading, setLoading] = useState(true);
  const [updatingOrderId, setUpdatingOrderId] = useState(null);
  const [error, setError] = useState("");

  const fetchOrders = async () => {
    try {
      setError("");

      const res = await api.get("/orders/");
      console.log("KITCHEN ORDERS RESPONSE:", res.data);

      const data = Array.isArray(res.data)
        ? res.data
        : res.data?.results || res.data?.orders || res.data?.data || [];

      setOrders(data);
    } catch (err) {
      console.error("Failed to fetch kitchen orders:", err);
      setError("Failed to load kitchen orders.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();

    const interval = setInterval(fetchOrders, 5000);

    return () => clearInterval(interval);
  }, []);

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

        const orderType =
          order.order_type || order.type || order.service_type || "dine_in";

        return orderType === activeType;
      })
      .sort((a, b) => {
        const aTime = new Date(a.created_at || a.createdAt || a.date).getTime();
        const bTime = new Date(b.created_at || b.createdAt || b.date).getTime();

        return aTime - bTime;
      });
  }, [orders, activeType]);

  const pendingOrders = visibleOrders.filter(
    (order) => normalizeStatus(order.status) === ORDER_STATUSES.PLACED
  );

  const preparingOrders = visibleOrders.filter(
    (order) => normalizeStatus(order.status) === ORDER_STATUSES.IN_PROGRESS
  );

  const readyOrders = visibleOrders.filter(
    (order) => normalizeStatus(order.status) === ORDER_STATUSES.READY
  );

  const lateOrders = visibleOrders.filter((order) => {
    const minutes = getMinutesSince(order.created_at || order.createdAt);
    const estimatedTime = Number(order.estimated_time || 15);

    return (
      minutes > estimatedTime &&
      normalizeStatus(order.status) !== ORDER_STATUSES.READY
    );
  });

  const handleUpdateStatus = async (order, nextStatus) => {
    try {
      setUpdatingOrderId(order.id);
      setError("");

      await api.patch(`/orders/${order.id}/`, {
        status: nextStatus,
      });

      setOrders((prev) =>
        prev.map((item) =>
          item.id === order.id
            ? {
                ...item,
                status: nextStatus,
              }
            : item
        )
      );
    } catch (err) {
      console.error("Failed to update order status:", err);
      setError("Failed to update order status.");
    } finally {
      setUpdatingOrderId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-500">
        Loading kitchen orders...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ChefHat
              className="text-orange-500"
              size={28}
            />
            <h1 className="text-2xl font-bold text-gray-800">
              Kitchen Display
            </h1>
          </div>

          <p className="text-sm text-gray-500 mt-1">
            Manage live orders from new to ready.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchOrders}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KitchenStatCard
          title="New Orders"
          value={pendingOrders.length}
          icon={<Clock size={22} />}
          color="yellow"
        />

        <KitchenStatCard
          title="Preparing"
          value={preparingOrders.length}
          icon={<Flame size={22} />}
          color="blue"
        />

        <KitchenStatCard
          title="Ready"
          value={readyOrders.length}
          icon={<PackageCheck size={22} />}
          color="green"
        />

        <KitchenStatCard
          title="Late"
          value={lateOrders.length}
          icon={<AlertTriangle size={22} />}
          color="red"
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {TYPE_FILTERS.map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => setActiveType(type)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${
              activeType === type
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}>
            {formatOrderType(type)}
          </button>
        ))}
      </div>

      {/* Board */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <KitchenColumn
          title="New Orders"
          subtitle="Orders waiting to be started"
          color="yellow"
          orders={pendingOrders}
          emptyText="No new orders"
          actionLabel="Start Preparing"
          actionIcon={<Flame size={16} />}
          onAction={(order) =>
            handleUpdateStatus(order, ORDER_STATUSES.IN_PROGRESS)
          }
          updatingOrderId={updatingOrderId}
        />

        <KitchenColumn
          title="Preparing"
          subtitle="Orders currently being cooked"
          color="blue"
          orders={preparingOrders}
          emptyText="No orders preparing"
          actionLabel="Mark Ready"
          actionIcon={<CheckCircle size={16} />}
          onAction={(order) => handleUpdateStatus(order, ORDER_STATUSES.READY)}
          updatingOrderId={updatingOrderId}
        />

        <KitchenColumn
          title="Ready"
          subtitle="Orders ready for pickup or serving"
          color="green"
          orders={readyOrders}
          emptyText="No ready orders"
          actionLabel="Complete"
          actionIcon={<PackageCheck size={16} />}
          onAction={(order) =>
            handleUpdateStatus(order, ORDER_STATUSES.COMPLETED)
          }
          updatingOrderId={updatingOrderId}
        />
      </div>
    </div>
  );
}

/* ================= Components ================= */

function KitchenStatCard({ title, value, icon, color }) {
  const colors = {
    yellow: "bg-yellow-50 text-yellow-700 border-yellow-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    green: "bg-green-50 text-green-700 border-green-200",
    red: "bg-red-50 text-red-700 border-red-200",
  };

  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium opacity-80">{title}</div>
          <div className="mt-2 text-3xl font-bold">{value}</div>
        </div>

        <div className="rounded-full bg-white p-3 shadow-sm">{icon}</div>
      </div>
    </div>
  );
}

function KitchenColumn({
  title,
  subtitle,
  color,
  orders,
  emptyText,
  actionLabel,
  actionIcon,
  onAction,
  updatingOrderId,
}) {
  const colorClasses = {
    yellow: {
      header: "border-yellow-300 bg-yellow-50 text-yellow-800",
      badge: "bg-yellow-100 text-yellow-700",
    },
    blue: {
      header: "border-blue-300 bg-blue-50 text-blue-800",
      badge: "bg-blue-100 text-blue-700",
    },
    green: {
      header: "border-green-300 bg-green-50 text-green-800",
      badge: "bg-green-100 text-green-700",
    },
  };

  return (
    <section className="rounded-2xl border border-gray-200 bg-gray-50 overflow-hidden">
      <div className={`border-b px-4 py-4 ${colorClasses[color].header}`}>
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold">{title}</h2>
            <p className="text-xs opacity-80">{subtitle}</p>
          </div>

          <span
            className={`rounded-full px-3 py-1 text-sm font-bold ${colorClasses[color].badge}`}>
            {orders.length}
          </span>
        </div>
      </div>

      <div className="space-y-4 p-4 min-h-screen">
        {orders.length === 0 ? (
          <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white text-sm text-gray-400">
            {emptyText}
          </div>
        ) : (
          orders.map((order) => (
            <KitchenOrderCard
              key={order.id}
              order={order}
              actionLabel={actionLabel}
              actionIcon={actionIcon}
              onAction={() => onAction(order)}
              isUpdating={updatingOrderId === order.id}
            />
          ))
        )}
      </div>
    </section>
  );
}

function KitchenOrderCard({
  order,
  actionLabel,
  actionIcon,
  onAction,
  isUpdating,
}) {
  const orderNumber = order.display_id || String(order.id).slice(0, 8);

  const orderType =
    order.order_type || order.type || order.service_type || "dine_in";

  const tableName =
    order.table?.name ||
    order.table_name ||
    order.tableNumber ||
    order.table_id ||
    null;

  const createdAt = order.created_at || order.createdAt || order.date;
  const minutesSince = getMinutesSince(createdAt);
  const estimatedTime = Number(order.estimated_time || 15);

  const isLate =
    minutesSince > estimatedTime &&
    normalizeStatus(order.status) !== ORDER_STATUSES.READY;

  const items = normalizeItems(order);

  return (
    <article
      className={`rounded-xl border bg-white p-4 shadow-sm ${
        isLate ? "border-red-300 ring-2 ring-red-100" : "border-gray-200"
      }`}>
      {/* Card Header */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-gray-900">
            Order #{orderNumber}
          </h3>

          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
            <span className="rounded-full bg-gray-100 px-2 py-1">
              {formatOrderType(orderType)}
            </span>

            {tableName && (
              <span className="rounded-full bg-gray-100 px-2 py-1">
                {tableName}
              </span>
            )}
          </div>
        </div>

        <div className="text-right">
          <div
            className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-bold ${
              isLate ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600"
            }`}>
            <Clock size={13} />
            {minutesSince} min
          </div>

          {isLate && (
            <div className="mt-1 text-xs font-bold text-red-600">LATE</div>
          )}
        </div>
      </div>

      {/* Items */}
      <div className="space-y-3">
        {items.length === 0 ? (
          <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-400">
            No items found.
          </div>
        ) : (
          items.map((item, index) => (
            <div
              key={`${item.name}-${index}`}
              className="rounded-lg bg-gray-50 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="font-semibold text-gray-800">
                  {item.quantity}x {item.name}
                </div>

                {item.station && (
                  <span className="rounded-full bg-orange-100 px-2 py-1 text-xs font-medium text-orange-700">
                    {item.station}
                  </span>
                )}
              </div>

              {item.modifiers?.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-600">
                  {item.modifiers.map((modifier, modifierIndex) => (
                    <li key={modifierIndex}>{modifier}</li>
                  ))}
                </ul>
              )}

              {item.note && (
                <div className="mt-2 rounded bg-white px-2 py-1 text-sm text-gray-600">
                  Note: {item.note}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Order Note */}
      {(order.note || order.notes || order.special_instructions) && (
        <div className="mt-3 rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800">
          {order.note || order.notes || order.special_instructions}
        </div>
      )}

      {/* Total */}
      <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-sm">
        <span className="text-gray-500">Total</span>
        <span className="font-bold text-gray-900">
          ${Number(order.total_price || 0).toFixed(2)}
        </span>
      </div>

      {/* Action */}
      <button
        type="button"
        onClick={onAction}
        disabled={isUpdating}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-gray-900 px-4 py-3 text-sm font-bold text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60">
        {actionIcon}
        {isUpdating ? "Updating..." : actionLabel}
      </button>
    </article>
  );
}

/* ================= Helpers ================= */

function normalizeStatus(status) {
  return String(status || "").toUpperCase();
}

function normalizeItems(order) {
  const rawItems =
    order.items ||
    order.order_items ||
    order.orderItems ||
    order.products ||
    [];

  if (!Array.isArray(rawItems)) return [];

  return rawItems.map((item) => {
    const product = item.product || item.menu_item || item.menuItem || item;

    const name =
      product.name ||
      item.name ||
      item.product_name ||
      item.menu_item_name ||
      "Item";

    const quantity = item.quantity || item.qty || 1;

    const modifiers = normalizeModifiers(item);

    return {
      name,
      quantity,
      modifiers,
      note: item.note || item.notes || item.special_instructions || "",
      station:
        item.station ||
        product.station ||
        product.kitchen_station ||
        item.kitchen_station ||
        "",
    };
  });
}

function normalizeModifiers(item) {
  const raw =
    item.modifiers || item.options || item.extras || item.customizations || [];

  if (Array.isArray(raw)) {
    return raw.map((modifier) => {
      if (typeof modifier === "string") return modifier;
      return modifier.name || modifier.label || String(modifier);
    });
  }

  if (typeof raw === "string") {
    return raw
      .split(",")
      .map((modifier) => modifier.trim())
      .filter(Boolean);
  }

  return [];
}

function getMinutesSince(dateValue) {
  if (!dateValue) return 0;

  const date = new Date(dateValue);

  if (Number.isNaN(date.getTime())) return 0;

  const diff = Date.now() - date.getTime();

  return Math.max(0, Math.floor(diff / 60000));
}

function isRecentKitchenOrder(order) {
  const createdAt = order.created_at || order.createdAt || order.date;

  if (!createdAt) return true;

  const createdTime = new Date(createdAt).getTime();

  if (Number.isNaN(createdTime)) return true;

  const ageHours = (Date.now() - createdTime) / (1000 * 60 * 60);

  // For testing, 72 hours keeps your Aug 2 orders visible on Aug 4.
  // In production, change this to 24.
  return ageHours <= 72;
}

function formatOrderType(type) {
  const labels = {
    all: "All",
    dine_in: "Dine-in",
    dinein: "Dine-in",
    takeout: "Takeout",
    takeaway: "Takeout",
    delivery: "Delivery",
  };

  return labels[type] || String(type || "Dine-in").replace("_", " ");
}
