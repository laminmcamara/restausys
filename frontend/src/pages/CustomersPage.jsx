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
  Search,
  RefreshCcw,
} from "lucide-react";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

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

  // Updated field names to match common Django Serializer patterns
  const [form, setForm] = useState({
    full_name: "",
    phone_number: "",
    email: "",
    address: "",
    notes: "",
  });

  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");

  const CUSTOMER_API = `${API_BASE_URL}/manager/customers/`;

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(CUSTOMER_API, {
        headers: getAuthHeaders(),
      });
      if (!res.ok)
        throw new Error(`Failed to load customers (Error ${res.status})`);
      const data = await res.json();
      // Handle DRF pagination
      setCustomers(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setError(err.message || "Unable to connect to backend.");
    } finally {
      setLoading(false);
    }
  }, [CUSTOMER_API]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  function openCreate() {
    setForm({
      full_name: "",
      phone_number: "",
      email: "",
      address: "",
      notes: "",
    });
    setEditingId(null);
    setFieldErrors({});
    setShowForm(true);
  }

  function openEdit(customer) {
    setForm({
      full_name: customer.full_name || "",
      phone_number: customer.phone_number || "",
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
    setError("");

    const url = editingId ? `${CUSTOMER_API}${editingId}/` : CUSTOMER_API;
    const method = editingId ? "PATCH" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(form),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        if (res.status === 400 && data) {
          setFieldErrors(data);
        } else {
          setError(data?.detail || "An unexpected error occurred.");
        }
        return;
      }

      setShowForm(false);
      fetchCustomers();
    } catch {
      setError("Network error. Please check your connection.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this customer?")) return;
    try {
      const res = await fetch(`${CUSTOMER_API}${id}/`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (res.ok) fetchCustomers();
      else throw new Error("Delete failed");
    } catch (err) {
      setError(err.message);
    }
  }

  const filtered = customers.filter((c) => {
    const q = search.toLowerCase();
    return (
      c.full_name?.toLowerCase().includes(q) ||
      c.phone_number?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            Customers
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage restaurant loyalty and contacts.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-xl bg-amber-400 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-md shadow-amber-500/20 transition hover:bg-amber-300">
          <Plus size={18} />
          Add Customer
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 flex items-center gap-2">
          <X
            size={16}
            className="bg-red-200 rounded-full p-0.5"
          />
          {error}
        </div>
      )}

      {/* Search & Refresh */}
      <div className="mb-6 flex gap-2">
        <div className="relative flex-1 max-w-md">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            size={18}
          />
          <input
            type="text"
            placeholder="Search customers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 py-2.5 text-sm focus:border-amber-500 focus:ring-4 focus:ring-amber-50 transition-all outline-none"
          />
        </div>
        <button
          onClick={fetchCustomers}
          className="p-2.5 text-slate-400 hover:bg-slate-100 rounded-xl transition">
          <RefreshCcw
            size={20}
            className={loading ? "animate-spin" : ""}
          />
        </button>
      </div>

      {/* Modal Form */}
      {showForm && (
        <div className="mb-8 rounded-3xl border-2 border-slate-100 bg-white p-8 shadow-xl animate-in slide-in-from-top-4">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-black text-slate-900">
              {editingId ? "Edit Profile" : "New Customer"}
            </h2>
            <button
              onClick={() => setShowForm(false)}
              className="text-slate-400 hover:text-slate-900 transition">
              <X size={24} />
            </button>
          </div>

          <form
            onSubmit={handleSubmit}
            className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest">
                Full Name
              </label>
              <input
                type="text"
                required
                value={form.full_name}
                onChange={(e) =>
                  setForm({ ...form, full_name: e.target.value })
                }
                className={`w-full rounded-xl border-2 p-3 text-sm outline-none transition-all ${
                  fieldErrors.full_name
                    ? "border-red-200 bg-red-50"
                    : "border-slate-50 bg-slate-50 focus:border-amber-400 focus:bg-white"
                }`}
              />
              {fieldErrors.full_name && (
                <p className="text-[10px] font-bold text-red-500 uppercase">
                  {fieldErrors.full_name[0]}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest">
                Phone Number
              </label>
              <input
                type="tel"
                value={form.phone_number}
                onChange={(e) =>
                  setForm({ ...form, phone_number: e.target.value })
                }
                className="w-full rounded-xl border-2 border-slate-50 bg-slate-50 p-3 text-sm outline-none focus:border-amber-400 focus:bg-white transition-all"
              />
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest">
                Email Address
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-xl border-2 border-slate-50 bg-slate-50 p-3 text-sm outline-none focus:border-amber-400 focus:bg-white transition-all"
              />
            </div>

            <div className="sm:col-span-2 flex gap-3 pt-2">
              <button
                type="submit"
                disabled={saving}
                className="flex-1 rounded-2xl bg-slate-900 py-4 text-sm font-black text-white shadow-lg transition hover:bg-black disabled:opacity-50">
                {saving
                  ? "Processing..."
                  : editingId
                  ? "Update Customer"
                  : "Create Customer"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-2xl border-2 border-slate-100 px-8 py-4 text-sm font-bold text-slate-600 hover:bg-slate-50 transition">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Customer Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-300">
          <RefreshCcw
            size={40}
            className="animate-spin mb-4"
          />
          <p className="font-bold uppercase tracking-widest text-xs">
            Syncing Directory
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-3xl border-2 border-dashed border-slate-100">
          <Users
            size={48}
            className="mx-auto text-slate-200 mb-4"
          />
          <p className="text-slate-500 font-bold">
            {search ? "No matches found." : "Your customer list is empty."}
          </p>
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c) => (
            <div
              key={c.id}
              className="group relative rounded-3xl border border-slate-200 bg-white p-6 transition-all hover:border-amber-200 hover:shadow-xl hover:-translate-y-1">
              <div className="flex items-start justify-between mb-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-50 font-black text-amber-600 text-xl">
                  {c.full_name?.charAt(0).toUpperCase() || "?"}
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => openEdit(c)}
                    className="rounded-lg p-2 text-slate-400 hover:bg-amber-50 hover:text-amber-600 transition">
                    <Pencil size={18} />
                  </button>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 transition">
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>

              <h3 className="text-lg font-black text-slate-900 mb-1">
                {c.full_name || "Unnamed Customer"}
              </h3>

              <div className="space-y-2 mt-4">
                {c.phone_number && (
                  <div className="flex items-center gap-3 text-sm font-bold text-slate-500">
                    <Phone
                      size={14}
                      className="text-slate-300"
                    />
                    <span>{c.phone_number}</span>
                  </div>
                )}
                {c.email && (
                  <div className="flex items-center gap-3 text-sm font-medium text-slate-400 truncate">
                    <Mail
                      size={14}
                      className="text-slate-300"
                    />
                    <span>{c.email}</span>
                  </div>
                )}
              </div>

              {c.total_spent > 0 && (
                <div className="mt-6 pt-4 border-t border-slate-50 flex items-center justify-between">
                  <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                    Total Spent
                  </span>
                  <span className="text-sm font-black text-emerald-600">
                    ${parseFloat(c.total_spent).toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
