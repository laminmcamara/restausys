// frontend/src/guards/SubscriptionGuard.jsx

import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import api from "../services/api";

const VALID_STATUSES = new Set(["active", "trialing"]);

function subscriptionAllowsAccess(subscription) {
  if (!subscription) {
    return false;
  }

  const status = String(subscription.status || "")
    .trim()
    .toLowerCase();

  if (!VALID_STATUSES.has(status)) {
    return false;
  }

  if (!subscription.current_period_end) {
    return true;
  }

  const periodEnd = new Date(subscription.current_period_end);

  if (Number.isNaN(periodEnd.getTime())) {
    return false;
  }

  return periodEnd.getTime() > Date.now();
}

export default function SubscriptionGuard({ children }) {
  const location = useLocation();

  const [loading, setLoading] = useState(true);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function verifySubscription() {
      try {
        const response = await api.get("/subscription/");
        const subscription = response.data?.subscription || response.data;

        console.log("SubscriptionGuard subscription:", subscription);

        if (!cancelled) {
          setAllowed(subscriptionAllowsAccess(subscription));
        }
      } catch (error) {
        console.error(
          "SubscriptionGuard request failed:",
          error?.response?.status,
          error?.response?.data || error?.message
        );

        if (!cancelled) {
          setAllowed(false);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    verifySubscription();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="h-9 w-9 animate-spin rounded-full border-4 border-amber-200 border-t-amber-600" />
      </div>
    );
  }

  if (!allowed) {
    return (
      <Navigate
        to="/subscription"
        replace
        state={{
          from: location.pathname,
        }}
      />
    );
  }

  return children;
}
