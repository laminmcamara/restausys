import { useState } from "react"
import { NavLink, Routes, Route } from "react-router-dom"
import { useAuth } from "../context/AuthContext";
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
  Settings
} from "lucide-react"

// Pages
import Dashboard from "../pages/Dashboard"
import POS from "../pages/POS"
import Orders from "../pages/Orders"
import Products from "../pages/Products"
import Categories from "../pages/Categories"
import Tables from "../pages/Tables"
import Kitchen from "../pages/Kitchen"
import Reports from "../pages/Reports"
import PickupDisplay from "../pages/PickupDisplay"
import SettingsPage from "../pages/SettingsPage"

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const systemName = "Smart POS"
  const restaurantName = "Main Branch Restaurant"
  const { user } = useAuth();
  const userName = user?.email || user?.username || "User";
  return (
    <div className="flex h-screen bg-gray-100">

      {/* ================= SIDEBAR ================= */}
      <aside
  className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300
  ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
  md:translate-x-0 md:static md:inset-0`}
>

  {/* ===== Brand Section ===== */}
  <div className="h-16 flex items-center border-b px-4">
    <div className="flex items-center space-x-3">
      <div className="w-10 h-10 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold">
        {systemName.slice(0, 2).toUpperCase()}
      </div>
      <div>
        <div className="font-bold text-gray-800">{systemName}</div>
        <div className="text-xs text-gray-500">Smart POS System</div>
      </div>
    </div>
  </div>

  {/* ===== Restaurant Name ===== */}
  <div className="px-4 py-3 text-sm text-gray-500 border-b">
    {restaurantName}
  </div>

  {/* ===== Navigation ===== */}
  <nav className="p-4 space-y-2">

    <SidebarLink to="/pos" icon={<CreditCard size={18} />} label="POS" />
    <SidebarLink to="/dashboard" icon={<LayoutDashboard size={18} />} label="Dashboard" />
    <SidebarLink to="/orders" icon={<Receipt size={18} />} label="Orders" />
    <SidebarLink to="/products" icon={<UtensilsCrossed size={18} />} label="Products" />
    <SidebarLink to="/categories" icon={<Folder size={18} />} label="Categories" />
    <SidebarLink to="/tables" icon={<Armchair size={18} />} label="Tables" />
    <SidebarLink to="/kitchen" icon={<ChefHat size={18} />} label="Kitchen" />
    <SidebarLink to="/reports" icon={<BarChart3 size={18} />} label="Reports" />
    <SidebarLink to="/pickup-display" icon={<Monitor size={18} />} label="Pickup Display" />
    <SidebarLink to="/settings" icon={<Settings size={18} />} label="Settings" />

  </nav>

</aside>

      {/* ================= MAIN SECTION ================= */}
      <div className="flex-1 flex flex-col">

        {/* Topbar */}
        <header className="h-16 bg-white shadow flex items-center justify-between px-6">

  <div className="flex items-center space-x-4">
    <button
      onClick={() => setSidebarOpen(!sidebarOpen)}
      className="md:hidden text-gray-600 text-xl"
    >
      ☰
    </button>

    <div className="text-lg font-semibold text-gray-800">
      {restaurantName}
    </div>
  </div>

  <div className="flex items-center space-x-4">

    <span className="text-gray-600">{userName}</span>

    <div className="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-semibold">
      {userName.charAt(0)}
    </div>

  </div>
</header>

        {/* Content Area */}
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="bg-white p-6 rounded-xl shadow">

            <Routes>
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="pos" element={<POS />} />
                <Route path="orders" element={<Orders />} />
                <Route path="products" element={<Products />} />
                <Route path="categories" element={<Categories />} />
                <Route path="tables" element={<Tables />} />
                <Route path="kitchen" element={<Kitchen />} />
                <Route path="reports" element={<Reports />} />
                <Route path="pickup-display" element={<PickupDisplay />} />
                <Route path="settings" element={<SettingsPage />} />

                {/* ✅ Default after login */}
                <Route path="/" element={<Dashboard />} />
            </Routes>

          </div>
        </main>

      </div>
    </div>
  )
}

/* ================= Reusable Sidebar Link ================= */

function SidebarLink({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center space-x-3 px-4 py-2 rounded-lg transition ${
          isActive
            ? "bg-blue-500 text-white"
            : "hover:bg-gray-100 text-gray-700"
        }`
      }
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  )
}

