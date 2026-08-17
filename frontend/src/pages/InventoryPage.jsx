import { useState, useEffect, useCallback } from "react";
import {
  Boxes,
  Plus,
  Trash2,
  Pencil,
  X,
  AlertTriangle,
  Minus,
  TrendingUp,
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

const UNITS = ["kg", "g", "liter", "ml", "piece", "box", "pack", "bottle"];

export default function InventoryPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    name: "",
    category: "",
    quantity: "",
    unit: "piece",
    low_stock_threshold: "",
    cost_per_unit: "",
    supplier: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [adjustingId, setAdjustingId] = useState(null);
  const [adjustQty, setAdjustQty] = useState("");

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/manager/inventory/`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load inventory");
      const data = await res.json();
      setItems(Array.isArray(data) ? data : data.results || []);
    } catch {
      setError("Unable to load inventory. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  function openCreate() {
    setForm({
      name: "",
      category: "",
      quantity: "",
      unit: "piece",
      low_stock_threshold: "",
      cost_per_unit: "",
      supplier: "",
    });
    setEditingId(null);
    setFieldErrors({});
    setShowForm(true);
  }

  function openEdit(item) {
    setForm({
      name: item.name || "",
      category: item.category || "",
      quantity: item.quantity?.toString() || "",
      unit: item.unit || "piece",
      low_stock_threshold: item.low_stock_threshold?.toString() || "",
      cost_per_unit: item.cost_per_unit?.toString() || "",
      supplier: item.supplier || "",
    });
    setEditingId(item.id);
    setFieldErrors({});
    setShowForm(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setFieldErrors({});

    const url = editingId
      ? `${API_BASE_URL}/api/v1/manager/inventory/${editingId}/`
      : `${API_BASE_URL}/api/v1/manager/inventory/`;

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
      fetchItems();
    } catch {
      setError("Unable to save. Check your connection.");
    } finally {
      setSaving(false);
    }
  }

  async function handleAdjust(item, direction) {
    const qty = parseFloat(adjustQty);
    if (!qty || qty <= 0) return;

    const newQty =
      direction === "add"
        ? parseFloat(item.quantity || 0) + qty
        : parseFloat(item.quantity || 0) - qty;

    try {
      await fetch(`${API_BASE_URL}/api/v1/manager/inventory/${item.id}/`, {
        method: "PATCH",
        headers: getAuthHeaders(),
        body: JSON.stringify({ quantity: newQty }),
      });
      setAdjustingId(null);
      setAdjustQty("");
      fetchItems();
    } catch {
      setError("Unable to adjust stock.");
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this inventory item?")) return;
    try {
      await fetch(`${API_BASE_URL}/api/v1/manager/inventory/${id}/`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      fetchItems();
    } catch {
      setError("Unable to delete.");
    }
  }

  const lowStockItems = items.filter(
    (i) =>
      i.low_stock_threshold != null &&
      parseFloat(i.quantity || 0) <= parseFloat(i.low_stock_threshold)
  );

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900">Inventory</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track ingredient stock, monitor low levels, and manage supplier
            costs.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-slate-950 shadow-md shadow-amber-500/20 transition hover:bg-amber-300">
          <Plus size={18} />
          Add Item
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          {error}
        </div>
      )}

      {/* Low stock alert */}
      {lowStockItems.length > 0 && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle
            size={20}
            className="text-amber-600"
          />
          <p className="text-sm font-semibold text-amber-800">
            {lowStockItems.length} item{lowStockItems.length > 1 ? "s" : ""} at
            or below low stock threshold.
          </p>
        </div>
      )}

      {/* Modal */}
      {showForm && (
        <div className="mb-6 rounded-2xl border border-slate-200 bg-slate-50 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">
              {editingId ? "Edit Inventory Item" : "Add Inventory Item"}
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
                Item Name
              </label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="Chicken Breast"
              />
              {fieldErrors.name && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.name[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Category
              </label>
              <input
                type="text"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="Meat, Produce, Dry Goods"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Quantity
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="0"
              />
              {fieldErrors.quantity && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.quantity[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Unit
              </label>
              <select
                value={form.unit}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none">
                {UNITS.map((u) => (
                  <option
                    key={u}
                    value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Low Stock Threshold
              </label>
              <input
                type="number"
                step="0.01"
                value={form.low_stock_threshold}
                onChange={(e) =>
                  setForm({ ...form, low_stock_threshold: e.target.value })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="Alert when below"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Cost per Unit ($)
              </label>
              <input
                type="number"
                step="0.01"
                value={form.cost_per_unit}
                onChange={(e) =>
                  setForm({ ...form, cost_per_unit: e.target.value })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="0.00"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Supplier
              </label>
              <input
                type="text"
                value={form.supplier}
                onChange={(e) => setForm({ ...form, supplier: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="Supplier name"
              />
            </div>

            <div className="sm:col-span-2 flex gap-3">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-amber-400 px-5 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-amber-300 disabled:opacity-60">
                {saving
                  ? "Saving..."
                  : editingId
                  ? "Update Item"
                  : "Create Item"}
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

      {/* Inventory table */}
      {loading ? (
        <p className="text-center text-slate-500 py-10">Loading inventory...</p>
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <Boxes
            size={48}
            className="mx-auto text-slate-300 mb-3"
          />
          <p className="text-slate-500">No inventory items yet.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                <th className="px-4 py-3">Item</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Quantity</th>
                <th className="px-4 py-3">Cost/Unit</th>
                <th className="px-4 py-3">Supplier</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => {
                const isLow =
                  item.low_stock_threshold != null &&
                  parseFloat(item.quantity || 0) <=
                    parseFloat(item.low_stock_threshold);
                return (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      {item.name}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {item.category || "—"}
                    </td>
                    <td className="px-4 py-3">
                      {adjustingId === item.id ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            step="0.01"
                            value={adjustQty}
                            onChange={(e) => setAdjustQty(e.target.value)}
                            placeholder="qty"
                            className="w-20 rounded border border-slate-300 px-2 py-1 text-xs"
                          />
                          <button
                            onClick={() => handleAdjust(item, "add")}
                            className="rounded bg-emerald-100 p-1 text-emerald-600 hover:bg-emerald-200"
                            title="Add stock">
                            <TrendingUp size={14} />
                          </button>
                          <button
                            onClick={() => handleAdjust(item, "subtract")}
                            className="rounded bg-orange-100 p-1 text-orange-600 hover:bg-orange-200"
                            title="Remove stock">
                            <Minus size={14} />
                          </button>
                          <button
                            onClick={() => {
                              setAdjustingId(null);
                              setAdjustQty("");
                            }}
                            className="text-slate-400 hover:text-slate-700">
                            <X size={14} />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setAdjustingId(item.id)}
                          className="font-bold text-slate-900 hover:text-amber-600 transition">
                          {item.quantity} {item.unit}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {item.cost_per_unit
                        ? `$${parseFloat(item.cost_per_unit).toFixed(2)}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {item.supplier || "—"}
                    </td>
                    <td className="px-4 py-3">
                      {isLow ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-700">
                          <AlertTriangle size={12} /> Low
                        </span>
                      ) : (
                        <span className="inline-block rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-700">
                          OK
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => openEdit(item)}
                          className="rounded-lg p-2 text-slate-400 hover:bg-amber-50 hover:text-amber-600 transition"
                          title="Edit">
                          <Pencil size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 transition"
                          title="Delete">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
