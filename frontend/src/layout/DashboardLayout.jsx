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
  ChevronDown,
  SlidersHorizontal,
  UserCog,
  CircleDollarSign,
  Users,
  Boxes,
  Tag,
} from "lucide-react";
import logo from "../assets/logo.png";

// Pages
import Dashboard from "../pages/Dashboard";
import FloorPlan from "../pages/FloorPlan";
import POS from "../pages/POS";
import Orders from "../pages/Orders";
import Products from "../pages/MenuManagement";
import Categories from "../pages/Categories";
import ModifierGroups from "../pages/ModifierGroupsPage";
import Tables from "../pages/TablesManagement";
import Kitchen from "../pages/KitchenDashboard";
import StaffPage from "../pages/StaffPage";
import PaymentsPage from "../pages/PaymentsPage";
import CustomersPage from "../pages/CustomersPage";
import InventoryPage from "../pages/InventoryPage";
import DiscountsPage from "../pages/DiscountsPage";
import Reports from "../pages/Reports";
import SettingsPage from "../pages/SettingsPage";

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [restaurantMenuOpen, setRestaurantMenuOpen] = useState(false);

  const { user, logout } = useAuth();

  const systemName = "BEEPOS";
  const restaurantName = user?.restaurant?.name || "Restaurant";
  const userName = user?.email || user?.username || "User";
  const restaurantId = user?.restaurant?.id || user?.restaurant_id;

  return (
    <div className="flex h-screen bg-slate-100">
      {/* ================= SIDEBAR ================= */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 shadow-2xl transform transition-transform duration-300
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        md:translate-x-0 md:static md:inset-0`}>
        {/* Brand / Home Link */}
        <NavLink
          to="/dashboard"
          end
          className="h-16 flex items-center border-b border-slate-700 px-4 hover:bg-slate-800 transition">
          <div className="flex items-center space-x-3">
            <img
              src={logo}
              alt="BEEPOS"
              className="h-10 w-10 rounded-lg object-contain"
            />
            <div>
              <div className="font-black text-amber-400">{systemName}</div>
              <div className="text-xs text-slate-400">Smart POS System</div>
            </div>
          </div>
        </NavLink>

        {/* Restaurant Name */}
        <div className="px-4 py-3 text-sm font-medium text-slate-400 border-b border-slate-700">
          {restaurantName}
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1 overflow-y-auto">
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
            to="/dashboard/products"
            icon={<UtensilsCrossed size={18} />}
            label="Products"
          />
          <SidebarLink
            to="/dashboard/categories"
            icon={<Folder size={18} />}
            label="Categories"
          />
          <SidebarLink
            to="/dashboard/modifiers"
            icon={<SlidersHorizontal size={18} />}
            label="Modifiers"
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
            to="/dashboard/staff"
            icon={<UserCog size={18} />}
            label="Staff"
          />

          <SidebarLink
            to="/dashboard/customers"
            icon={<Users size={18} />}
            label="Customers"
          />

          <SidebarLink
            to="/dashboard/payments"
            icon={<CircleDollarSign size={18} />}
            label="Payments"
          />

          <SidebarLink
            to="/dashboard/inventory"
            icon={<Boxes size={18} />}
            label="Inventory"
          />

          <SidebarLink
            to="/dashboard/discounts"
            icon={<Tag size={18} />}
            label="Discounts"
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
              className="flex items-center space-x-3 px-4 py-2 rounded-lg transition hover:bg-slate-800 text-slate-300">
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
        <header className="h-16 bg-white shadow-sm flex items-center justify-between px-6 border-b border-slate-200">
          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="md:hidden text-slate-600 text-xl">
              ☰
            </button>

            {/* Restaurant Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setRestaurantMenuOpen((prev) => !prev)}
                className="flex items-center space-x-2 text-lg font-bold text-slate-800 hover:text-amber-600 transition">
                <span>{restaurantName}</span>
                <ChevronDown
                  size={18}
                  className={`transition-transform ${
                    restaurantMenuOpen ? "rotate-180" : ""
                  }`}
                />
              </button>

              {restaurantMenuOpen && (
                <div className="absolute left-0 top-10 z-50 w-48 rounded-xl border border-slate-200 bg-white py-2 shadow-lg">
                  <NavLink
                    to="/dashboard/restaurant/floor-plan"
                    onClick={() => setRestaurantMenuOpen(false)}
                    className={({ isActive }) =>
                      `block px-4 py-2 text-sm font-medium transition ${
                        isActive
                          ? "bg-amber-50 text-amber-700"
                          : "text-slate-700 hover:bg-slate-100"
                      }`
                    }>
                    Floor Plan
                  </NavLink>

                  <NavLink
                    to="/dashboard/restaurant/dine-in"
                    onClick={() => setRestaurantMenuOpen(false)}
                    className={({ isActive }) =>
                      `block px-4 py-2 text-sm font-medium transition ${
                        isActive
                          ? "bg-amber-50 text-amber-700"
                          : "text-slate-700 hover:bg-slate-100"
                      }`
                    }>
                    Dine-in
                  </NavLink>

                  <NavLink
                    to="/dashboard/restaurant/take-out"
                    onClick={() => setRestaurantMenuOpen(false)}
                    className={({ isActive }) =>
                      `block px-4 py-2 text-sm font-medium transition ${
                        isActive
                          ? "bg-amber-50 text-amber-700"
                          : "text-slate-700 hover:bg-slate-100"
                      }`
                    }>
                    Take-out
                  </NavLink>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm font-medium text-slate-600 hidden sm:block">
              {userName}
            </span>

            <div className="w-9 h-9 rounded-full bg-amber-400 text-slate-950 flex items-center justify-center font-black text-sm">
              {userName.charAt(0).toUpperCase()}
            </div>

            <button
              type="button"
              onClick={logout}
              className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded-lg text-sm font-semibold transition">
              <LogOut size={16} />
              <span className="hidden sm:block">Logout</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="bg-white p-6 rounded-xl shadow-sm">
            <Routes>
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
                path="restaurant/floor-plan"
                element={<FloorPlan />}
              />
              <Route
                path="restaurant/dine-in"
                element={<POS orderType="dine-in" />}
              />
              <Route
                path="restaurant/dine-in/:tableId"
                element={<POS orderType="dine-in" />}
              />
              <Route
                path="restaurant/take-out"
                element={<POS orderType="take-out" />}
              />
              <Route
                path="orders"
                element={<Orders />}
              />
              <Route
                path="products"
                element={<Products />}
              />
              <Route
                path="categories"
                element={<Categories />}
              />
              <Route
                path="modifiers"
                element={<ModifierGroups />}
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
                path="staff"
                element={<StaffPage />}
              />
              <Route
                path="customers"
                element={<CustomersPage />}
              />
              <Route
                path="payments"
                element={<PaymentsPage />}
              />
              <Route
                path="inventory"
                element={<InventoryPage />}
              />
              <Route
                path="discounts"
                element={<DiscountsPage />}
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
        `flex items-center space-x-3 px-4 py-2.5 rounded-lg transition font-medium text-sm ${
          isActive
            ? "bg-amber-400 text-slate-950 shadow-md shadow-amber-500/20"
            : "hover:bg-slate-800 text-slate-300"
        }`
      }>
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}
