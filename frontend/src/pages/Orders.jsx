import React, { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { API_BASE } from "../config";

export default function Orders() {
  const { accessToken } = useAuth();
  const [orders, setOrders] = useState([]);

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
      setOrders(data);
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
        {orders.map((order) => (
          <div
            key={order.id}
            className="border rounded-lg p-5 shadow-sm space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="font-semibold">Order #{order.display_id}</h2>

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
                )}`}>
                {order.status.replace("_", " ")}
              </span>
            </div>

            <div className="space-y-1 text-sm">
              {order.items?.map((item) => (
                <div key={item.id}>
                  {item.quantity} × {item.product?.name}
                </div>
              ))}
            </div>

            <div className="flex justify-between items-center">
              <div className="font-semibold">Total: ${order.total_price}</div>

              {allowedTransitions[order.status]?.length > 0 && (
                <select
                  onChange={(e) => updateStatus(order.id, e.target.value)}
                  defaultValue=""
                  className="border p-2 rounded">
                  <option
                    value=""
                    disabled>
                    Change Status
                  </option>

                  {allowedTransitions[order.status].map((status) => (
                    <option
                      key={status}
                      value={status}>
                      {status.replace("_", " ")}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
