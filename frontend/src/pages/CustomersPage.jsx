import { useState, useEffect, useCallback } from "react";
import {
  Users,
  Plus,
  Trash2,
  Pencil,
  X,
  Phone,
  Mail,
  ShoppingBag,
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

export default function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    address: "",
    notes: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/manager/customers/`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load customers");
      const data = await res.json();
      setCustomers(Array.isArray(data) ? data : data.results || []);
    } catch {
      setError("Unable to load customers. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  function openCreate() {
    setForm({ name: "", phone: "", email: "", address: "", notes: "" });
    setEditingId(null);
    setFieldErrors({});
    setShowForm(true);
  }

  function openEdit(customer) {
    setForm({
      name: customer.name || "",
      phone: customer.phone || "",
      email: customer.email || "",
      address: customer.address || "",
      notes: customer.notes || "",
    });
    setEditingId(customer.id);
    setFieldErrors({});
    setShowForm(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setFieldErrors({});

    const url = editingId
      ? `${API_BASE_URL}/api/v1/manager/customers/${editingId}/`
      : `${API_BASE_URL}/api/v1/manager/customers/`;

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
      fetchCustomers();
    } catch {
      setError("Unable to save. Check your connection.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this customer?")) return;
    try {
      await fetch(`${API_BASE_URL}/api/v1/manager/customers/${id}/`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      fetchCustomers();
    } catch {
      setError("Unable to delete.");
    }
  }

  const filtered = customers.filter((c) => {
    const q = search.toLowerCase();
    return (
      c.name?.toLowerCase().includes(q) ||
      c.phone?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q)
    );
  });

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900">Customers</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track customer info, contact details, and order history.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-slate-950 shadow-md shadow-amber-500/20 transition hover:bg-amber-300">
          <Plus size={18} />
          Add Customer
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          {error}
        </div>
      )}

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search by name, phone, or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-md rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
        />
      </div>

      {/* Modal */}
      {showForm && (
        <div className="mb-6 rounded-2xl border border-slate-200 bg-slate-50 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">
              {editingId ? "Edit Customer" : "Add Customer"}
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
                placeholder="John Smith"
              />
              {fieldErrors.name && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.name[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Phone
              </label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="+852 1234 5678"
              />
              {fieldErrors.phone && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.phone[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Email
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="john@example.com"
              />
              {fieldErrors.email && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.email[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Address
              </label>
              <input
                type="text"
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="123 Main St, Hong Kong"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Notes
              </label>
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={2}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="Allergies, preferences, etc."
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
                  ? "Update Customer"
                  : "Create Customer"}
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

      {/* Customer cards */}
      {loading ? (
        <p className="text-center text-slate-500 py-10">Loading customers...</p>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <Users
            size={48}
            className="mx-auto text-slate-300 mb-3"
          />
          <p className="text-slate-500">
            {search ? "No customers match your search." : "No customers yet."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c) => (
            <div
              key={c.id}
              className="rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-amber-300 hover:shadow-md">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-amber-100 font-black text-amber-700">
                    {c.name?.charAt(0).toUpperCase() || "?"}
                  </div>
                  <div>
                    <p className="font-bold text-slate-900">
                      {c.name || "Unknown"}
                    </p>
                    {c.total_orders != null && (
                      <p className="text-xs text-slate-400">
                        {c.total_orders} orders
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => openEdit(c)}
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-amber-50 hover:text-amber-600 transition">
                    <Pencil size={15} />
                  </button>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 transition">
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              <div className="mt-4 space-y-2 text-sm text-slate-600">
                {c.phone && (
                  <div className="flex items-center gap-2">
                    <Phone
                      size={14}
                      className="text-slate-400"
                    />
                    <span>{c.phone}</span>
                  </div>
                )}
                {c.email && (
                  <div className="flex items-center gap-2">
                    <Mail
                      size={14}
                      className="text-slate-400"
                    />
                    <span className="truncate">{c.email}</span>
                  </div>
                )}
                {c.total_spent != null && (
                  <div className="flex items-center gap-2 pt-1">
                    <ShoppingBag
                      size={14}
                      className="text-slate-400"
                    />
                    <span className="font-bold text-slate-900">
                      ${parseFloat(c.total_spent).toFixed(2)} total spent
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
