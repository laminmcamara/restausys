import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import api from "../services/api";

export default function SubscriptionGuard() {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let active = true;

    async function checkAccess() {
      try {
        const response = await api.get("/dashboard/");
        const data = response.data;

        if (!active) return;

        // Superusers bypass subscription check
        const isSuperuser = Boolean(data?.user?.is_superuser);
        const hasActiveSubscription = Boolean(
          data?.access?.has_active_subscription
        );

        setAllowed(isSuperuser || hasActiveSubscription || hasActiveTrial);
      } catch {
        if (active) {
          setAllowed(false);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    checkAccess();

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-9 w-9 animate-spin rounded-full border-4 border-amber-200 border-t-amber-600" />
      </div>
    );
  }

  if (!allowed) {
    return (
      <Navigate
        to="/subscription"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return <Outlet />;
}
