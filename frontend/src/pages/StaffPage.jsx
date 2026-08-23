import { useState, useEffect, useCallback } from "react";
import {
  UserCog,
  Plus,
  Trash2,
  Pencil,
  X,
  ShieldCheck,
  RefreshCcw,
  CheckSquare,
  Square,
} from "lucide-react";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

const PERMISSION_FIELDS = [
  { id: "can_manage_staff", label: "Manage Staff" },
  { id: "can_access_pos", label: "Access POS" },
  { id: "can_access_kitchen", label: "Access Kitchen" },
  { id: "can_view_dashboard", label: "View Dashboard" },
  { id: "can_manage_products", label: "Manage Products" },
  { id: "can_manage_tables", label: "Manage Tables" },
];

export default function StaffPage() {
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    role: "STAFF",
    is_active: true,
    can_manage_staff: false,
    can_access_pos: true,
    can_access_kitchen: false,
    can_access_public_display: false,
    can_view_dashboard: false,
    can_view_reports: false,
    can_manage_products: false,
    can_manage_tables: false,
    can_manage_settings: false,
  });

  const STAFF_API = `${API_BASE_URL}/api/v1/manager/staff/`;

  const fetchStaff = useCallback(async () => {
    setLoading(true);
    try {
      const token =
        localStorage.getItem("accessToken") || localStorage.getItem("access");
      const res = await fetch(STAFF_API, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setStaff(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setError("Failed to fetch staff.");
    } finally {
      setLoading(false);
    }
  }, [STAFF_API]);

  useEffect(() => {
    fetchStaff();
  }, [fetchStaff]);

  const togglePermission = (field) => {
    setForm((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  async function handleSubmit(e) {
    e.preventDefault();
    const token =
      localStorage.getItem("accessToken") || localStorage.getItem("access");
    const url = editingId ? `${STAFF_API}${editingId}/` : STAFF_API;

    try {
      const res = await fetch(url, {
        method: editingId ? "PATCH" : "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(JSON.stringify(data));
      }

      setShowForm(false);
      fetchStaff();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-black text-slate-900">Staff Management</h1>
        <button
          onClick={() => {
            setEditingId(null);
            setShowForm(true);
          }}
          className="bg-amber-400 px-6 py-2.5 rounded-xl font-bold shadow-lg shadow-amber-200 hover:bg-amber-300 transition">
          + Add Staff Member
        </button>
      </div>

      {showForm && (
        <div className="bg-white border-2 border-slate-100 rounded-3xl p-8 mb-8 shadow-xl animate-in slide-in-from-top-4 duration-300">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">
              {editingId ? "Edit Staff Member" : "Create New Staff Member"}
            </h2>
            <button
              onClick={() => setShowForm(false)}
              className="p-2 hover:bg-slate-100 rounded-full">
              <X />
            </button>
          </div>

          <form
            onSubmit={handleSubmit}
            className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-500 uppercase">
                  Username
                </label>
                <input
                  className="w-full border-2 border-slate-100 p-3 rounded-xl outline-none focus:border-amber-400"
                  value={form.username}
                  onChange={(e) =>
                    setForm({ ...form, username: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-500 uppercase">
                  Email
                </label>
                <input
                  type="email"
                  className="w-full border-2 border-slate-100 p-3 rounded-xl outline-none focus:border-amber-400"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-500 uppercase">
                  Password
                </label>
                <input
                  type="password"
                  className="w-full border-2 border-slate-100 p-3 rounded-xl outline-none focus:border-amber-400"
                  value={form.password}
                  onChange={(e) =>
                    setForm({ ...form, password: e.target.value })
                  }
                  required={!editingId}
                />
              </div>
            </div>

            <div className="bg-slate-50 p-6 rounded-2xl">
              <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
                <ShieldCheck
                  size={18}
                  className="text-amber-500"
                />
                Permissions & Access
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {PERMISSION_FIELDS.map((field) => (
                  <button
                    key={field.id}
                    type="button"
                    onClick={() => togglePermission(field.id)}
                    className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${
                      form[field.id]
                        ? "bg-white border-amber-400 text-amber-900 shadow-sm"
                        : "bg-transparent border-slate-200 text-slate-500"
                    }`}>
                    {form[field.id] ? (
                      <CheckSquare className="text-amber-500" />
                    ) : (
                      <Square />
                    )}
                    <span className="text-sm font-bold">{field.label}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                className="flex-1 bg-slate-900 text-white py-4 rounded-2xl font-bold hover:bg-black transition shadow-lg">
                {editingId ? "Update Staff Member" : "Create Staff Member"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-8 bg-slate-100 py-4 rounded-2xl font-bold">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Staff Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead className="bg-slate-50/50 border-b border-slate-100">
            <tr>
              <th className="px-6 py-4 text-xs font-black text-slate-400 uppercase">
                Staff Member
              </th>
              <th className="px-6 py-4 text-xs font-black text-slate-400 uppercase">
                Role
              </th>
              <th className="px-6 py-4 text-xs font-black text-slate-400 uppercase">
                Permissions
              </th>
              <th className="px-6 py-4 text-right"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {staff.map((member) => (
              <tr
                key={member.id}
                className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="font-bold text-slate-900">
                    {member.username}
                  </div>
                  <div className="text-xs text-slate-400">{member.email}</div>
                </td>
                <td className="px-6 py-4">
                  <span className="px-3 py-1 bg-slate-100 rounded-full text-[10px] font-black text-slate-600 uppercase">
                    {member.role}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex gap-1 flex-wrap">
                    {member.can_access_pos && (
                      <span
                        className="w-2 h-2 rounded-full bg-emerald-400"
                        title="POS Access"></span>
                    )}
                    {member.can_manage_staff && (
                      <span
                        className="w-2 h-2 rounded-full bg-amber-400"
                        title="Manager"></span>
                    )}
                    {member.can_access_kitchen && (
                      <span
                        className="w-2 h-2 rounded-full bg-blue-400"
                        title="Kitchen"></span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => {
                      setEditingId(member.id);
                      setForm(member);
                      setShowForm(true);
                    }}
                    className="p-2 text-slate-400 hover:text-amber-500 transition">
                    <Pencil size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
