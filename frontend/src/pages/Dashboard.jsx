import React, { useEffect, useState, useMemo } from "react";
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

  // Best-effort: determine the restaurant name from the logged-in user/tenant first
  const restaurantName = useMemo(() => {
    // Common patterns depending on your backend/serializer
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
    const loadDashboard = async () => {
      try {
        setLoading(true);
        const response = await api.get("/settings/");
        setDashboardData(response.data);
      } catch (err) {
        console.error("DASHBOARD ERROR:", err);
        setError(
          err?.response?.data?.message ||
            err?.response?.data?.detail ||
            "Could not load dashboard data."
        );
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

  // Auto-hide success messages after 5 seconds
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 5000);
    return () => clearTimeout(timer);
  }, [message]);

  // 1. Handle Loading State
  if (loading || !user) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-pulse text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  // 2. Handle Error State
  if (error) {
    return (
      <div className="p-8">
        <div
          className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative"
          role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <main className="p-8 max-w-7xl mx-auto">
      {/* Success Notification */}
      {message && (
        <div
          className="mb-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative"
          role="alert">
          {message}
        </div>
      )}

      {/* Header Section */}
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{restaurantName}</h1>

        <p className="text-gray-600">
          Welcome back, <span className="font-semibold">{user.username}</span>.{" "}
          Here is your {dashboardData?.company?.name || "BEEPOS"} overview.
        </p>
      </header>

      {/* Onboarding Alert */}
      {dashboardData?.restaurant?.onboarding_completed === false && (
        <div className="mb-6 p-4 bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800">
          <p className="font-medium">Action Required</p>
          <p>Please complete your restaurant profile before the trial ends.</p>
        </div>
      )}

      {/* Dashboard Content Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 bg-white rounded-lg shadow-sm border border-gray-200">
          <h3 className="font-semibold text-gray-500 uppercase text-xs">
            Status
          </h3>
          <p className="text-2xl font-bold text-green-600">Active</p>
        </div>
        {/* Add more dashboard widgets here */}
      </div>
    </main>
  );
}
