import React, { useCallback, useEffect, useMemo, useState } from "react";

import api from "../services/api";

import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Loader2,
  Receipt,
  RefreshCw,
  Search,
  Send,
  UtensilsCrossed,
  X,
} from "lucide-react";

const FALLBACK_PAYMENT_METHODS = [
  {
    value: "cash",
    label: "Cash",
  },
  {
    value: "card",
    label: "Card",
  },
  {
    value: "mobile",
    label: "Mobile Pay",
  },
];

const STATUS_CONFIG = {
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
    action: null,
    btnText: null,
    icon: Receipt,
  },

  COMPLETED: {
    color: "bg-emerald-700",
    border: "border-l-emerald-700",
    label: "Completed",
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

  CANCELLED: {
    color: "bg-red-500",
    border: "border-l-red-500",
    label: "Canceled",
    action: null,
    btnText: null,
    icon: AlertCircle,
  },

  DEFAULT: {
    color: "bg-slate-400",
    border: "border-l-slate-400",
    label: "Unknown",
    action: null,
    btnText: null,
    icon: AlertCircle,
  },
};

const formatMoney = (value) => {
  const number = Number(value);

  return Number.isFinite(number) ? number.toFixed(2) : "0.00";
};

const isCanceledRequest = (error) => {
  return (
    error?.code === "ERR_CANCELED" ||
    error?.name === "CanceledError" ||
    error?.name === "AbortError"
  );
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

const getOrderStatus = (order) => {
  return String(order?.status || "UNKNOWN").toUpperCase();
};

const getStatusConfig = (order) => {
  const status = getOrderStatus(order);

  return STATUS_CONFIG[status] || STATUS_CONFIG.DEFAULT;
};

const getOrderTotal = (order) => {
  return order?.total ?? order?.total_price ?? order?.total_amount ?? 0;
};

const getReadableOrderNumber = (order) => {
  if (order?.order_number !== undefined && order?.order_number !== null) {
    const value = String(order.order_number);

    return value.startsWith("ORD-") ? value : `ORD-${value}`;
  }

  const id = String(order?.id || "");

  return `ORD-${id.slice(0, 6).toUpperCase()}`;
};

const getShortOrderId = (order) => {
  const orderNumber = getReadableOrderNumber(order);

  return orderNumber.replace(/^ORD-/i, "");
};

const getTableNumber = (order) => {
  const table = order?.table || null;

  return (
    order?.table_number ??
    order?.table_name ??
    table?.display_number ??
    table?.table_number ??
    table?.number ??
    table?.name ??
    null
  );
};

const getTableStatus = (order) => {
  const table = order?.table || null;

  return String(
    order?.table_status ??
      order?.table_current_status ??
      table?.current_status ??
      table?.status ??
      ""
  ).toUpperCase();
};

const getCustomerOrTable = (order) => {
  const tableNumber = getTableNumber(order);

  if (tableNumber !== null) {
    return `Table ${tableNumber}`;
  }

  if (order?.customer_name) {
    return order.customer_name;
  }

  if (order?.customer?.name) {
    return order.customer.name;
  }

  if (
    String(order?.order_type || "")
      .toUpperCase()
      .includes("TAKE")
  ) {
    return "Take-Out";
  }

  return "Takeaway";
};

const getErrorMessage = (error, fallback) => {
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

  if (data?.payment_method) {
    if (Array.isArray(data.payment_method)) {
      return data.payment_method.join(" ");
    }

    return String(data.payment_method);
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

const normalizePaymentStatus = (value) => {
  return String(value || "")
    .trim()
    .toUpperCase();
};

const isOrderPaid = (order) => {
  return normalizePaymentStatus(order?.payment_status) === "PAID";
};

const isOrderRefunded = (order) => {
  return normalizePaymentStatus(order?.payment_status) === "REFUNDED";
};

const isOrderCanceled = (order) => {
  const status = getOrderStatus(order);

  return status === "CANCELED" || status === "CANCELLED";
};

const isOrderCompleted = (order) => {
  return getOrderStatus(order) === "COMPLETED";
};

const canSettleOrder = (order) => {
  if (isOrderPaid(order)) {
    return false;
  }

  if (isOrderRefunded(order)) {
    return false;
  }

  if (isOrderCanceled(order)) {
    return false;
  }

  if (isOrderCompleted(order)) {
    return false;
  }

  return true;
};

const normalizePaymentMethod = (method) => {
  if (!method) {
    return null;
  }

  if (typeof method !== "object") {
    return String(method);
  }

  if (method.id !== undefined && method.id !== null) {
    return method.id;
  }

  return method.value ?? method.slug ?? method.name ?? null;
};

const getPaymentMethodLabel = (method) => {
  if (!method) {
    return "Unknown";
  }

  if (typeof method === "object") {
    return method.label ?? method.name ?? method.slug ?? "Unknown";
  }

  const normalized = String(method)
    .toLowerCase()
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .trim();

  if (normalized.includes("cash")) {
    return "Cash";
  }

  if (
    normalized.includes("card") ||
    normalized.includes("credit") ||
    normalized.includes("debit")
  ) {
    return "Card";
  }

  if (
    normalized.includes("mobile") ||
    normalized.includes("momo") ||
    normalized.includes("mtn")
  ) {
    return "Mobile Pay";
  }

  return String(method);
};

const normalizePaymentMethods = (response) => {
  const methods = getResponseList(response);

  const activeMethods = methods
    .filter((method) => method?.is_active !== false && method?.active !== false)
    .map((method) => {
      const value = normalizePaymentMethod(method);

      return {
        value,
        label: getPaymentMethodLabel(method),
      };
    })
    .filter((method) => method.value);

  return activeMethods.length > 0 ? activeMethods : FALLBACK_PAYMENT_METHODS;
};

const getItemUnitPrice = (item) => {
  return Number(
    item?.final_price ??
      item?.price ??
      item?.product?.price ??
      item?.product?.base_price ??
      0
  );
};

const getItemTotal = (item) => {
  if (item?.total_price !== undefined && item?.total_price !== null) {
    return Number(item.total_price);
  }

  return getItemUnitPrice(item) * Number(item?.quantity || 0);
};

export default function Orders() {
  const [orders, setOrders] = useState([]);

  const [loading, setLoading] = useState(true);

  const [isRefreshing, setIsRefreshing] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");

  const [selectedPaymentMethods, setSelectedPaymentMethods] = useState({});

  const [paymentMethods, setPaymentMethods] = useState(
    FALLBACK_PAYMENT_METHODS
  );

  const [processingOrders, setProcessingOrders] = useState({});

  const [error, setError] = useState(null);

  const fetchOrders = useCallback(async (signal) => {
    setIsRefreshing(true);

    try {
      const response = await api.get("/orders/", {
        signal,
        params: {
          _: Date.now(),
        },
      });

      const data = getResponseList(response);

      const sortedOrders = [...data].sort((first, second) => {
        const firstDate = new Date(first.created_at || 0).getTime();

        const secondDate = new Date(second.created_at || 0).getTime();

        return secondDate - firstDate;
      });

      setOrders(sortedOrders);
      setError(null);
    } catch (requestError) {
      if (isCanceledRequest(requestError)) {
        return;
      }

      console.error("Fetch orders failed:", requestError);

      setError(getErrorMessage(requestError, "Failed to load orders."));
    } finally {
      if (!signal || !signal.aborted) {
        setLoading(false);
        setIsRefreshing(false);
      }
    }
  }, []);

  const fetchPaymentMethods = useCallback(async (signal) => {
    try {
      const response = await api.get("/payment-methods/", {
        signal,
        params: {
          _: Date.now(),
        },
      });

      setPaymentMethods(normalizePaymentMethods(response));
    } catch (requestError) {
      if (isCanceledRequest(requestError)) {
        return;
      }

      console.error("Fetch payment methods failed:", requestError);

      setPaymentMethods(FALLBACK_PAYMENT_METHODS);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchOrders(controller.signal);

    fetchPaymentMethods(controller.signal);

    const interval = setInterval(() => {
      fetchOrders();
    }, 15000);

    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, [fetchOrders, fetchPaymentMethods]);

  const updateSelectedPaymentMethod = (orderId, method) => {
    setSelectedPaymentMethods((current) => ({
      ...current,
      [orderId]: method,
    }));
  };

  const handlePrint = async (orderId, type) => {
    try {
      const action = type === "kitchen" ? "print-kitchen" : "print-receipt";

      const response = await api.get(`/orders/${orderId}/${action}/`, {
        responseType: "text",
        headers: {
          Accept: "text/html",
        },
      });

      const printWindow = window.open("", "_blank");

      if (!printWindow) {
        window.alert("Please allow popups to print.");
        return;
      }

      printWindow.document.open();
      printWindow.document.write(response.data);
      printWindow.document.close();
      printWindow.focus();
      printWindow.print();
    } catch (requestError) {
      console.error("Print error:", requestError);

      window.alert(
        getErrorMessage(requestError, "Failed to load print document.")
      );
    }
  };

  const triggerAction = async (order, actionName) => {
    const orderId = order?.id;

    if (!orderId) {
      window.alert("This order does not have a valid ID.");
      return;
    }

    const currentStatus = String(order?.status || "").toUpperCase();

    const blockedStatuses = [
      "IN_PROGRESS",
      "READY",
      "SERVED",
      "COMPLETED",
      "CANCELED",
      "CANCELLED",
    ];

    if (
      actionName === "send_to_kitchen" &&
      blockedStatuses.includes(currentStatus)
    ) {
      window.alert(
        `This order is already ${currentStatus
          .toLowerCase()
          .replaceAll("_", " ")}.`
      );

      return;
    }

    if (
      isOrderPaid(order) ||
      isOrderRefunded(order) ||
      isOrderCanceled(order) ||
      isOrderCompleted(order)
    ) {
      window.alert("This order cannot be changed.");

      return;
    }

    setProcessingOrders((current) => ({
      ...current,
      [orderId]: true,
    }));

    try {
      const response = await api.post(`/orders/${orderId}/${actionName}/`, {});

      console.log(`${actionName} success:`, response.data);

      await fetchOrders();
    } catch (requestError) {
      console.error(
        `${actionName} failed:`,
        requestError?.response?.status,
        requestError?.response?.data || requestError
      );

      window.alert(
        getErrorMessage(requestError, `Failed to perform ${actionName}.`)
      );
    } finally {
      setProcessingOrders((current) => {
        const next = {
          ...current,
        };

        delete next[orderId];

        return next;
      });
    }
  };
  
  const markOrderPaid = async (order) => {
    const orderId = order?.id;

    if (!orderId) {
      window.alert("This order does not have a valid ID.");
      return;
    }

    if (!canSettleOrder(order)) {
      window.alert("This order cannot be paid.");
      return;
    }

    const selectedMethod = selectedPaymentMethods[orderId];

    if (!selectedMethod) {
      window.alert("Please select a payment method.");
      return;
    }

    const total = Number(getOrderTotal(order));

    if (!Number.isFinite(total) || total <= 0) {
      window.alert("This order has a zero total and cannot be paid.");
      return;
    }

    setProcessingOrders((current) => ({
      ...current,
      [orderId]: true,
    }));

    try {
      const response = await api.post(`/orders/${orderId}/mark_paid/`, {
        payment_method: selectedMethod,
      });

      console.log("mark_paid success:", response.data);

      setSelectedPaymentMethods((current) => {
        const next = {
          ...current,
        };

        delete next[orderId];

        return next;
      });

      await fetchOrders();
    } catch (requestError) {
      console.error(
        "mark_paid failed:",
        requestError?.response?.data || requestError
      );

      window.alert(
        getErrorMessage(requestError, "Failed to mark order as paid.")
      );
    } finally {
      setProcessingOrders((current) => {
        const next = {
          ...current,
        };

        delete next[orderId];

        return next;
      });
    }
  };

  const filteredOrders = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    if (!query) {
      return orders;
    }

    return orders.filter((order) => {
      const orderNumber = getReadableOrderNumber(order).toLowerCase();

      const shortId = getShortOrderId(order).toLowerCase();

      const tableName = getCustomerOrTable(order).toLowerCase();

      const customerName = String(
        order?.customer_name || order?.customer?.name || ""
      ).toLowerCase();

      const orderType = String(order?.order_type || "").toLowerCase();

      return (
        orderNumber.includes(query) ||
        shortId.includes(query) ||
        tableName.includes(query) ||
        customerName.includes(query) ||
        orderType.includes(query)
      );
    });
  }, [orders, searchQuery]);

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
          <div className="relative flex-1 md:w-64">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              size={18}
            />

            <input
              type="text"
              placeholder="Search order or table..."
              value={searchQuery}
              onChange={(event) => {
                setSearchQuery(event.target.value);
              }}
              className="w-full pl-10 pr-10 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all"
            />

            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <X size={16} />
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={() => {
              fetchOrders();
            }}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-50 transition-all shadow-sm active:scale-95 disabled:opacity-50">
            <RefreshCw
              className={isRefreshing ? "animate-spin" : ""}
              size={16}
            />

            {isRefreshing ? "..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4">
          <AlertCircle size={20} />

          <p className="text-sm font-semibold">{error}</p>
        </div>
      )}

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
            const config = getStatusConfig(order);

            const Icon = config.icon;

            const orderId = String(order.id);

            const selectedMethod = selectedPaymentMethods[orderId] || "";

            const isProcessing = Boolean(processingOrders[orderId]);

            const orderStatus = getOrderStatus(order);

            const tableNumber = getTableNumber(order);

            const tableStatus = getTableStatus(order);

            const orderIsPaid = isOrderPaid(order);

            const orderIsRefunded = isOrderRefunded(order);

            const orderIsCanceled = isOrderCanceled(order);

            const orderIsCompleted = isOrderCompleted(order);

            const canPay = canSettleOrder(order);

            const hasKitchenAction =
              Boolean(config.action) &&
              !orderIsPaid &&
              !orderIsRefunded &&
              !orderIsCanceled &&
              !orderIsCompleted;

            const items = Array.isArray(order.items) ? order.items : [];

            return (
              <div
                key={orderId}
                className={`bg-white border border-slate-200 border-l-[6px] ${config.border} rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all`}>
                <div className="p-5">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex gap-4">
                      <div
                        className={`p-3 rounded-2xl text-white ${config.color} shadow-lg`}>
                        <Icon size={24} />
                      </div>

                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h2 className="text-xl font-black text-slate-900">
                            #{getShortOrderId(order)}
                          </h2>

                          <span
                            className={`text-[10px] font-black text-white px-2.5 py-1 rounded-full uppercase tracking-wider ${config.color}`}>
                            {config.label}
                          </span>

                          {orderIsPaid && (
                            <span className="text-[10px] font-black text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-full uppercase tracking-wider">
                              Paid
                            </span>
                          )}

                          {orderIsRefunded && (
                            <span className="text-[10px] font-black text-red-700 bg-red-100 px-2.5 py-1 rounded-full uppercase tracking-wider">
                              Refunded
                            </span>
                          )}
                        </div>

                        <p className="text-sm text-slate-500 font-bold uppercase mt-0.5">
                          {getCustomerOrTable(order)}
                        </p>

                        {tableNumber !== null && (
                          <p className="text-[11px] text-slate-400 font-bold uppercase mt-1">
                            Table status: {tableStatus || "UNKNOWN"}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-2xl font-black text-slate-900">
                        ${formatMoney(getOrderTotal(order))}
                      </p>

                      <div className="flex items-center justify-end gap-1 text-slate-400 font-bold text-[11px]">
                        <Clock size={12} />

                        {order.created_at
                          ? new Date(order.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "—"}
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 space-y-2">
                    {items.length > 0 ? (
                      items.map((item) => (
                        <div
                          key={String(item.id)}
                          className="flex justify-between items-center text-sm">
                          <div className="flex items-center gap-3">
                            <span className="w-6 h-6 bg-slate-200 text-slate-600 rounded-md flex items-center justify-center text-[10px] font-black">
                              {item.quantity}
                            </span>

                            <span className="text-slate-800 font-bold">
                              {item.product_name ||
                                item.product?.name ||
                                "Unnamed product"}
                            </span>
                          </div>

                          <span className="text-slate-500 font-mono font-bold">
                            ${formatMoney(getItemTotal(item))}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-slate-400 italic">
                        No items added yet.
                      </p>
                    )}
                  </div>

                  <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 pt-5 mt-2 border-t border-slate-50">
                    <div className="flex gap-2 flex-wrap">
                      <button
                        type="button"
                        onClick={() => {
                          handlePrint(orderId, "receipt");
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-black text-slate-600 transition-colors">
                        <Receipt size={14} />
                        RECEIPT
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          handlePrint(orderId, "kitchen");
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-black text-slate-600 transition-colors">
                        <UtensilsCrossed size={14} />
                        KITCHEN
                      </button>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                      {hasKitchenAction && (
                        <button
                          type="button"
                          disabled={isProcessing}
                          onClick={() => {
                            triggerAction(order, config.action);
                          }}
                          className={`flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-black text-sm text-white shadow-lg transition-all active:scale-95 ${config.color} hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed`}>
                          {isProcessing ? (
                            <Loader2
                              size={18}
                              className="animate-spin"
                            />
                          ) : (
                            <>
                              {config.btnText}
                              <ChevronRight size={18} />
                            </>
                          )}
                        </button>
                      )}

                      {canPay && (
                        <>
                          <select
                            value={selectedMethod}
                            onChange={(event) => {
                              updateSelectedPaymentMethod(
                                orderId,
                                event.target.value
                              );
                            }}
                            disabled={isProcessing}
                            className="px-4 py-3 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-black text-slate-600 transition-colors disabled:opacity-50">
                            <option value="">Select Payment Method</option>

                            {paymentMethods.map((method) => (
                              <option
                                key={String(method.value)}
                                value={method.value}>
                                {method.label}
                              </option>
                            ))}
                          </select>

                          <button
                            type="button"
                            disabled={isProcessing || !selectedMethod}
                            onClick={() => {
                              markOrderPaid(order);
                            }}
                            className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-black text-sm text-white bg-green-600 hover:bg-green-700 shadow-lg transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed">
                            {isProcessing ? (
                              <Loader2
                                size={18}
                                className="animate-spin"
                              />
                            ) : (
                              <>
                                Mark Paid
                                <CheckCircle2 size={18} />
                              </>
                            )}
                          </button>
                        </>
                      )}

                      {orderIsPaid && (
                        <p className="text-sm text-emerald-600 font-bold">
                          Paid
                        </p>
                      )}

                      {orderIsRefunded && (
                        <p className="text-sm text-red-600 font-bold">
                          Refunded
                        </p>
                      )}

                      {orderIsCanceled && (
                        <p className="text-sm text-red-600 font-bold">
                          Canceled
                        </p>
                      )}

                      {orderIsCompleted && (
                        <p className="text-sm text-emerald-700 font-bold">
                          Completed
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
