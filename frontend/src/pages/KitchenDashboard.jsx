import { useCallback, useEffect, useMemo, useState } from "react";

import {
  AlertTriangle,
  CheckCircle,
  ChefHat,
  Clock,
  Flame,
  PackageCheck,
  RefreshCw,
  Search,
  UtensilsCrossed,
  X,
} from "lucide-react";

import api from "../services/api";

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

const getErrorMessage = (error, fallback = "Something went wrong.") => {
  const data = error?.response?.data;

  if (typeof data === "string") {
    return data;
  }

  if (data?.detail) {
    return data.detail;
  }

  if (data?.error) {
    return data.error;
  }

  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([key, value]) => {
        const message = Array.isArray(value) ? value.join(" ") : String(value);

        return `${key}: ${message}`;
      })
      .join(" | ");
  }

  return error?.message || fallback;
};

const getResponseList = (response) => {
  const payload = response?.data;

  if (Array.isArray(payload)) {
    return payload;
  }

  if (Array.isArray(payload?.results)) {
    return payload.results;
  }

  return [];
};

const normalizeStatus = (status) => {
  return String(status || "")
    .trim()
    .toUpperCase();
};

const normalizeOrderType = (orderType) => {
  const value = String(orderType || "DINE_IN")
    .trim()
    .toUpperCase()
    .replaceAll("-", "_");

  if (value === "TAKEOUT" || value === "TAKE_OUT" || value === "TAKE_AWAY") {
    return "takeout";
  }

  if (value === "DELIVERY") {
    return "delivery";
  }

  return "dine_in";
};

const formatOrderId = (order) => {
  if (order?.display_id) {
    return String(order.display_id);
  }

  if (order?.order_number !== undefined && order?.order_number !== null) {
    return String(order.order_number);
  }

  const id = String(order?.id || "");

  return id.split("-").pop().slice(-4).toUpperCase();
};

const getTableOrCustomer = (order) => {
  if (order?.table_name) {
    return `Table ${order.table_name}`;
  }

  if (order?.table?.table_number) {
    return `Table ${order.table.table_number}`;
  }

  return order?.customer_name || order?.customer?.name || "Takeaway";
};

const normalizeItems = (order) => {
  const rawItems = Array.isArray(order?.items)
    ? order.items
    : Array.isArray(order?.order_items)
    ? order.order_items
    : [];

  return rawItems.map((item, index) => {
    const modifiers = Array.isArray(item?.modifiers)
      ? item.modifiers.map((modifier) => {
          if (typeof modifier === "string") {
            return modifier;
          }

          return (
            modifier?.name || modifier?.label || String(modifier?.id || "")
          );
        })
      : [];

    return {
      key:
        item?.id ||
        `${order?.id}-${item?.product_id || item?.product}-${index}`,
      productName:
        item?.product_name ||
        item?.product?.name ||
        item?.name ||
        "Unknown Item",
      quantity: Number(item?.quantity || 1),
      modifiers,
      note: item?.note || item?.notes || "",
    };
  });
};

const getMinutesSince = (dateValue) => {
  if (!dateValue) {
    return 0;
  }

  const timestamp = new Date(dateValue).getTime();

  if (Number.isNaN(timestamp)) {
    return 0;
  }

  const difference = Date.now() - timestamp;

  return Math.max(0, Math.floor(difference / 60000));
};

const isRecentKitchenOrder = (order) => {
  if (!order?.created_at) {
    return false;
  }

  const createdAt = new Date(order.created_at).getTime();

  if (Number.isNaN(createdAt)) {
    return false;
  }

  const ageHours = (Date.now() - createdAt) / (1000 * 60 * 60);

  return ageHours <= 24;
};

const STATUS_ACTIONS = {
  [ORDER_STATUSES.PLACED]: {
    endpoint: "start_preparing",
    label: "START COOKING",
    icon: Flame,
  },

  [ORDER_STATUSES.IN_PROGRESS]: {
    endpoint: "mark_ready",
    label: "MARK AS READY",
    icon: CheckCircle,
  },

  [ORDER_STATUSES.READY]: {
    endpoint: "mark_served",
    label: "MARK AS SERVED",
    icon: PackageCheck,
  },
};

const normalizeOrder = (order) => {
  return {
    ...order,
    id: order?.id,
    status: normalizeStatus(order?.status),
    payment_status: String(order?.payment_status || "").toUpperCase(),
    order_type: normalizeOrderType(order?.order_type),
    items: Array.isArray(order?.items)
      ? order.items
      : Array.isArray(order?.order_items)
      ? order.order_items
      : [],
  };
};

export default function KitchenDashboard() {
  const [orders, setOrders] = useState([]);
  const [activeType, setActiveType] = useState("all");
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [updatingOrderId, setUpdatingOrderId] = useState(null);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [now, setNow] = useState(Date.now());

  const fetchOrders = useCallback(async (isManual = false, signal) => {
    if (isManual) {
      setIsRefreshing(true);
    }

    try {
      setError("");

      const response = await api.get("/orders/", {
        signal,
        params: {
          _: Date.now(),
        },
      });

      const data = getResponseList(response).map(normalizeOrder);

      setOrders(data);
    } catch (requestError) {
      if (
        requestError?.code === "ERR_CANCELED" ||
        requestError?.name === "CanceledError"
      ) {
        return;
      }

      console.error("Kitchen fetch error:", requestError);

      setError(getErrorMessage(requestError, "Failed to load kitchen orders."));
    } finally {
      if (!signal || !signal.aborted) {
        setLoading(false);

        if (isManual) {
          setIsRefreshing(false);
        }
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchOrders(false, controller.signal);

    const pollInterval = setInterval(() => {
      if (!controller.signal.aborted) {
        fetchOrders(false, controller.signal);
      }
    }, 15000);

    const clockInterval = setInterval(() => {
      setNow(Date.now());
    }, 60000);

    return () => {
      controller.abort();
      clearInterval(pollInterval);
      clearInterval(clockInterval);
    };
  }, [fetchOrders]);

  const handlePrintKitchen = async (orderId) => {
    try {
      const response = await api.get(`/orders/${orderId}/print-kitchen/`, {
        responseType: "text",
        headers: {
          Accept: "text/html",
        },
      });

      const printWindow = window.open("", "_blank");

      if (!printWindow) {
        window.alert("Please allow popups for this site to print.");
        return;
      }

      printWindow.document.open();
      printWindow.document.write(response.data);
      printWindow.document.close();
      printWindow.focus();
    } catch (requestError) {
      console.error("Kitchen print error:", requestError);

      window.alert(
        getErrorMessage(requestError, "Failed to generate kitchen ticket.")
      );
    }
  };
const handleUpdateStatus = async (order, nextStatus) => {
  const orderId = order?.id;

  if (!orderId) {
    setError("The order does not have a valid ID.");
    return;
  }

  const currentStatus = normalizeStatus(order?.status);

  const action = STATUS_ACTIONS[nextStatus];

  if (!action) {
    setError(`Unsupported kitchen status: ${nextStatus}`);
    return;
  }

  if (currentStatus === ORDER_STATUSES.COMPLETED) {
    setError("Completed orders cannot be changed.");
    return;
  }

  setUpdatingOrderId(orderId);
  setError("");

  try {
    const response = await api.post(`/orders/${orderId}/${action.endpoint}/`);

    const updatedOrder = response.data?.order || response.data;

    setOrders((currentOrders) =>
      currentOrders.map((currentOrder) => {
        if (String(currentOrder.id) !== String(orderId)) {
          return currentOrder;
        }

        return normalizeOrder({
          ...currentOrder,
          ...updatedOrder,
          status: updatedOrder?.status || nextStatus,
        });
      })
    );

    await fetchOrders();
  } catch (requestError) {
    console.error(
      "Kitchen status update failed:",
      requestError?.response?.data || requestError
    );

    setError(getErrorMessage(requestError, "Failed to update order status."));
  } finally {
    setUpdatingOrderId(null);
  }
};

  const visibleOrders = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

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
        const typeMatches =
          activeType === "all" ||
          normalizeOrderType(order.order_type) === activeType;

        if (!typeMatches) {
          return false;
        }

        if (!query) {
          return true;
        }

        const orderId = formatOrderId(order).toLowerCase();

        const tableName = getTableOrCustomer(order).toLowerCase();

        const customerName = String(
          order?.customer_name || order?.customer?.name || ""
        ).toLowerCase();

        return (
          orderId.includes(query) ||
          tableName.includes(query) ||
          customerName.includes(query)
        );
      })
      .sort((first, second) => {
        const firstTime = new Date(first.created_at).getTime();

        const secondTime = new Date(second.created_at).getTime();

        return firstTime - secondTime;
      });
  }, [orders, activeType, searchQuery, now]);

  const pendingOrders = visibleOrders.filter(
    (order) => normalizeStatus(order.status) === ORDER_STATUSES.PLACED
  );

  const preparingOrders = visibleOrders.filter(
    (order) => normalizeStatus(order.status) === ORDER_STATUSES.IN_PROGRESS
  );

  const readyOrders = visibleOrders.filter(
    (order) => normalizeStatus(order.status) === ORDER_STATUSES.READY
  );

  const lateOrdersCount = visibleOrders.filter((order) => {
    return (
      getMinutesSince(order.created_at) > 15 &&
      normalizeStatus(order.status) !== ORDER_STATUSES.READY
    );
  }).length;

  if (loading && orders.length === 0) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-500 animate-pulse font-black tracking-widest">
        INITIALIZING KITCHEN DISPLAY...
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto p-4">
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
          <div className="relative w-full md:w-80">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
              size={18}
            />

            <input
              type="text"
              placeholder="Search Order ID or Table..."
              value={searchQuery}
              onChange={(event) => {
                setSearchQuery(event.target.value);
              }}
              className="w-full pl-12 pr-10 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-orange-500/20 transition-all"
            />

            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                }}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <X size={16} />
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={() => {
              fetchOrders(true);
            }}
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

      {error && (
        <div className="bg-red-50 border border-red-100 text-red-700 rounded-2xl p-4 font-bold">
          {error}
        </div>
      )}

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

      <div className="flex flex-wrap gap-2 bg-slate-100 p-1.5 rounded-2xl w-fit">
        {TYPE_FILTERS.map((type) => (
          <button
            type="button"
            key={type}
            onClick={() => {
              setActiveType(type);
            }}
            className={`rounded-xl px-6 py-2 text-[10px] font-black uppercase tracking-[0.2em] transition-all ${
              activeType === type
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}>
            {type.replaceAll("_", " ")}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <KitchenColumn
          title="NEW ORDERS"
          color="yellow"
          orders={pendingOrders}
          actionLabel="START COOKING"
          actionIcon={<Flame size={18} />}
          onAction={(order) => {
            handleUpdateStatus(order, ORDER_STATUSES.IN_PROGRESS);
          }}
          onPrint={handlePrintKitchen}
          updatingOrderId={updatingOrderId}
          formatId={formatOrderId}
        />

        <KitchenColumn
          title="PREPARING"
          color="blue"
          orders={preparingOrders}
          actionLabel="MARK AS READY"
          actionIcon={<CheckCircle size={18} />}
          onAction={(order) => {
            handleUpdateStatus(order, ORDER_STATUSES.READY);
          }}
          onPrint={handlePrintKitchen}
          updatingOrderId={updatingOrderId}
          formatId={formatOrderId}
        />

        <KitchenColumn
          title="READY TO SERVE"
          color="green"
          orders={readyOrders}
          actionLabel="MARK AS SERVED"
          actionIcon={<PackageCheck size={18} />}
          onAction={(order) => {
            handleUpdateStatus(order, ORDER_STATUSES.SERVED);
          }}
          onPrint={handlePrintKitchen}
          updatingOrderId={updatingOrderId}
          formatId={formatOrderId}
        />
      </div>
    </div>
  );
}

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
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">
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
            key={String(order.id)}
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
            {getTableOrCustomer(order)}
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
        {items.length === 0 ? (
          <p className="text-sm text-slate-400 italic">No items found.</p>
        ) : (
          items.map((item) => (
            <div
              key={String(item.key)}
              className="flex gap-3">
              <span className="bg-slate-900 text-white w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-black shrink-0">
                {item.quantity}
              </span>

              <div>
                <p className="text-sm font-black text-slate-800 uppercase">
                  {item.productName}
                </p>

                {item.modifiers.map((modifier, index) => (
                  <p
                    key={`${item.key}-modifier-${index}`}
                    className="text-[10px] text-slate-500 font-bold">
                    • {modifier}
                  </p>
                ))}

                {item.note && (
                  <p className="text-[10px] text-orange-600 font-bold mt-1 italic">
                    Note: {item.note}
                  </p>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="flex gap-2 mb-3">
        <button
          type="button"
          onClick={() => {
            onPrint(order.id);
          }}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-[10px] font-black text-slate-600 transition-colors">
          <UtensilsCrossed size={14} />
          TICKET
        </button>
      </div>

      <button
        type="button"
        onClick={() => {
          onAction(order);
        }}
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
    </div>
  );
}
