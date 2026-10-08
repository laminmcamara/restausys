import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./hooks/useAuth";
import { useRTL } from "./hooks/useRTL";

// i18n
import "./i18n";

import HomePage from "./pages/HomePage";
import Login from "./pages/Login";
import DashboardLayout from "./layout/DashboardLayout";
import PickupDisplay from "./pages/PickupDisplay";
import OnboardingPage from "./pages/OnboardingPage";
import PublicTableMenu from "./pages/PublicTableMenu";
import POS from "./pages/POS";
import SubscriptionPage from "./pages/SubscriptionPage";
import SubscriptionGuard from "./guards/SubscriptionGuard";

// Dashboard pages
import Dashboard from "./pages/Dashboard";
import Orders from "./pages/Orders";
import MenuManagement from "./pages/MenuManagement";
import KitchenDashboard from "./pages/KitchenDashboard";
import InventoryPage from "./pages/InventoryPage";
import CustomersPage from "./pages/CustomersPage";
import StaffPage from "./pages/StaffPage";
import TablesManagement from "./pages/TablesManagement";
import FloorPlan from "./pages/FloorPlan";
import PaymentsPage from "./pages/PaymentsPage";
import BillingPage from "./pages/BillingPage";
import Reports from "./pages/Reports";
import ActivityPage from "./pages/ActivityPage";
import SettingsPage from "./pages/SettingsPage";
import ProfilePage from "./pages/ProfilePage";
import DiscountsPage from "./pages/DiscountsPage";
import Categories from "./pages/Categories";
import ModifierGroupsPage from "./pages/ModifierGroupsPage";
import DevelopersPage from "./pages/DevelopersPage";
import FilesPage from "./pages/FilesPage";
import HelpPage from "./pages/HelpPage";
import TutorialsPage from "./pages/TutorialsPage";
import PrivacyPage from "./pages/PrivacyPage";
import TermsPage from "./pages/TermsPage";
// import SubscriptionGuard from "./guards/SubscriptionGuard";

function ProtectedRoute({ children }) {
  const { accessToken, authLoading } = useAuth();

  if (authLoading) {
    return <div className="p-8 text-gray-600">Checking authentication...</div>;
  }

  if (!accessToken) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }

  return children;
}

function App() {
  useRTL();

  return (
    <AuthProvider>
      <Routes>
        {/* Public routes */}
        <Route
          path="/"
          element={<HomePage />}
        />
        <Route
          path="/login"
          element={<Login />}
        />
        <Route
          path="/onboarding"
          element={<OnboardingPage />}
        />
        <Route
          path="/table/:token/"
          element={<PublicTableMenu />}
        />
        <Route
          path="/pickup"
          element={<PickupDisplay />}
        />
        <Route
          path="/subscription"
          element={<SubscriptionPage />}
        />

        {/* Login required + subscription required */}
        <Route
          path="/dashboard/*"
          element={
            <ProtectedRoute>
              <SubscriptionGuard>
                <DashboardLayout />
              </SubscriptionGuard>
            </ProtectedRoute>
          }
        />
        <Route
          path="/manager/*"
          element={
            <ProtectedRoute>
              <SubscriptionGuard>
                <DashboardLayout />
              </SubscriptionGuard>
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route
          path="*"
          element={
            <Navigate
              to="/"
              replace
            />
          }
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;
