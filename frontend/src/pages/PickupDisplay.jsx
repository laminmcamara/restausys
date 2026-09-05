import React, { useEffect, useState } from "react";
import { CheckCircle2, Timer, Bell, Eye, EyeOff, Loader2 } from "lucide-react";
import api from "../services/api";
import { useAuth } from "../hooks/useAuth";
import useDisplaySocket from "../hooks/useDisplaySocket";

export default function PickupDisplay() {
  const { user, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState([]);
  const [isStaffMode, setIsStaffMode] = useState(false);

  const ACTIVE_STATUSES = ["PLACED", "IN_PROGRESS", "READY"];

  const fetchOrders = async () => {
    const restaurantId = user?.restaurant?.id || user?.restaurant;
    if (!restaurantId) return;

    try {
      const { data } = await api.get("/orders/");
      let ordersData = data.results || data;

      // 1. Filter by status
      // 2. SORT: Newest first (Latest on top/start of grid)
      const processed = ordersData
        .filter((order) => ACTIVE_STATUSES.includes(order.status))
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

      setOrders(processed);
    } catch (error) {
      console.error("Fetch orders failed:", error);
    }
  };

  useEffect(() => {
    if (!authLoading && user) {
      fetchOrders();
      const interval = setInterval(fetchOrders, 10000); // Poll every 10s
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

  // CONSISTENT ID LOGIC: Use this in Kitchen and Orders list too
  const formatOrderId = (order) => {
    if (order.display_id) return order.display_id;
    const idStr = String(order.id);
    // Take last 4 of UUID
    return idStr.includes("-")
      ? idStr.split("-").pop()?.slice(-4).toUpperCase()
      : idStr.slice(-4);
  };

  const markServed = async (id) => {
    try {
      await api.post(`/orders/${id}/mark_served/`);
      setOrders((prev) => prev.filter((o) => o.id !== id));
    } catch (error) {
      console.error("Mark served failed:", error);
    }
  };

  if (authLoading)
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
      </div>
    );

  const readyOrders = orders.filter((o) => o.status === "READY");
  const preparingOrders = orders.filter((o) => o.status !== "READY");

  return (
    <div className="min-h-screen bg-[#0f172a] text-white overflow-hidden font-sans">
      <header className="bg-[#1e293b] px-8 py-6 flex justify-between items-center border-b border-slate-700 shadow-2xl">
        <div className="flex items-center gap-4">
          <div className="bg-indigo-600 p-3 rounded-2xl shadow-lg shadow-indigo-500/20">
            <Bell
              className="text-white animate-bounce"
              size={32}
            />
          </div>
          <div>
            <h1 className="text-4xl font-black tracking-tighter uppercase leading-none">
              Order Status
            </h1>
            <p className="text-slate-400 font-bold text-xs tracking-[0.2em] uppercase mt-1">
              {user?.restaurant?.name || "Restaurant"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <button
            onClick={() => setIsStaffMode(!isStaffMode)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 rounded-xl text-[10px] font-black tracking-widest hover:bg-slate-700 transition-all border border-slate-700">
            {isStaffMode ? <EyeOff size={14} /> : <Eye size={14} />}
            {isStaffMode ? "STAFF MODE" : "CUSTOMER VIEW"}
          </button>
          <div className="text-3xl font-black text-indigo-400 tabular-nums border-l border-slate-700 pl-6">
            {new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
      </header>

      <main className="grid grid-cols-2 h-[calc(100vh-110px)]">
        {/* PREPARING - Newest at the top left */}
        <section className="border-r border-slate-800 p-8 overflow-y-auto bg-slate-900/20">
          <div className="flex items-center gap-3 mb-8 border-b border-slate-800 pb-4">
            <Timer
              className="text-amber-500"
              size={32}
            />
            <h2 className="text-3xl font-black uppercase text-slate-500 tracking-tight">
              Preparing
            </h2>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
            {preparingOrders.map((order) => (
              <div
                key={order.id}
                className="bg-slate-800/40 border border-slate-700/50 p-6 rounded-[32px] flex flex-col items-center justify-center animate-in slide-in-from-top-4 duration-500">
                <span className="text-4xl font-black text-white mb-1">
                  #{formatOrderId(order)}
                </span>
                <span className="text-slate-500 font-black text-[12px] uppercase tracking-widest">
                  {order.table_name
                    ? `Table ${order.table_name}`
                    : order.customer_name || "Kitchen"}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* READY - Newest at the top left */}
        <section className="bg-emerald-500/5 p-8 overflow-y-auto">
          <div className="flex items-center gap-3 mb-8 border-b border-emerald-900/30 pb-4">
            <CheckCircle2
              className="text-emerald-500"
              size={32}
            />
            <h2 className="text-3xl font-black uppercase text-emerald-500 tracking-tight">
              Ready
            </h2>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
            {readyOrders.map((order) => (
              <div
                key={order.id}
                className="bg-emerald-500 p-8 rounded-[40px] flex flex-col items-center justify-center shadow-[0_0_50px_rgba(16,185,129,0.2)] ring-4 ring-emerald-500/20 animate-pulse">
                <span className="text-6xl font-black text-white mb-1">
                  #{formatOrderId(order)}
                </span>
                <span className="text-emerald-100 font-black text-xs uppercase tracking-widest">
                  {order.table_name
                    ? `Table ${order.table_name}`
                    : order.customer_name}
                </span>

                {isStaffMode && (
                  <button
                    onClick={() => markServed(order.id)}
                    className="mt-4 w-full py-3 bg-white text-emerald-600 rounded-2xl font-black text-xs hover:bg-emerald-50 transition-colors shadow-xl">
                    MARK SERVED
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="fixed bottom-0 w-full bg-indigo-600 py-3 overflow-hidden">
        <div className="inline-block animate-marquee whitespace-nowrap text-xs font-black uppercase tracking-[0.5em]">
          Please have your receipt ready • Thank you for dining with{" "}
          {user?.restaurant?.name || "us"} •
        </div>
      </footer>

      <style
        dangerouslySetInnerHTML={{
          __html: `
        @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
        .animate-marquee { display: inline-block; animation: marquee 30s linear infinite; }
      `,
        }}
      />
    </div>
  );
}
