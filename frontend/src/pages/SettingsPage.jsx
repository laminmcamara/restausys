import { useEffect, useMemo, useState } from "react";
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
} from "lucide-react";
import api from "../services/api";

const tabs = [
  { id: "general", label: "General", icon: Store },
  { id: "tax", label: "Tax & Charges", icon: CreditCard },
  { id: "orders", label: "Orders", icon: ShoppingBag },
  { id: "receipt", label: "Receipt", icon: ReceiptText },
  { id: "inventory", label: "Inventory", icon: ClipboardList },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "staff", label: "Staff & Roles", icon: Users },
];

const defaultSettings = {
  restaurant_display_name: "",
  business_email: "",
  business_phone: "",
  business_address: "",
  currency_symbol: "$",
  timezone: "UTC",

  tax_percentage: "0.00",
  service_charge_percentage: "0.00",
  prices_include_tax: false,

  auto_mark_order_paid: false,
  allow_split_payments: true,
  allow_table_merge: true,
  default_order_type: "DINE_IN",
  require_table_for_dine_in: true,
  auto_print_kitchen_tickets: true,

  show_logo_on_receipt: true,
  receipt_header_text: "",
  receipt_footer_text: "",

  stock_alerts_enabled: true,
  auto_deduct_inventory: true,

  email_notifications_enabled: true,
  send_daily_sales_report: false,
  low_stock_email_alerts: true,
  notify_on_new_order: true,

  default_theme: "system",
  items_per_page: 20,
};

function Field({ label, name, value, onChange, type = "text", placeholder }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">
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
}

function TextareaField({ label, name, value, onChange, placeholder }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </span>
      <textarea
        name={name}
        value={value ?? ""}
        onChange={onChange}
        placeholder={placeholder}
        rows={3}
        className="w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
      />
    </label>
  );
}

function SelectField({ label, name, value, onChange, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </span>
      <select
        name={name}
        value={value ?? ""}
        onChange={onChange}
        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        {children}
      </select>
    </label>
  );
}

function ToggleField({ label, description, name, checked, onChange }) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4">
      <div>
        <span className="block text-sm font-semibold text-slate-800">
          {label}
        </span>
        {description && (
          <span className="mt-1 block text-xs text-slate-500">
            {description}
          </span>
        )}
      </div>

      <input
        type="checkbox"
        name={name}
        checked={Boolean(checked)}
        onChange={onChange}
        className="mt-1 h-5 w-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
      />
    </label>
  );
}

function SectionCard({ title, description, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="text-lg font-bold text-slate-900">{title}</h2>
        {description && (
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");
  const [settings, setSettings] = useState(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const activeTabInfo = useMemo(
    () => tabs.find((tab) => tab.id === activeTab),
    [activeTab]
  );

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await api.get("/v1/settings/");
      setSettings({
        ...defaultSettings,
        ...response.data,
      });
    } catch (err) {
      console.error(err);
      setError(
        err?.response?.data?.detail ||
          "Could not load settings. Please check your connection or permissions."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;

    setSettings((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError("");
      setMessage("");

      const payload = {
        restaurant_display_name: settings.restaurant_display_name,
        business_email: settings.business_email || null,
        business_phone: settings.business_phone || null,
        business_address: settings.business_address || null,
        currency_symbol: settings.currency_symbol,
        timezone: settings.timezone,

        tax_percentage: settings.tax_percentage,
        service_charge_percentage: settings.service_charge_percentage,
        prices_include_tax: settings.prices_include_tax,

        auto_mark_order_paid: settings.auto_mark_order_paid,
        allow_split_payments: settings.allow_split_payments,
        allow_table_merge: settings.allow_table_merge,
        default_order_type: settings.default_order_type,
        require_table_for_dine_in: settings.require_table_for_dine_in,
        auto_print_kitchen_tickets: settings.auto_print_kitchen_tickets,

        show_logo_on_receipt: settings.show_logo_on_receipt,
        receipt_header_text: settings.receipt_header_text || null,
        receipt_footer_text: settings.receipt_footer_text || null,

        stock_alerts_enabled: settings.stock_alerts_enabled,
        auto_deduct_inventory: settings.auto_deduct_inventory,

        email_notifications_enabled: settings.email_notifications_enabled,
        send_daily_sales_report: settings.send_daily_sales_report,
        low_stock_email_alerts: settings.low_stock_email_alerts,
        notify_on_new_order: settings.notify_on_new_order,

        default_theme: settings.default_theme,
        items_per_page: settings.items_per_page,
      };

      const response = await api.patch("/settings/", payload);

      setSettings({
        ...defaultSettings,
        ...response.data,
      });

      setMessage("Settings saved successfully.");
    } catch (err) {
      console.error(err);
      setError(
        err?.response?.data?.detail ||
          "Could not save settings. Please check the form and try again."
      );
    } finally {
      setSaving(false);
    }
  };

  const renderTabContent = () => {
    if (activeTab === "general") {
      return (
        <SectionCard
          title="General Settings"
          description="Basic restaurant identity and regional preferences.">
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Restaurant Display Name"
              name="restaurant_display_name"
              value={settings.restaurant_display_name}
              onChange={handleChange}
            />

            <Field
              label="Business Email"
              name="business_email"
              type="email"
              value={settings.business_email}
              onChange={handleChange}
            />

            <Field
              label="Business Phone"
              name="business_phone"
              value={settings.business_phone}
              onChange={handleChange}
            />

            <Field
              label="Currency Symbol"
              name="currency_symbol"
              value={settings.currency_symbol}
              onChange={handleChange}
              placeholder="$"
            />

            <Field
              label="Timezone"
              name="timezone"
              value={settings.timezone}
              onChange={handleChange}
              placeholder="UTC"
            />

            <div className="md:col-span-2">
              <TextareaField
                label="Business Address"
                name="business_address"
                value={settings.business_address}
                onChange={handleChange}
              />
            </div>
          </div>
        </SectionCard>
      );
    }

    if (activeTab === "tax") {
      return (
        <SectionCard
          title="Tax & Charges"
          description="Configure tax calculation and service charges.">
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Tax Percentage"
              name="tax_percentage"
              type="number"
              value={settings.tax_percentage}
              onChange={handleChange}
            />

            <Field
              label="Service Charge Percentage"
              name="service_charge_percentage"
              type="number"
              value={settings.service_charge_percentage}
              onChange={handleChange}
            />

            <div className="md:col-span-2">
              <ToggleField
                label="Prices Include Tax"
                description="If enabled, tax is treated as already included in menu prices."
                name="prices_include_tax"
                checked={settings.prices_include_tax}
                onChange={handleChange}
              />
            </div>
          </div>
        </SectionCard>
      );
    }

    if (activeTab === "orders") {
      return (
        <SectionCard
          title="Order Behavior"
          description="Control default order behavior and kitchen workflow.">
          <div className="grid gap-4 md:grid-cols-2">
            <SelectField
              label="Default Order Type"
              name="default_order_type"
              value={settings.default_order_type}
              onChange={handleChange}>
              <option value="DINE_IN">Dine In</option>
              <option value="TAKEAWAY">Takeaway</option>
              <option value="DELIVERY">Delivery</option>
            </SelectField>

            <ToggleField
              label="Auto Mark Order Paid"
              description="Automatically mark orders as paid when completed."
              name="auto_mark_order_paid"
              checked={settings.auto_mark_order_paid}
              onChange={handleChange}
            />

            <ToggleField
              label="Allow Split Payments"
              description="Allow one order to be paid using multiple payments."
              name="allow_split_payments"
              checked={settings.allow_split_payments}
              onChange={handleChange}
            />

            <ToggleField
              label="Allow Table Merge"
              description="Allow staff to merge tables during service."
              name="allow_table_merge"
              checked={settings.allow_table_merge}
              onChange={handleChange}
            />

            <ToggleField
              label="Require Table For Dine In"
              description="Require dine-in orders to be attached to a table."
              name="require_table_for_dine_in"
              checked={settings.require_table_for_dine_in}
              onChange={handleChange}
            />

            <ToggleField
              label="Auto Print Kitchen Tickets"
              description="Automatically create kitchen print jobs for new orders."
              name="auto_print_kitchen_tickets"
              checked={settings.auto_print_kitchen_tickets}
              onChange={handleChange}
            />
          </div>
        </SectionCard>
      );
    }

    if (activeTab === "receipt") {
      return (
        <SectionCard
          title="Receipt Settings"
          description="Customize receipt display and printed receipt text.">
          <div className="grid gap-4">
            <ToggleField
              label="Show Logo On Receipt"
              description="Display restaurant logo on customer receipts."
              name="show_logo_on_receipt"
              checked={settings.show_logo_on_receipt}
              onChange={handleChange}
            />

            <Field
              label="Receipt Header Text"
              name="receipt_header_text"
              value={settings.receipt_header_text}
              onChange={handleChange}
              placeholder="Thank you for dining with us"
            />

            <Field
              label="Receipt Footer Text"
              name="receipt_footer_text"
              value={settings.receipt_footer_text}
              onChange={handleChange}
              placeholder="Please come again"
            />
          </div>
        </SectionCard>
      );
    }

    if (activeTab === "inventory") {
      return (
        <SectionCard
          title="Inventory Settings"
          description="Configure inventory deduction and stock alerts.">
          <div className="grid gap-4 md:grid-cols-2">
            <ToggleField
              label="Stock Alerts Enabled"
              description="Show low-stock alerts in the system."
              name="stock_alerts_enabled"
              checked={settings.stock_alerts_enabled}
              onChange={handleChange}
            />

            <ToggleField
              label="Auto Deduct Inventory"
              description="Automatically reduce stock when items are sold."
              name="auto_deduct_inventory"
              checked={settings.auto_deduct_inventory}
              onChange={handleChange}
            />
          </div>
        </SectionCard>
      );
    }

    if (activeTab === "notifications") {
      return (
        <SectionCard
          title="Notification Settings"
          description="Manage email alerts and order notifications.">
          <div className="grid gap-4 md:grid-cols-2">
            <ToggleField
              label="Email Notifications Enabled"
              description="Allow the system to send email notifications."
              name="email_notifications_enabled"
              checked={settings.email_notifications_enabled}
              onChange={handleChange}
            />

            <ToggleField
              label="Send Daily Sales Report"
              description="Send a daily sales summary email."
              name="send_daily_sales_report"
              checked={settings.send_daily_sales_report}
              onChange={handleChange}
            />

            <ToggleField
              label="Low Stock Email Alerts"
              description="Send email alerts when stock is low."
              name="low_stock_email_alerts"
              checked={settings.low_stock_email_alerts}
              onChange={handleChange}
            />

            <ToggleField
              label="Notify On New Order"
              description="Notify staff when a new order is created."
              name="notify_on_new_order"
              checked={settings.notify_on_new_order}
              onChange={handleChange}
            />
          </div>
        </SectionCard>
      );
    }

    if (activeTab === "appearance") {
      return (
        <SectionCard
          title="Appearance"
          description="Configure app theme and display preferences.">
          <div className="grid gap-4 md:grid-cols-2">
            <SelectField
              label="Default Theme"
              name="default_theme"
              value={settings.default_theme}
              onChange={handleChange}>
              <option value="system">System Preference</option>
              <option value="light">Light Mode</option>
              <option value="dark">Dark Mode</option>
            </SelectField>

            <Field
              label="Items Per Page"
              name="items_per_page"
              type="number"
              value={settings.items_per_page}
              onChange={handleChange}
            />
          </div>
        </SectionCard>
      );
    }

    if (activeTab === "staff") {
      return (
        <SectionCard
          title="Staff & Roles"
          description="Manage staff accounts and role permissions.">
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
            <Users className="mx-auto mb-3 h-10 w-10 text-slate-400" />
            <h3 className="text-base font-bold text-slate-800">
              Staff management coming next
            </h3>
            <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">
              This section will connect to your existing staff/user endpoints.
              Managers and owners will be able to invite or create staff, assign
              roles, deactivate accounts, and manage access.
            </p>
          </div>
        </SectionCard>
      );
    }

    return null;
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
        <div className="flex items-center gap-3 rounded-2xl bg-white px-5 py-4 shadow-sm">
          <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
          <span className="text-sm font-medium text-slate-700">
            Loading settings...
          </span>
        </div>
      </div>
    );
  }

  const ActiveIcon = activeTabInfo?.icon || SettingsIcon;

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-indigo-600">
              <SettingsIcon className="h-4 w-4" />
              Restaurant Configuration
            </div>
            <h1 className="mt-1 text-2xl font-black text-slate-950 md:text-3xl">
              Settings
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Manage restaurant preferences, receipts, orders, notifications,
              and access.
            </p>
          </div>

          <button
            type="button"
            onClick={handleSave}
            disabled={saving || activeTab === "staff"}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>

        {message && (
          <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
            {message}
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {error}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-12">
          <aside className="lg:col-span-3">
            <div className="sticky top-4 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;

                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => {
                      setActiveTab(tab.id);
                      setMessage("");
                      setError("");
                    }}
                    className={`mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold transition last:mb-0 ${
                      isActive
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
                    }`}>
                    <Icon className="h-4 w-4" />
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </aside>

          <main className="lg:col-span-9">
            <div className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-700">
              <ActiveIcon className="h-4 w-4 text-indigo-600" />
              {activeTabInfo?.label}
            </div>

            {renderTabContent()}
          </main>
        </div>
      </div>
    </div>
  );
}
