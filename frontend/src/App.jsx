import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./hooks/useAuth";

import Login from "./pages/Login";
import DashboardLayout from "./layout/DashboardLayout";
import PickupDisplay from "./pages/PickupDisplay";

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
  return (
    <AuthProvider>
      <Routes>
        <Route
          path="/"
          element={<Login />}
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
