import React, { useState, useEffect, useCallback } from "react";
import api from "../services/api";
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
      const res = await api.get("/manager/inventory/");
      setItems(Array.isArray(res.data) ? res.data : res.data.results || []);
    } catch (err) {
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

    try {
      if (editingId) {
        await api.patch(`/manager/inventory/${editingId}/`, form);
      } else {
        await api.post("/manager/inventory/", form);
      }
      setShowForm(false);
      fetchItems();
    } catch (err) {
      if (err.response?.data) {
        setFieldErrors(err.response.data);
      } else {
        setError("Unable to save. Check your connection.");
      }
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
      await api.patch(`/manager/inventory/${item.id}/`, { quantity: newQty });
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
      await api.delete(`/manager/inventory/${id}/`);
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
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900">Inventory</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track ingredient stock and manage costs.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-slate-950 shadow-md transition hover:bg-amber-300">
          <Plus size={18} /> Add Item
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          {error}
        </div>
      )}

      {/* Low Stock Alert */}
      {lowStockItems.length > 0 && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle
            size={20}
            className="text-amber-600"
          />
          <p className="text-sm font-semibold text-amber-800">
            {lowStockItems.length} items at low stock.
          </p>
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h2 className="text-xl font-bold text-slate-900">
                {editingId ? "Edit Item" : "Add New Item"}
              </h2>
              <button
                onClick={() => setShowForm(false)}
                className="text-slate-400 hover:text-slate-600">
                <X size={24} />
              </button>
            </div>
            <form
              onSubmit={handleSubmit}
              className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-slate-700 mb-1">
                  Item Name
                </label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full border rounded-lg p-2"
                />
                {fieldErrors.name && (
                  <p className="text-red-500 text-xs mt-1">
                    {fieldErrors.name[0]}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1">
                  Category
                </label>
                <input
                  type="text"
                  value={form.category}
                  onChange={(e) =>
                    setForm({ ...form, category: e.target.value })
                  }
                  className="w-full border rounded-lg p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1">
                  Unit
                </label>
                <select
                  value={form.unit}
                  onChange={(e) => setForm({ ...form, unit: e.target.value })}
                  className="w-full border rounded-lg p-2">
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
                <label className="block text-sm font-bold text-slate-700 mb-1">
                  Quantity
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={form.quantity}
                  onChange={(e) =>
                    setForm({ ...form, quantity: e.target.value })
                  }
                  className="w-full border rounded-lg p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1">
                  Low Stock Threshold
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={form.low_stock_threshold}
                  onChange={(e) =>
                    setForm({ ...form, low_stock_threshold: e.target.value })
                  }
                  className="w-full border rounded-lg p-2"
                />
              </div>
              <div className="md:col-span-2 flex justify-end gap-3 mt-4">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-slate-600 font-bold">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-amber-400 px-6 py-2 rounded-lg font-bold text-slate-950 hover:bg-amber-300 disabled:opacity-50">
                  {saving
                    ? "Saving..."
                    : editingId
                    ? "Update Item"
                    : "Create Item"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="text-center py-10">Loading...</div>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b font-bold text-slate-600 uppercase text-xs">
              <tr>
                <th className="p-4">Item</th>
                <th className="p-4">Stock</th>
                <th className="p-4">Category</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-slate-50">
                  <td className="p-4 font-bold text-slate-900">{item.name}</td>
                  <td className="p-4">
                    {adjustingId === item.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          className="w-16 border rounded p-1"
                          value={adjustQty}
                          onChange={(e) => setAdjustQty(e.target.value)}
                        />
                        <button
                          onClick={() => handleAdjust(item, "add")}
                          className="text-emerald-600">
                          <TrendingUp size={16} />
                        </button>
                        <button
                          onClick={() => handleAdjust(item, "subtract")}
                          className="text-orange-600">
                          <Minus size={16} />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setAdjustingId(item.id)}
                        className="hover:text-amber-600 font-mono">
                        {item.quantity} {item.unit}
                      </button>
                    )}
                  </td>
                  <td className="p-4 text-slate-500">{item.category}</td>
                  <td className="p-4 text-right">
                    <button
                      onClick={() => openEdit(item)}
                      className="p-2 text-slate-400 hover:text-amber-600">
                      <Pencil size={18} />
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="p-2 text-slate-400 hover:text-red-600">
                      <Trash2 size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
