import { useState } from "react";
import { NavLink, Routes, Route, Navigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
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
import ProfilePage from "../pages/ProfilePage";
import TutorialsPage from "../pages/TutorialsPage";
import HelpPage from "../pages/HelpPage";
import FilesPage from "../pages/FilesPage";
import DevelopersPage from "../pages/DevelopersPage";
import BillingPage from "../pages/BillingPage";
import ActivityPage from "../pages/ActivityPage";
import PrivacyPage from "../pages/PrivacyPage";
import TermsPage from "../pages/TermsPage";

// Components
import LanguageSwitcher from "../components/LanguageSwitcher";
import RightSidebar from "../components/RightSidebar";
import DashboardFooter from "../components/DashboardFooter";

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [controlPanelOpen, setControlPanelOpen] = useState(true);
  const [restaurantMenuOpen, setRestaurantMenuOpen] = useState(false);

  const { user, logout } = useAuth();
  const { t } = useTranslation();

  const systemName = "BEEPOS";
  const restaurantName = user?.restaurant?.name || t("common.restaurant");
  const userName = user?.email || user?.username || t("common.user");
  const restaurantId = user?.restaurant?.id || user?.restaurant_id;

  const closeMobileSidebar = () => {
    setSidebarOpen(false);
  };

  return (
    <div className="flex h-screen bg-slate-100">
      {/* Left sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-slate-900 shadow-2xl transition-transform duration-300 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } md:static md:inset-0 md:translate-x-0`}>
        {/* Brand */}
        <NavLink
          to="/dashboard"
          end
          onClick={closeMobileSidebar}
          className="flex h-16 items-center border-b border-slate-700 px-4 transition hover:bg-slate-800">
          <div className="flex items-center space-x-3">
            <img
              src={logo}
              alt={systemName}
              className="h-10 w-10 rounded-lg object-contain"
            />

            <div>
              <div className="font-black text-amber-400">{systemName}</div>
              <div className="text-xs text-slate-400">
                {t("common.smartPosSystem")}
              </div>
            </div>
          </div>
        </NavLink>

        {/* Restaurant name */}
        <div className="border-b border-slate-700 px-4 py-3 text-sm font-medium text-slate-400">
          {restaurantName}
        </div>

        {/* Navigation */}
        <nav className="h-screen w-64 space-y-1 overflow-y-auto bg-slate-900 p-3">
          {/* Operations */}
          <div className="space-y-1">
            <SidebarLink
              to="/dashboard"
              end
              icon={<LayoutDashboard size={28} />}
              label={t("sidebar.home")}
              onClick={closeMobileSidebar}
            />

            <SidebarLink
              to="/dashboard/pos"
              icon={<CreditCard size={28} />}
              label={t("sidebar.pos")}
              onClick={closeMobileSidebar}
            />

            <SidebarLink
              to="/dashboard/orders"
              icon={<Receipt size={28} />}
              label={t("sidebar.orders")}
              onClick={closeMobileSidebar}
            />

            <SidebarLink
              to="/dashboard/tables"
              icon={<Armchair size={28} />}
              label={t("sidebar.tables")}
              onClick={closeMobileSidebar}
            />

            <SidebarLink
              to="/dashboard/kitchen"
              icon={<ChefHat size={28} />}
              label={t("sidebar.kitchen")}
              onClick={closeMobileSidebar}
            />

            <SidebarLink
              to="/dashboard/payments"
              icon={<CircleDollarSign size={28} />}
              label={t("sidebar.payments")}
              onClick={closeMobileSidebar}
            />
          </div>

          {/* Public display */}
          {restaurantId && (
            <a
              href={`/display/${restaurantId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-3 rounded-lg px-4 py-2 text-slate-300 transition hover:bg-slate-800">
              <Monitor size={18} />
              <span>{t("sidebar.pickupDisplay")}</span>
            </a>
          )}

          {/* Analytics */}
          <SidebarLink
            to="/dashboard/reports"
            icon={<BarChart3 size={28} />}
            label={t("sidebar.reports")}
            onClick={closeMobileSidebar}
          />

          <div className="my-2 border-t border-slate-800" />

          {/* Control panel */}
          <button
            type="button"
            onClick={() => setControlPanelOpen((value) => !value)}
            className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-slate-200 transition hover:bg-slate-800">
            <span className="flex items-center space-x-3">
              <SlidersHorizontal size={28} />
              <span className="font-medium">{t("sidebar.controlPanel")}</span>
            </span>

            <ChevronDown
              size={28}
              className={`transition-transform duration-200 ${
                controlPanelOpen ? "rotate-180" : "rotate-0"
              }`}
            />
          </button>

          {controlPanelOpen && (
            <div className="ml-4 mt-1 space-y-1 border-l border-slate-700 pl-2">
              <SidebarLink
                to="/dashboard/products"
                icon={<UtensilsCrossed size={18} />}
                label={t("sidebar.products")}
                onClick={closeMobileSidebar}
              />

              <SidebarLink
                to="/dashboard/categories"
                icon={<Folder size={28} />}
                label={t("sidebar.categories")}
                onClick={closeMobileSidebar}
              />

              <SidebarLink
                to="/dashboard/modifiers"
                icon={<SlidersHorizontal size={28} />}
                label={t("sidebar.modifiers")}
                onClick={closeMobileSidebar}
              />

              <SidebarLink
                to="/dashboard/inventory"
                icon={<Boxes size={28} />}
                label={t("sidebar.inventory")}
                onClick={closeMobileSidebar}
              />

              <SidebarLink
                to="/dashboard/discounts"
                icon={<Tag size={28} />}
                label={t("sidebar.discounts")}
                onClick={closeMobileSidebar}
              />

              <SidebarLink
                to="/dashboard/staff"
                icon={<UserCog size={28} />}
                label={t("sidebar.staff")}
                onClick={closeMobileSidebar}
              />

              <SidebarLink
                to="/dashboard/customers"
                icon={<Users size={28} />}
                label={t("sidebar.customers")}
                onClick={closeMobileSidebar}
              />

              <SidebarLink
                to="/dashboard/settings"
                icon={<Settings size={28} />}
                label={t("sidebar.settings")}
                onClick={closeMobileSidebar}
              />
            </div>
          )}
        </nav>
      </aside>

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar */}
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={() => setSidebarOpen((value) => !value)}
              className="text-xl text-slate-600 md:hidden"
              aria-label={t("common.toggleNavigation")}
              aria-expanded={sidebarOpen}>
              ☰
            </button>

            {/* Restaurant dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setRestaurantMenuOpen((value) => !value)}
                className="flex items-center space-x-2 text-lg font-bold text-slate-800 transition hover:text-amber-600"
                aria-expanded={restaurantMenuOpen}>
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
                  <DashboardMenuLink
                    to="/dashboard/restaurant/floor-plan"
                    label={t("restaurant.floorPlan")}
                    onClick={() => setRestaurantMenuOpen(false)}
                  />

                  <DashboardMenuLink
                    to="/dashboard/restaurant/dine-in"
                    label={t("restaurant.dineIn")}
                    onClick={() => setRestaurantMenuOpen(false)}
                  />

                  <DashboardMenuLink
                    to="/dashboard/restaurant/take-out"
                    label={t("restaurant.takeOut")}
                    onClick={() => setRestaurantMenuOpen(false)}
                  />
                </div>
              )}
            </div>
          </div>

          {/* User controls */}
          <div className="flex items-center gap-3">
            <div className="shrink-0">
              <LanguageSwitcher />
            </div>

            <span className="hidden text-sm font-medium text-slate-600 sm:block">
              {userName}
            </span>

            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-400 text-sm font-black text-slate-950">
              {userName.charAt(0).toUpperCase()}
            </div>

            <button
              type="button"
              onClick={logout}
              className="flex items-center space-x-2 rounded-lg bg-slate-800 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-slate-700">
              <LogOut size={16} />
              <span className="hidden sm:block">{t("common.logout")}</span>
            </button>
          </div>
        </header>

        {/* Content and right sidebar */}
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <main className="min-w-0 flex-1 overflow-y-auto p-6">
            <div className="flex min-h-full flex-col rounded-xl bg-white p-6 shadow-sm">
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
                  path="settings/profile"
                  element={<ProfilePage />}
                />

                <Route
                  path="tutorials"
                  element={<TutorialsPage />}
                />
                <Route
                  path="help"
                  element={<HelpPage />}
                />
                <Route
                  path="files"
                  element={<FilesPage />}
                />
                <Route
                  path="developers"
                  element={<DevelopersPage />}
                />
                <Route
                  path="billing"
                  element={<BillingPage />}
                />
                <Route
                  path="activity"
                  element={<ActivityPage />}
                />
                <Route
                  path="privacy"
                  element={<PrivacyPage />}
                />
                <Route
                  path="terms"
                  element={<TermsPage />}
                />

                {/* Keep the catch-all route last */}
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

              <DashboardFooter />
            </div>
          </main>

          <RightSidebar />
        </div>
      </div>
    </div>
  );
}

function SidebarLink({ to, icon, label, end = false, onClick }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center space-x-3 rounded-lg px-4 py-2.5 text-sm font-medium transition ${
          isActive
            ? "bg-amber-400 text-slate-950 shadow-md shadow-amber-500/20"
            : "text-slate-300 hover:bg-slate-800"
        }`
      }>
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}

function DashboardMenuLink({ to, label, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        `block px-4 py-2 text-sm font-medium transition ${
          isActive
            ? "bg-amber-50 text-amber-700"
            : "text-slate-700 hover:bg-slate-100"
        }`
      }>
      {label}
    </NavLink>
  );
}
