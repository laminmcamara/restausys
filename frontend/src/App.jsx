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

        {/* Protected routes: require login AND active subscription */}
        <Route
          element={
            <ProtectedRoute>
              <SubscriptionGuard />
            </ProtectedRoute>
          }>
          <Route
            path="/dashboard"
            element={<DashboardLayout />}>
            <Route
              index
              element={<Dashboard />}
            />
            <Route
              path="orders"
              element={<Orders />}
            />
            <Route
              path="products"
              element={<MenuManagement />}
            />
            <Route
              path="kitchen"
              element={<KitchenDashboard />}
            />
            <Route
              path="pos"
              element={<POS />}
            />
            <Route
              path="inventory"
              element={<InventoryPage />}
            />
            <Route
              path="customers"
              element={<CustomersPage />}
            />
            <Route
              path="staff"
              element={<StaffPage />}
            />
            <Route
              path="tables"
              element={<TablesManagement />}
            />
            <Route
              path="floor-plan"
              element={<FloorPlan />}
            />
            <Route
              path="payments"
              element={<PaymentsPage />}
            />
            <Route
              path="billing"
              element={<BillingPage />}
            />
            <Route
              path="reports"
              element={<Reports />}
            />
            <Route
              path="activity"
              element={<ActivityPage />}
            />
            <Route
              path="settings"
              element={<SettingsPage />}
            />
            <Route
              path="profile"
              element={<ProfilePage />}
            />
            <Route
              path="discounts"
              element={<DiscountsPage />}
            />
            <Route
              path="categories"
              element={<Categories />}
            />
            <Route
              path="modifier-groups"
              element={<ModifierGroupsPage />}
            />
            <Route
              path="developers"
              element={<DevelopersPage />}
            />
            <Route
              path="files"
              element={<FilesPage />}
            />
            <Route
              path="help"
              element={<HelpPage />}
            />
            <Route
              path="tutorials"
              element={<TutorialsPage />}
            />
            <Route
              path="privacy"
              element={<PrivacyPage />}
            />
            <Route
              path="terms"
              element={<TermsPage />}
            />
          </Route>

          <Route
            path="/manager"
            element={<DashboardLayout />}>
            <Route
              index
              element={<Dashboard />}
            />
            <Route
              path="orders"
              element={<Orders />}
            />
            <Route
              path="products"
              element={<MenuManagement />}
            />
            <Route
              path="kitchen"
              element={<KitchenDashboard />}
            />
            <Route
              path="pos"
              element={<POS />}
            />
            <Route
              path="inventory"
              element={<InventoryPage />}
            />
            <Route
              path="customers"
              element={<CustomersPage />}
            />
            <Route
              path="staff"
              element={<StaffPage />}
            />
            <Route
              path="tables"
              element={<TablesManagement />}
            />
            <Route
              path="floor-plan"
              element={<FloorPlan />}
            />
            <Route
              path="payments"
              element={<PaymentsPage />}
            />
            <Route
              path="billing"
              element={<BillingPage />}
            />
            <Route
              path="reports"
              element={<Reports />}
            />
            <Route
              path="activity"
              element={<ActivityPage />}
            />
            <Route
              path="settings"
              element={<SettingsPage />}
            />
            <Route
              path="profile"
              element={<ProfilePage />}
            />
            <Route
              path="discounts"
              element={<DiscountsPage />}
            />
            <Route
              path="categories"
              element={<Categories />}
            />
            <Route
              path="modifier-groups"
              element={<ModifierGroupsPage />}
            />
            <Route
              path="developers"
              element={<DevelopersPage />}
            />
            <Route
              path="files"
              element={<FilesPage />}
            />
            <Route
              path="help"
              element={<HelpPage />}
            />
            <Route
              path="tutorials"
              element={<TutorialsPage />}
            />
            <Route
              path="privacy"
              element={<PrivacyPage />}
            />
            <Route
              path="terms"
              element={<TermsPage />}
            />
          </Route>
        </Route>

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
