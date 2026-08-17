import { useState, useEffect, useCallback } from "react";
import {
  Tag,
  Plus,
  Trash2,
  Pencil,
  X,
  Percent,
  DollarSign,
  Calendar,
} from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getAuthHeaders() {
  const token =
    localStorage.getItem("accessToken") || localStorage.getItem("access");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export default function DiscountsPage() {
  const [discounts, setDiscounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    name: "",
    code: "",
    discount_type: "percentage",
    value: "",
    is_active: true,
    valid_from: "",
    valid_to: "",
    min_order_amount: "",
    max_discount_amount: "",
    usage_limit: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const fetchDiscounts = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/manager/discounts/`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load discounts");
      const data = await res.json();
      setDiscounts(Array.isArray(data) ? data : data.results || []);
    } catch {
      setError("Unable to load discounts. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDiscounts();
  }, [fetchDiscounts]);

  function openCreate() {
    setForm({
      name: "",
      code: "",
      discount_type: "percentage",
      value: "",
      is_active: true,
      valid_from: "",
      valid_to: "",
      min_order_amount: "",
      max_discount_amount: "",
      usage_limit: "",
    });
    setEditingId(null);
    setFieldErrors({});
    setShowForm(true);
  }

  function openEdit(discount) {
    setForm({
      name: discount.name || "",
      code: discount.code || "",
      discount_type: discount.discount_type || "percentage",
      value: discount.value?.toString() || "",
      is_active: discount.is_active !== false,
      valid_from: discount.valid_from?.slice(0, 10) || "",
      valid_to: discount.valid_to?.slice(0, 10) || "",
      min_order_amount: discount.min_order_amount?.toString() || "",
      max_discount_amount: discount.max_discount_amount?.toString() || "",
      usage_limit: discount.usage_limit?.toString() || "",
    });
    setEditingId(discount.id);
    setFieldErrors({});
    setShowForm(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setFieldErrors({});

    const url = editingId
      ? `${API_BASE_URL}/api/v1/manager/discounts/${editingId}/`
      : `${API_BASE_URL}/api/v1/manager/discounts/`;

    const method = editingId ? "PATCH" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(form),
      });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const errors = {};
        if (data) {
          Object.entries(data).forEach(([key, val]) => {
            errors[key] = Array.isArray(val) ? val : [String(val)];
          });
        }
        setFieldErrors(errors);
        return;
      }

      setShowForm(false);
      fetchDiscounts();
    } catch {
      setError("Unable to save. Check your connection.");
    } finally {
      setSaving(false);
    }
  }

  async function handleToggle(id, currentActive) {
    try {
      await fetch(`${API_BASE_URL}/api/v1/manager/discounts/${id}/`, {
        method: "PATCH",
        headers: getAuthHeaders(),
        body: JSON.stringify({ is_active: !currentActive }),
      });
      fetchDiscounts();
    } catch {
      setError("Unable to toggle discount.");
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this discount?")) return;
    try {
      await fetch(`${API_BASE_URL}/api/v1/manager/discounts/${id}/`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      fetchDiscounts();
    } catch {
      setError("Unable to delete.");
    }
  }

  function isExpired(discount) {
    if (!discount.valid_to) return false;
    return new Date(discount.valid_to) < new Date();
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900">Discounts</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage promo codes, percentage and fixed-amount discounts.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-slate-950 shadow-md shadow-amber-500/20 transition hover:bg-amber-300">
          <Plus size={18} />
          Add Discount
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          {error}
        </div>
      )}

      {/* Modal */}
      {showForm && (
        <div className="mb-6 rounded-2xl border border-slate-200 bg-slate-50 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">
              {editingId ? "Edit Discount" : "Add Discount"}
            </h2>
            <button
              onClick={() => setShowForm(false)}
              className="text-slate-400 hover:text-slate-700">
              <X size={20} />
            </button>
          </div>

          <form
            onSubmit={handleSubmit}
            className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Name
              </label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="Happy Hour"
              />
              {fieldErrors.name && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.name[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Code
              </label>
              <input
                type="text"
                required
                value={form.code}
                onChange={(e) =>
                  setForm({ ...form, code: e.target.value.toUpperCase() })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-mono uppercase focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="HAPPY20"
              />
              {fieldErrors.code && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.code[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Discount Type
              </label>
              <select
                value={form.discount_type}
                onChange={(e) =>
                  setForm({ ...form, discount_type: e.target.value })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none">
                <option value="percentage">Percentage (%)</option>
                <option value="fixed">Fixed Amount ($)</option>
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Value {form.discount_type === "percentage" ? "(%)" : "($)"}
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                  {form.discount_type === "percentage" ? (
                    <Percent size={16} />
                  ) : (
                    <DollarSign size={16} />
                  )}
                </div>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={form.value}
                  onChange={(e) => setForm({ ...form, value: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 pl-10 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                  placeholder={
                    form.discount_type === "percentage" ? "20" : "5.00"
                  }
                />
              </div>
              {fieldErrors.value && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.value[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Valid From
              </label>
              <input
                type="date"
                value={form.valid_from}
                onChange={(e) =>
                  setForm({ ...form, valid_from: e.target.value })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Valid To
              </label>
              <input
                type="date"
                value={form.valid_to}
                onChange={(e) => setForm({ ...form, valid_to: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Min Order Amount ($)
              </label>
              <input
                type="number"
                step="0.01"
                value={form.min_order_amount}
                onChange={(e) =>
                  setForm({ ...form, min_order_amount: e.target.value })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="0.00"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Max Discount ($)
              </label>
              <input
                type="number"
                step="0.01"
                value={form.max_discount_amount}
                onChange={(e) =>
                  setForm({ ...form, max_discount_amount: e.target.value })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="No limit"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Usage Limit (0 = unlimited)
              </label>
              <input
                type="number"
                value={form.usage_limit}
                onChange={(e) =>
                  setForm({ ...form, usage_limit: e.target.value })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="100"
              />
            </div>

            <div className="sm:col-span-2 flex items-center gap-2">
              <input
                type="checkbox"
                id="disc_active"
                checked={form.is_active}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.checked })
                }
                className="h-4 w-4 rounded border-slate-300 text-amber-500 focus:ring-amber-400"
              />
              <label
                htmlFor="disc_active"
                className="text-sm font-medium text-slate-700">
                Active
              </label>
            </div>

            <div className="sm:col-span-2 flex gap-3">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-amber-400 px-5 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-amber-300 disabled:opacity-60">
                {saving
                  ? "Saving..."
                  : editingId
                  ? "Update Discount"
                  : "Create Discount"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Discount cards */}
      {loading ? (
        <p className="text-center text-slate-500 py-10">Loading discounts...</p>
      ) : discounts.length === 0 ? (
        <div className="text-center py-16">
          <Tag
            size={48}
            className="mx-auto text-slate-300 mb-3"
          />
          <p className="text-slate-500">No discounts yet.</p>
          <p className="text-sm text-slate-400 mt-1">
            Click "Add Discount" to create your first promo.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {discounts.map((d) => {
            const expired = isExpired(d);
            return (
              <div
                key={d.id}
                className={`rounded-2xl border bg-white p-5 transition hover:shadow-md ${
                  expired
                    ? "border-slate-200 opacity-60"
                    : "border-slate-200 hover:border-amber-300"
                }`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                        d.discount_type === "percentage"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-emerald-100 text-emerald-700"
                      }`}>
                      {d.discount_type === "percentage" ? (
                        <Percent size={18} />
                      ) : (
                        <DollarSign size={18} />
                      )}
                    </div>
                    <div>
                      <p className="font-bold text-slate-900">{d.name}</p>
                      <p className="font-mono text-xs text-slate-400">
                        {d.code || "—"}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => openEdit(d)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-amber-50 hover:text-amber-600 transition">
                      <Pencil size={15} />
                    </button>
                    <button
                      onClick={() => handleDelete(d.id)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 transition">
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>

                <div className="mt-4">
                  <p className="text-3xl font-black text-slate-900">
                    {d.discount_type === "percentage"
                      ? `${d.value}%`
                      : `$${parseFloat(d.value || 0).toFixed(2)}`}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {d.discount_type === "percentage"
                      ? "off total"
                      : "off total"}
                  </p>
                </div>

                <div className="mt-4 space-y-1.5 text-xs text-slate-500">
                  {d.valid_from && d.valid_to && (
                    <div className="flex items-center gap-2">
                      <Calendar
                        size={13}
                        className="text-slate-400"
                      />
                      <span>
                        {d.valid_from.slice(0, 10)} → {d.valid_to.slice(0, 10)}
                      </span>
                    </div>
                  )}
                  {d.min_order_amount && (
                    <p>
                      Min order: ${parseFloat(d.min_order_amount).toFixed(2)}
                    </p>
                  )}
                  {d.usage_limit && d.usage_limit > 0 && (
                    <p>Usage limit: {d.usage_limit}</p>
                  )}
                </div>

                <div className="mt-4 flex items-center justify-between">
                  {expired ? (
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-500">
                      Expired
                    </span>
                  ) : (
                    <button
                      onClick={() => handleToggle(d.id, d.is_active)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                        d.is_active !== false ? "bg-amber-400" : "bg-slate-300"
                      }`}>
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                          d.is_active !== false
                            ? "translate-x-6"
                            : "translate-x-1"
                        }`}
                      />
                    </button>
                  )}
                  <span
                    className={`text-xs font-bold ${
                      d.is_active !== false && !expired
                        ? "text-emerald-600"
                        : "text-slate-400"
                    }`}>
                    {d.is_active !== false && !expired ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
