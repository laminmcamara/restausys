import React, { useEffect, useMemo, useState } from "react";
import {
  Bell,
  ClipboardList,
  CreditCard,
  Loader2,
  Palette,
  ReceiptText,
  Save,
  Settings as SettingsIcon,
  ShoppingBag,
  Store,
  Users,
  CheckCircle2,
  AlertCircle,
  Wallet,
} from "lucide-react";
import api from "../services/api";
import SessionManagement from "../components/SessionManagement";

// Updated tabs to include Register and Staff
const tabs = [
  { id: "general", label: "General", icon: Store },
  { id: "register", label: "Register", icon: Wallet },
  { id: "tax", label: "Tax & Charges", icon: CreditCard },
  { id: "orders", label: "Orders", icon: ShoppingBag },
  { id: "receipt", label: "Receipt", icon: ReceiptText },
  { id: "inventory", label: "Inventory", icon: ClipboardList },
  { id: "staff", label: "Staff", icon: Users },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "appearance", label: "Appearance", icon: Palette },
];

// Helper Components
const Field = ({
  label,
  name,
  value,
  onChange,
  type = "text",
  placeholder,
}) => (
  <label className="block">
    <span className="mb-1 block text-sm font-semibold text-slate-700">
      {label}
    </span>
    <input
      type={type}
      name={name}
      value={value ?? ""}
      onChange={onChange}
      placeholder={placeholder}
      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
    />
  </label>
);

const ToggleField = ({ label, description, name, checked, onChange }) => (
  <label className="flex cursor-pointer items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 hover:bg-slate-50 transition-colors">
    <div>
      <span className="block text-sm font-bold text-slate-800">{label}</span>
      {description && (
        <span className="mt-1 block text-xs text-slate-500">{description}</span>
      )}
    </div>
    <input
      type="checkbox"
      name={name}
      checked={Boolean(checked)}
      onChange={onChange}
      className="mt-1 h-5 w-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
    />
  </label>
);

const SectionCard = ({ title, children }) => (
  <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6 animate-in fade-in duration-300">
    <h2 className="text-lg font-bold text-slate-900 border-b pb-4">{title}</h2>
    {children}
  </div>
);

// Placeholder for StaffList until created
const StaffList = () => (
  <SectionCard title="Staff Management">
    <div className="text-center py-12">
      <Users
        className="mx-auto text-slate-300 mb-4"
        size={48}
      />
      <p className="text-slate-500 font-medium">
        Staff management features coming soon.
      </p>
    </div>
  </SectionCard>
);

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get("/settings/");
        setSettings(res.data);
      } catch (err) {
        setError("Failed to load settings.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    setIsDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const payload = {
        ...settings,
        tax_percentage: parseFloat(settings.tax_percentage) || 0,
        service_charge_percentage:
          parseFloat(settings.service_charge_percentage) || 0,
        items_per_page: parseInt(settings.items_per_page) || 20,
      };
      const res = await api.patch("/settings/", payload);
      setSettings(res.data);
      setMessage("Settings updated successfully!");
      setIsDirty(false);
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Validation Error. Please check your inputs."
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setSaving(false);
    }
  };

  if (loading)
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="animate-spin text-indigo-600" />
      </div>
    );

  return (
    <div className="min-h-screen bg-slate-50 p-6 pb-24">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight">
              System Settings
            </h1>
            <p className="text-slate-500">
              Manage your restaurant configuration and preferences.
            </p>
          </div>
          {/* Save button only visible/useful for standard settings tabs */}
          {!["register", "staff"].includes(activeTab) && (
            <button
              onClick={handleSave}
              disabled={!isDirty || saving}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all shadow-lg ${
                isDirty
                  ? "bg-indigo-600 text-white hover:bg-indigo-700 scale-105"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed"
              }`}>
              {saving ? (
                <Loader2
                  className="animate-spin"
                  size={18}
                />
              ) : (
                <Save size={18} />
              )}
              {saving ? "Saving..." : "Save Changes"}
            </button>
          )}
        </header>

        {message && (
          <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl flex items-center gap-2 font-bold">
            <CheckCircle2 size={20} /> {message}
          </div>
        )}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-center gap-2 font-bold">
            <AlertCircle size={20} /> {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <nav className="space-y-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold transition-all ${
                  activeTab === tab.id
                    ? "bg-white text-indigo-600 shadow-sm border border-slate-200"
                    : "text-slate-500 hover:bg-slate-100"
                }`}>
                <tab.icon size={20} /> {tab.label}
              </button>
            ))}
          </nav>

          <div className="lg:col-span-3">
            {activeTab === "register" && <SessionManagement />}

            {activeTab === "staff" && <StaffList />}

            {activeTab === "general" && (
              <SectionCard title="Restaurant Identity">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Field
                    label="Restaurant Name"
                    name="restaurant_display_name"
                    value={settings.restaurant_display_name}
                    onChange={handleChange}
                  />
                  <Field
                    label="Currency Symbol"
                    name="currency_symbol"
                    value={settings.currency_symbol}
                    onChange={handleChange}
                  />
                  <Field
                    label="Business Email"
                    name="business_email"
                    value={settings.business_email}
                    onChange={handleChange}
                  />
                  <Field
                    label="Business Phone"
                    name="business_phone"
                    value={settings.business_phone}
                    onChange={handleChange}
                  />
                </div>
              </SectionCard>
            )}

            {activeTab === "tax" && (
              <SectionCard title="Taxes & Fees">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Field
                    label="Tax (%)"
                    name="tax_percentage"
                    type="number"
                    value={settings.tax_percentage}
                    onChange={handleChange}
                  />
                  <Field
                    label="Service Charge (%)"
                    name="service_charge_percentage"
                    type="number"
                    value={settings.service_charge_percentage}
                    onChange={handleChange}
                  />
                  <div className="md:col-span-2">
                    <ToggleField
                      label="Prices Include Tax"
                      description="Enable if your menu prices already have tax calculated."
                      name="prices_include_tax"
                      checked={settings.prices_include_tax}
                      onChange={handleChange}
                    />
                  </div>
                </div>
              </SectionCard>
            )}

            {activeTab === "orders" && (
              <SectionCard title="Order Workflow">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <ToggleField
                    label="Auto-Mark Paid"
                    description="Mark orders as paid immediately upon completion."
                    name="auto_mark_order_paid"
                    checked={settings.auto_mark_order_paid}
                    onChange={handleChange}
                  />
                  <ToggleField
                    label="Split Payments"
                    description="Allow customers to pay using multiple methods."
                    name="allow_split_payments"
                    checked={settings.allow_split_payments}
                    onChange={handleChange}
                  />
                  <ToggleField
                    label="Kitchen Tickets"
                    description="Automatically print tickets for the chef."
                    name="auto_print_kitchen_tickets"
                    checked={settings.auto_print_kitchen_tickets}
                    onChange={handleChange}
                  />
                  <ToggleField
                    label="Require Table"
                    description="Dine-in orders must select a table number."
                    name="require_table_for_dine_in"
                    checked={settings.require_table_for_dine_in}
                    onChange={handleChange}
                  />
                </div>
              </SectionCard>
            )}

            {activeTab === "receipt" && (
              <SectionCard title="Receipt Customization">
                <div className="space-y-6">
                  <ToggleField
                    label="Show Logo"
                    description="Print your restaurant logo on the header."
                    name="show_logo_on_receipt"
                    checked={settings.show_logo_on_receipt}
                    onChange={handleChange}
                  />
                  <Field
                    label="Header Text"
                    name="receipt_header_text"
                    value={settings.receipt_header_text}
                    onChange={handleChange}
                    placeholder="Welcome to BEEPOS"
                  />
                  <Field
                    label="Footer Text"
                    name="receipt_footer_text"
                    value={settings.receipt_footer_text}
                    onChange={handleChange}
                    placeholder="Thank you!"
                  />
                </div>
              </SectionCard>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
