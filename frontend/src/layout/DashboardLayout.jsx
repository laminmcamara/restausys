import { useState } from "react";
import { NavLink, Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  CreditCard,
  LayoutDashboard,
  Receipt,
  UtensilsCrossed,
  Folder,
  Armchair,
  ChefHat,
  BarChart3,
  Monitor,
  Settings,
  LogOut,
} from "lucide-react";

// Pages
import Dashboard from "../pages/Dashboard";
import POS from "../pages/POS";
import Orders from "../pages/Orders";
import Products from "../pages/MenuManagement";
import Categories from "../pages/Categories";
import Tables from "../pages/TablesManagement";
import Kitchen from "../pages/KitchenDashboard";
import Reports from "../pages/Reports";
import SettingsPage from "../pages/SettingsPage";

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { user, logout } = useAuth();

  const systemName = "BEEPOS";
  const restaurantName = user?.restaurant?.name || "Restaurant";
  const userName = user?.email || user?.username || "User";
  const restaurantId = user?.restaurant?.id || user?.restaurant_id;

  return (
    <div className="flex h-screen bg-gray-100">
      {/* ================= SIDEBAR ================= */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        md:translate-x-0 md:static md:inset-0`}>
        {/* Brand / Home Link */}
        <NavLink
          to="/dashboard"
          end
          className="h-16 flex items-center border-b px-4 hover:bg-gray-50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold">
              {systemName.slice(0, 2).toUpperCase()}
            </div>

            <div>
              <div className="font-bold text-gray-800">{systemName}</div>
              <div className="text-xs text-gray-500">Smart POS System</div>
            </div>
          </div>
        </NavLink>

        {/* Restaurant Name */}
        <div className="px-4 py-3 text-sm text-gray-500 border-b">
          {restaurantName}
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          {/* Home / Dashboard */}
          <SidebarLink
            to="/dashboard"
            end
            icon={<LayoutDashboard size={18} />}
            label="Home"
          />

          <SidebarLink
            to="/dashboard/pos"
            icon={<CreditCard size={18} />}
            label="POS"
          />

          <SidebarLink
            to="/dashboard/orders"
            icon={<Receipt size={18} />}
            label="Orders"
          />

          <SidebarLink
            to="/dashboard/menu"
            icon={<UtensilsCrossed size={18} />}
            label="Products"
          />

          <SidebarLink
            to="/dashboard/categories"
            icon={<Folder size={18} />}
            label="Categories"
          />

          <SidebarLink
            to="/dashboard/tables"
            icon={<Armchair size={18} />}
            label="Tables"
          />

          <SidebarLink
            to="/dashboard/kitchen"
            icon={<ChefHat size={18} />}
            label="Kitchen"
          />

          <SidebarLink
            to="/dashboard/reports"
            icon={<BarChart3 size={18} />}
            label="Reports"
          />

          {restaurantId && (
            <a
              href={`/display/${restaurantId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-3 px-4 py-2 rounded-lg transition hover:bg-gray-100 text-gray-700">
              <Monitor size={18} />
              <span>Pickup Display</span>
            </a>
          )}

          <SidebarLink
            to="/dashboard/settings"
            icon={<Settings size={18} />}
            label="Settings"
          />
        </nav>
      </aside>

      {/* ================= MAIN ================= */}
      <div className="flex-1 flex flex-col">
        {/* Topbar */}
        <header className="h-16 bg-white shadow flex items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="md:hidden text-gray-600 text-xl">
              ☰
            </button>

            <div className="text-lg font-semibold text-gray-800">
              {restaurantName}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-gray-600">{userName}</span>

            <div className="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-semibold">
              {userName.charAt(0).toUpperCase()}
            </div>

            <button
              type="button"
              onClick={logout}
              className="flex items-center space-x-2 bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded-lg">
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="bg-white p-6 rounded-xl shadow">
            <Routes>
              {/* Home page */}
              <Route
                index
                element={<Dashboard />}
              />

              <Route
                path="pos"
                element={<POS />}
              />

              <Route
                path="pos/:orderId"
                element={<POS />}
              />

              <Route
                path="orders"
                element={<Orders />}
              />

              <Route
                path="menu"
                element={<Products />}
              />

              <Route
                path="categories"
                element={<Categories />}
              />

              <Route
                path="tables"
                element={<Tables />}
              />

              <Route
                path="kitchen"
                element={<Kitchen />}
              />

              <Route
                path="reports"
                element={<Reports />}
              />

              <Route
                path="settings"
                element={<SettingsPage />}
              />

              <Route
                path="*"
                element={
                  <Navigate
                    to="/dashboard"
                    replace
                  />
                }
              />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
}

/* ================= Sidebar Link ================= */

function SidebarLink({ to, icon, label, end = false }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center space-x-3 px-4 py-2 rounded-lg transition ${
          isActive
            ? "bg-blue-500 text-white"
            : "hover:bg-gray-100 text-gray-700"
        }`
      }>
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}
