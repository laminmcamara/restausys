import React, { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import api from "../services/api";

export default function Dashboard() {
  const { user } = useAuth();
  const location = useLocation();

  const [dashboardData, setDashboardData] = useState(null);
  const [message, setMessage] = useState(
    location.state?.registrationMessage || ""
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const restaurantName = useMemo(() => {
    return (
      user?.restaurant?.name ||
      user?.restaurant_name ||
      user?.restaurantName ||
      dashboardData?.restaurant?.name ||
      dashboardData?.tenant?.restaurant_name ||
      dashboardData?.tenant?.restaurant?.name ||
      "Restaurant Dashboard"
    );
  }, [user, dashboardData]);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");

        const response = await api.get("/dashboard/");

        if (!cancelled) {
          setDashboardData(response.data);
        }
      } catch (err) {
        console.error("DASHBOARD ERROR:", err);

        if (!cancelled) {
          setError(
            err?.response?.data?.detail ||
              err?.response?.data?.message ||
              "Could not load dashboard data."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!message) {
      return undefined;
    }

    const timer = setTimeout(() => {
      setMessage("");
    }, 5000);

    return () => clearTimeout(timer);
  }, [message]);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-pulse text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div
          className="rounded border border-red-200 bg-red-50 px-4 py-3 text-red-700"
          role="alert">
          <strong className="font-bold">Error: </strong>
          <span>{error}</span>
        </div>
      </div>
    );
  }

  const summary = dashboardData?.summary || {};
  const trends = dashboardData?.trends || {};

  return (
    <main className="mx-auto max-w-7xl p-8">
      {message && (
        <div
          className="relative mb-4 rounded border border-green-400 bg-green-100 px-4 py-3 text-green-700"
          role="alert">
          {message}
        </div>
      )}

      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{restaurantName}</h1>

        <p className="text-gray-600">
          Welcome back, <span className="font-semibold">{user.username}</span>.
          Here is your restaurant overview.
        </p>
      </header>

      {dashboardData?.restaurant?.onboarding_completed === false && (
        <div className="mb-6 border-l-4 border-yellow-400 bg-yellow-50 p-4 text-yellow-800">
          <p className="font-medium">Action Required</p>
          <p>Please complete your restaurant profile before the trial ends.</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-xs font-semibold uppercase text-gray-500">
            Today’s Orders
          </h3>

          <p className="text-2xl font-bold text-gray-900">
            {summary.today_orders ?? 0}
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-xs font-semibold uppercase text-gray-500">
            Today’s Revenue
          </h3>

          <p className="text-2xl font-bold text-green-600">
            {summary.today_revenue ?? 0}
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-xs font-semibold uppercase text-gray-500">
            Active Orders
          </h3>

          <p className="text-2xl font-bold text-blue-600">
            {summary.active_orders_count ?? 0}
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-xs font-semibold uppercase text-gray-500">
            Tables In Use
          </h3>

          <p className="text-2xl font-bold text-orange-600">
            {summary.tables_in_use ?? 0}
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-xs font-semibold uppercase text-gray-500">
            This Week’s Orders
          </h3>

          <p className="text-2xl font-bold text-purple-600">
            {summary.this_week_orders ?? 0}
          </p>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-xs font-semibold uppercase text-gray-500">
            Monthly Revenue
          </h3>

          <p className="text-2xl font-bold text-cyan-600">
            {summary.monthly_revenue ?? 0}
          </p>
        </div>
      </div>

      <section className="mt-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-bold text-gray-900">Trends</h2>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <TrendCard
            label="Orders"
            trend={trends.orders}
          />

          <TrendCard
            label="Revenue"
            trend={trends.revenue}
          />

          <TrendCard
            label="Weekly Orders"
            trend={trends.weekly_orders}
          />

          <TrendCard
            label="Weekly Revenue"
            trend={trends.weekly_revenue}
          />
        </div>
      </section>
    </main>
  );
}

function TrendCard({ label, trend }) {
  const percentage = trend?.percentage;

  const direction = trend?.direction;

  if (percentage === null || percentage === undefined) {
    return (
      <div className="rounded border border-gray-100 bg-gray-50 p-4">
        <p className="text-sm text-gray-500">{label}</p>

        <p className="mt-1 text-sm text-gray-500">No comparison data</p>
      </div>
    );
  }

  const color =
    direction === "up"
      ? "text-green-600"
      : direction === "down"
      ? "text-red-600"
      : "text-gray-600";

  return (
    <div className="rounded border border-gray-100 bg-gray-50 p-4">
      <p className="text-sm text-gray-500">{label}</p>

      <p className={`mt-1 text-xl font-bold ${color}`}>
        {direction === "up" ? "+" : direction === "down" ? "-" : ""}
        {percentage}%
      </p>
    </div>
  );
}
