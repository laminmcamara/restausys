import React, { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { API_BASE } from "../config";
import PrintPreviewModal from "../components/printing/PrintPreviewModal";

export default function Orders() {
  const { accessToken } = useAuth();

  const [orders, setOrders] = useState([]);

  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [printOrder, setPrintOrder] = useState(null);
  const [printType, setPrintType] = useState("receipt");

  useEffect(() => {
    if (accessToken) {
      fetchOrders();

      const interval = setInterval(fetchOrders, 10000);

      return () => clearInterval(interval);
    }
  }, [accessToken]);

  const authFetch = async (url, options = {}) => {
    return fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });
  };

  const formatMoney = (value) =>
    value !== undefined && value !== null && !Number.isNaN(Number(value))
      ? Number(value).toFixed(2)
      : "0.00";

  const getOrderItems = (order) => {
    return order?.items || order?.order_items || [];
  };

  const getUnitPrice = (item) => {
    const quantity = Number(item.quantity || 1);

    const explicitUnitPrice =
      item.unit_price ??
      item.unitPrice ??
      item.product?.base_price ??
      item.product?.price ??
      item.menu_item?.base_price ??
      item.menu_item?.price ??
      item.product_base_price ??
      item.menu_item_base_price ??
      item.base_price ??
      item.price;

    if (explicitUnitPrice !== undefined && explicitUnitPrice !== null) {
      return Number(explicitUnitPrice);
    }

    if (item.final_price !== undefined && item.final_price !== null) {
      return Number(item.final_price) / quantity;
    }

    return 0;
  };

  const getLineTotal = (item) => {
    const quantity = Number(item.quantity || 1);

    const explicitLineTotal =
      item.line_total ??
      item.lineTotal ??
      item.total_price ??
      item.totalPrice ??
      item.total;

    if (explicitLineTotal !== undefined && explicitLineTotal !== null) {
      return Number(explicitLineTotal);
    }

    return getUnitPrice(item) * quantity;
  };

  const getOrderTotal = (order) => {
    const items = getOrderItems(order);

    return items.reduce((sum, item) => {
      return sum + getLineTotal(item);
    }, 0);
  };

  const getSafeOrderForPrint = (order) => {
    const items = getOrderItems(order);

    const safeItems = items.map((item) => {
      const unitPrice = getUnitPrice(item);
      const lineTotal = getLineTotal(item);

      return {
        ...item,
        unit_price: unitPrice,
        unitPrice,
        line_total: lineTotal,
        lineTotal,
        final_price: lineTotal,
        total_price: lineTotal,
        total: lineTotal,
      };
    });

    const calculatedTotal = safeItems.reduce((sum, item) => {
      return sum + Number(item.line_total || 0);
    }, 0);

    return {
      ...order,
      items: safeItems,
      order_items: safeItems,
      total_price: calculatedTotal,
      total: calculatedTotal,
    };
  };

  const fetchOrders = async () => {
    try {
      const res = await authFetch(`${API_BASE}/api/v1/orders/`, {
        method: "GET",
      });

      if (!res) return;

      if (!res.ok) {
        console.error("Failed to fetch orders:", res.status);
        return;
      }

      const data = await res.json();

      console.log("ORDERS ENDPOINT RAW DATA:", data);
      console.log(
        "FIRST ORDER ITEMS:",
        Array.isArray(data)
          ? data[0]?.items || data[0]?.order_items
          : data.results?.[0]?.items || data.results?.[0]?.order_items
      );
      console.log(
        "FIRST ORDER TOTAL FROM BACKEND:",
        Array.isArray(data)
          ? data[0]?.total_price || data[0]?.total
          : data.results?.[0]?.total_price || data.results?.[0]?.total
      );

      const normalizedOrders = Array.isArray(data) ? data : data.results || [];

      setOrders(normalizedOrders);
    } catch (err) {
      console.error("Fetch failed:", err);
    }
  };
  
  const updateStatus = async (orderId, newStatus) => {
    try {
      const response = await authFetch(
        `${API_BASE}/api/v1/orders/${orderId}/`,
        {
          method: "PATCH",
          body: JSON.stringify({ status: newStatus }),
        }
      );

      if (response && response.ok) {
        fetchOrders();
      } else if (response) {
        const error = await response.json().catch(() => null);
        console.log("Status update error:", error || response.status);
      }
    } catch (err) {
      console.error("Status update failed:", err);
    }
  };

  const openPrintPreview = (order, type) => {
    const safeOrder = getSafeOrderForPrint(order);

    setPrintOrder(safeOrder);
    setPrintType(type);
    setPrintModalOpen(true);
  };

  const statusColor = (status) => {
    switch (status) {
      case "DRAFT":
        return "bg-gray-400";
      case "PLACED":
        return "bg-blue-500";
      case "IN_PROGRESS":
        return "bg-yellow-500";
      case "READY":
        return "bg-green-500";
      case "SERVED":
        return "bg-purple-500";
      case "COMPLETED":
        return "bg-black";
      case "CANCELED":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const allowedTransitions = {
    DRAFT: ["PLACED", "CANCELED"],
    PLACED: ["IN_PROGRESS", "CANCELED"],
    IN_PROGRESS: ["READY", "CANCELED"],
    READY: ["SERVED", "CANCELED"],
    SERVED: ["COMPLETED"],
    COMPLETED: [],
    CANCELED: [],
  };

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Orders Dashboard</h1>

      {orders.length === 0 && (
        <div className="text-gray-500">No orders yet.</div>
      )}

      <div className="space-y-4">
        {orders.map((order) => {
          const orderItems = getOrderItems(order);
          const calculatedTotal = getOrderTotal(order);

          return (
            <div
              key={order.id}
              className="border rounded-lg p-5 shadow-sm space-y-3"
            >
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="font-semibold">
                    Order #{order.display_id || order.id}
                  </h2>

                  <p className="text-sm text-gray-500">
                    {order.table_name
                      ? `Table ${order.table_name}`
                      : order.customer_name
                      ? `Customer: ${order.customer_name}`
                      : "Pickup"}
                  </p>
                </div>

                <span
                  className={`text-white px-3 py-1 rounded text-sm ${statusColor(
                    order.status
                  )}`}
                >
                  {String(order.status || "").replace("_", " ")}
                </span>
              </div>

              <div className="space-y-1 text-sm">
                {orderItems.map((item) => {
                  const itemName =
                    item.product?.name ||
                    item.menu_item?.name ||
                    item.product_name ||
                    item.menu_item_name ||
                    item.name ||
                    "Item";

                  return (
                    <div
                      key={item.id}
                      className="flex justify-between gap-4"
                    >
                      <span>
                        {item.quantity} × {itemName}
                      </span>

                      <span className="text-gray-600">
                        ${formatMoney(getLineTotal(item))}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="flex justify-between items-center gap-4 flex-wrap">
                <div className="font-semibold">
                  Total: ${formatMoney(calculatedTotal)}
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    type="button"
                    onClick={() => openPrintPreview(order, "bill")}
                    className="border px-3 py-2 rounded text-sm hover:bg-gray-100"
                  >
                    Bill
                  </button>

                  <button
                    type="button"
                    onClick={() => openPrintPreview(order, "receipt")}
                    className="border px-3 py-2 rounded text-sm hover:bg-gray-100"
                  >
                    Receipt
                  </button>

                  <button
                    type="button"
                    onClick={() => openPrintPreview(order, "kitchen")}
                    className="border px-3 py-2 rounded text-sm hover:bg-gray-100"
                  >
                    Kitchen Ticket
                  </button>

                  <button
                    type="button"
                    onClick={() => openPrintPreview(order, "bar")}
                    className="border px-3 py-2 rounded text-sm hover:bg-gray-100"
                  >
                    Bar Ticket
                  </button>

                  {allowedTransitions[order.status]?.length > 0 && (
                    <select
                      onChange={(e) => updateStatus(order.id, e.target.value)}
                      defaultValue=""
                      className="border p-2 rounded text-sm"
                    >
                      <option value="" disabled>
                        Change Status
                      </option>

                      {allowedTransitions[order.status].map((status) => (
                        <option key={status} value={status}>
                          {status.replace("_", " ")}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
            </div>
          );
        })}
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