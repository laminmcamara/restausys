import { useState, useEffect, useCallback } from "react";
import { UserCog, Plus, Trash2, Pencil, X, ShieldCheck } from "lucide-react";

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

const ROLES = [
  { value: "manager", label: "Manager" },
  { value: "waiter", label: "Waiter" },
  { value: "cook", label: "Cook" },
  { value: "cashier", label: "Cashier" },
];

function roleLabel(value) {
  return ROLES.find((r) => r.value === value)?.label || value;
}

function roleBadgeColor(role) {
  const colors = {
    manager: "bg-amber-100 text-amber-800",
    waiter: "bg-blue-100 text-blue-800",
    cook: "bg-orange-100 text-orange-800",
    cashier: "bg-emerald-100 text-emerald-800",
  };
  return colors[role] || "bg-slate-100 text-slate-700";
}

export default function StaffPage() {
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    role: "waiter",
    password: "",
    is_active: true,
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const fetchStaff = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/manager/staff/`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load staff");
      const data = await res.json();
      setStaff(Array.isArray(data) ? data : data.results || []);
    } catch {
      setError("Unable to load staff. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStaff();
  }, [fetchStaff]);

  function openCreate() {
    setForm({
      full_name: "",
      email: "",
      role: "waiter",
      password: "",
      is_active: true,
    });
    setEditingId(null);
    setFieldErrors({});
    setShowForm(true);
  }

  function openEdit(member) {
    setForm({
      full_name: member.full_name || member.name || "",
      email: member.email || "",
      role: member.role || "waiter",
      password: "",
      is_active: member.is_active !== false,
    });
    setEditingId(member.id);
    setFieldErrors({});
    setShowForm(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setFieldErrors({});

    const url = editingId
      ? `${API_BASE_URL}/api/v1/manager/staff/${editingId}/`
      : `${API_BASE_URL}/api/v1/manager/staff/`;

    const method = editingId ? "PATCH" : "POST";
    const body = { ...form };
    if (editingId && !body.password) delete body.password;

    try {
      const res = await fetch(url, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
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
      fetchStaff();
    } catch {
      setError("Unable to save. Check your connection.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this staff member?")) return;
    try {
      await fetch(`${API_BASE_URL}/api/v1/manager/staff/${id}/`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      fetchStaff();
    } catch {
      setError("Unable to delete.");
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900">
            Staff Management
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage employees, roles, and access permissions.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-slate-950 shadow-md shadow-amber-500/20 transition hover:bg-amber-300">
          <Plus size={18} />
          Add Staff
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
              {editingId ? "Edit Staff Member" : "Add Staff Member"}
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
                Full Name
              </label>
              <input
                type="text"
                required
                value={form.full_name}
                onChange={(e) =>
                  setForm({ ...form, full_name: e.target.value })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="Jane Doe"
              />
              {fieldErrors.full_name && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.full_name[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Email
              </label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="jane@restaurant.com"
              />
              {fieldErrors.email && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.email[0]}
                </p>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Role
              </label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none">
                {ROLES.map((r) => (
                  <option
                    key={r.value}
                    value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">
                Password{" "}
                {editingId && (
                  <span className="text-slate-400">(leave blank to keep)</span>
                )}
              </label>
              <input
                type="password"
                required={!editingId}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-amber-500 focus:ring-2 focus:ring-amber-100 outline-none"
                placeholder="Minimum 8 characters"
              />
              {fieldErrors.password && (
                <p className="mt-1 text-xs text-red-600">
                  {fieldErrors.password[0]}
                </p>
              )}
            </div>

            <div className="sm:col-span-2 flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={form.is_active}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.checked })
                }
                className="h-4 w-4 rounded border-slate-300 text-amber-500 focus:ring-amber-400"
              />
              <label
                htmlFor="is_active"
                className="text-sm font-medium text-slate-700">
                Active account
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
                  ? "Update Staff"
                  : "Create Staff"}
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

      {/* Staff list */}
      {loading ? (
        <p className="text-center text-slate-500 py-10">Loading staff...</p>
      ) : staff.length === 0 ? (
        <div className="text-center py-16">
          <UserCog
            size={48}
            className="mx-auto text-slate-300 mb-3"
          />
          <p className="text-slate-500">No staff members yet.</p>
          <p className="text-sm text-slate-400 mt-1">
            Click "Add Staff" to create your first team member.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {staff.map((member) => (
                <tr
                  key={member.id}
                  className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold text-slate-900">
                    {member.full_name || member.name || "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {member.email || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${roleBadgeColor(
                        member.role
                      )}`}>
                      {roleLabel(member.role)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {member.is_active !== false ? (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600">
                        <ShieldCheck size={14} /> Active
                      </span>
                    ) : (
                      <span className="text-xs font-semibold text-slate-400">
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => openEdit(member)}
                        className="rounded-lg p-2 text-slate-400 hover:bg-amber-50 hover:text-amber-600 transition"
                        title="Edit">
                        <Pencil size={16} />
                      </button>
                      <button
                        onClick={() => handleDelete(member.id)}
                        className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 transition"
                        title="Delete">
                        <Trash2 size={16} />
                      </button>
                    </div>
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
