import React, { useEffect, useState } from "react";
import useDisplaySocket from "../hooks/useDisplaySocket";
import api from "../services/api";
import { useAuth } from "../hooks/useAuth";

function PickupDisplay() {
  const [orders, setOrders] = useState([]);
  const { user } = useAuth();

  const ACTIVE_STATUSES = ["PLACED", "IN_PROGRESS", "READY"];

  /* ================= FETCH ORDERS ================= */

  const fetchOrders = async () => {
    if (!user?.restaurant) return;

    try {
      const { data } = await api.get("/orders/");

      const ordersData = data.results || data;

      const filtered = ordersData.filter((order) =>
        ACTIVE_STATUSES.includes(order.status)
      );

      setOrders(filtered);
    } catch (error) {
      console.error(
        "Fetch orders failed:",
        error.response?.data || error.message
      );
    }
  };

  /* ================= INITIAL LOAD ================= */

  useEffect(() => {
    if (user?.restaurant) {
      fetchOrders();
    }
  }, [user]);

  /* ================= WEBSOCKET ================= */

  useDisplaySocket(
    user?.restaurant,
    (data) => {
      if (data.event === "ORDER_STATUS_UPDATED") {
        const updatedOrder = data.order;

        // Remove if no longer active
        if (!ACTIVE_STATUSES.includes(updatedOrder.status)) {
          setOrders((prev) => prev.filter((o) => o.id !== updatedOrder.id));
          return;
        }

        // Add/update order
        setOrders((prev) => {
          const filtered = prev.filter((o) => o.id !== updatedOrder.id);
          return [updatedOrder, ...filtered];
        });
      }
    },
    !!user?.restaurant
  );

  /* ================= ACTION ================= */

  const markServed = async (id) => {
    try {
      await api.post(`/orders/${id}/mark_served/`);
    } catch (error) {
      console.error(
        "Mark served failed:",
        error.response?.data || error.message
      );
    }
  };

  /* ================= HELPERS ================= */

  const getStatusColor = (status) => {
    switch (status) {
      case "READY":
        return "text-green-400";
      case "IN_PROGRESS":
        return "text-yellow-400";
      case "PLACED":
        return "text-white";
      default:
        return "text-gray-400";
    }
  };

  /* ================= UI ================= */

  return (
    <div className="p-6 grid md:grid-cols-4 gap-6">
      {orders.map((order) => (
        <div
          key={order.id}
          className="bg-black text-white rounded p-6 shadow-lg">
          {/* Order Number */}
          <h2 className="text-4xl font-bold">#{order.display_id}</h2>

          {/* Table OR Customer */}
          {(order.table_name || order.customer_name) && (
            <p className="mt-2 text-xl font-semibold">
              {order.table_name
                ? `Table ${order.table_name}`
                : order.customer_name}
            </p>
          )}

          {/* Status */}
          <p
            className={`mt-3 text-lg font-bold ${getStatusColor(
              order.status
            )}`}>
            {order.status.replace("_", " ")}
          </p>

          {/* Staff Button */}
          <button
            onClick={() => markServed(order.id)}
            className="mt-4 bg-green-500 hover:bg-green-600 px-4 py-2 rounded font-semibold">
            Mark Served
          </button>
        </div>
      ))}
    </div>
  );
}

export default PickupDisplay;
