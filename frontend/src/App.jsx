import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./hooks/useAuth";
import { useRTL } from "./hooks/useRTL";

// i18n
import "./i18n"; // <-- ensures i18next is initialized before rendering

import HomePage from "./pages/HomePage";
import Login from "./pages/Login";
import DashboardLayout from "./layout/DashboardLayout";
import PickupDisplay from "./pages/PickupDisplay";
import OnboardingPage from "./pages/OnboardingPage";

function ProtectedRoute({ children }) {
  const { accessToken, authLoading } = useAuth();
  
  console.log("ProtectedRoute", { authLoading, hasToken: !!accessToken });

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
  // Initialize RTL handling based on current language
  useRTL();

  return (
    <AuthProvider>
      <Routes>
        {/* Public homepage */}
        <Route
          path="/"
          element={<HomePage />}
        />

        {/* Public login page */}
        <Route
          path="/login"
          element={<Login />}
        />

        {/* Public onboarding page */}
        <Route
          path="/onboarding"
          element={<OnboardingPage />}
        />

        {/* Public pickup display */}
        <Route
          path="/display/:restaurantId"
          element={<PickupDisplay />}
        />

        {/* Protected dashboard */}
        <Route
          path="/dashboard/*"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        />

        {/* Manager area - protected */}
        <Route
          path="/manager/*"
          element={
            <ProtectedRoute>
              <DashboardLayout />
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
