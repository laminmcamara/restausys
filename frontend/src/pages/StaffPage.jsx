import { useCallback, useEffect, useMemo, useState } from "react";

import {
  CheckSquare,
  Pencil,
  Plus,
  RefreshCcw,
  ShieldCheck,
  Square,
  Trash2,
  UserCog,
  X,
} from "lucide-react";

import api from "../services/api";

const STAFF_ENDPOINT = "/manager/staff/";

const ROLE_OPTIONS = [
  {
    value: "MANAGER",
    label: "Manager",
  },
  {
    value: "SERVER",
    label: "Server",
  },
  {
    value: "COOK",
    label: "Cook",
  },
  {
    value: "CASHIER",
    label: "Cashier",
  },
  {
    value: "STAFF",
    label: "General Staff",
  },
  {
    value: "CUSTOMER",
    label: "Customer",
  },
];

const PERMISSION_FIELDS = [
  {
    id: "can_manage_staff",
    label: "Manage Staff",
  },
  {
    id: "can_access_pos",
    label: "Access POS",
  },
  {
    id: "can_access_kitchen",
    label: "Access Kitchen",
  },
  {
    id: "can_view_dashboard",
    label: "View Dashboard",
  },
  {
    id: "can_view_reports",
    label: "View Reports",
  },
  {
    id: "can_manage_products",
    label: "Manage Products",
  },
  {
    id: "can_manage_tables",
    label: "Manage Tables",
  },
  {
    id: "can_manage_settings",
    label: "Manage Settings",
  },
];

const EMPTY_FORM = {
  username: "",
  email: "",
  password: "",
  role: "STAFF",
  is_active: true,
};

function roleCapabilities(role) {
  switch (String(role || "").toUpperCase()) {
    case "MANAGER":
      return {
        can_manage_staff: true,
        can_access_pos: true,
        can_access_kitchen: true,
        can_view_dashboard: true,
        can_view_reports: true,
        can_manage_products: true,
        can_manage_tables: true,
        can_manage_settings: true,
      };

    case "CASHIER":
      return {
        can_manage_staff: false,
        can_access_pos: true,
        can_access_kitchen: false,
        can_view_dashboard: false,
        can_view_reports: false,
        can_manage_products: false,
        can_manage_tables: false,
        can_manage_settings: false,
      };

    case "SERVER":
      return {
        can_manage_staff: false,
        can_access_pos: true,
        can_access_kitchen: false,
        can_view_dashboard: false,
        can_view_reports: false,
        can_manage_products: false,
        can_manage_tables: false,
        can_manage_settings: false,
      };

    case "COOK":
      return {
        can_manage_staff: false,
        can_access_pos: false,
        can_access_kitchen: true,
        can_view_dashboard: false,
        can_view_reports: false,
        can_manage_products: false,
        can_manage_tables: false,
        can_manage_settings: false,
      };

    default:
      return {
        can_manage_staff: false,
        can_access_pos: false,
        can_access_kitchen: false,
        can_view_dashboard: false,
        can_view_reports: false,
        can_manage_products: false,
        can_manage_tables: false,
        can_manage_settings: false,
      };
  }
}

function getErrorMessage(error, fallback) {
  const data = error?.response?.data;

  if (!data) {
    return fallback;
  }

  if (typeof data === "string") {
    return data;
  }

  if (data.detail) {
    return data.detail;
  }

  if (data.message) {
    return data.message;
  }

  const firstFieldError = Object.entries(data).find(([, value]) => value);

  if (firstFieldError) {
    const [field, value] = firstFieldError;
    const message = Array.isArray(value) ? value.join(", ") : String(value);

    return `${field}: ${message}`;
  }

  return fallback;
}

function normalizeStaffMember(member) {
  return {
    ...member,
    id: member.id,
    username: member.username || "",
    email: member.email || "",
    role: String(member.role || "STAFF").toUpperCase(),
    is_active: member.is_active ?? true,
    permissions: member.permissions || roleCapabilities(member.role),
  };
}

function RoleBadge({ role }) {
  const normalized = String(role || "STAFF").toUpperCase();

  const colors = {
    MANAGER: "bg-blue-100 text-blue-800",
    SERVER: "bg-purple-100 text-purple-800",
    COOK: "bg-orange-100 text-orange-800",
    CASHIER: "bg-green-100 text-green-800",
    CUSTOMER: "bg-gray-100 text-gray-700",
    STAFF: "bg-gray-100 text-gray-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
        colors[normalized] || colors.STAFF
      }`}>
      {normalized}
    </span>
  );
}

function PermissionPreview({ capabilities }) {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {PERMISSION_FIELDS.map((permission) => {
        const enabled = Boolean(capabilities[permission.id]);

        return (
          <div
            key={permission.id}
            className="flex items-center gap-2 text-sm">
            {enabled ? (
              <CheckSquare
                size={16}
                className="text-green-600"
              />
            ) : (
              <Square
                size={16}
                className="text-gray-400"
              />
            )}

            <span className={enabled ? "text-gray-800" : "text-gray-400"}>
              {permission.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function FormField({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-gray-700">
        {label}
      </span>
      {children}
    </label>
  );
}

export default function StaffPage() {
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const capabilities = useMemo(() => roleCapabilities(form.role), [form.role]);

  const fetchStaff = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get(STAFF_ENDPOINT);

      const data = response.data;

      const members = Array.isArray(data)
        ? data
        : Array.isArray(data?.results)
        ? data.results
        : [];

      setStaff(members.map(normalizeStaffMember));
    } catch (requestError) {
      console.error("Failed to fetch staff:", requestError);

      setError(getErrorMessage(requestError, "Failed to fetch staff."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStaff();
  }, [fetchStaff]);

  function updateForm(field, value) {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  }

  function startCreate() {
    setEditingId(null);
    setError("");
    setSuccess("");
    setForm({
      ...EMPTY_FORM,
    });
    setShowForm(true);
  }

  function startEdit(member) {
    setEditingId(member.id);
    setError("");
    setSuccess("");

    setForm({
      username: member.username || "",
      email: member.email || "",
      password: "",
      role: member.role || "STAFF",
      is_active: member.is_active ?? true,
    });

    setShowForm(true);
  }

  function closeForm() {
    if (saving) {
      return;
    }

    setShowForm(false);
    setEditingId(null);
    setForm({
      ...EMPTY_FORM,
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);

    const payload = {
      username: form.username.trim(),
      email: form.email.trim(),
      role: form.role,
      is_active: form.is_active,
    };

    if (!editingId) {
      payload.password = form.password;
    } else if (form.password.trim()) {
      payload.password = form.password;
    }

    try {
      if (editingId) {
        await api.patch(`${STAFF_ENDPOINT}${editingId}/`, payload);

        setSuccess("Staff member updated successfully.");
      } else {
        await api.post(STAFF_ENDPOINT, payload);

        setSuccess("Staff member created successfully.");
      }

      closeForm();
      await fetchStaff();
    } catch (requestError) {
      console.error("Failed to save staff member:", requestError);

      setError(getErrorMessage(requestError, "Failed to save staff member."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(member) {
    const confirmed = window.confirm(`Delete ${member.username}?`);

    if (!confirmed) {
      return;
    }

    setError("");
    setSuccess("");
    setDeletingId(member.id);

    try {
      await api.delete(`${STAFF_ENDPOINT}${member.id}/`);

      setSuccess("Staff member deleted successfully.");

      await fetchStaff();
    } catch (requestError) {
      console.error("Failed to delete staff member:", requestError);

      setError(getErrorMessage(requestError, "Failed to delete staff member."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-3">
            <UserCog
              size={28}
              className="text-blue-600"
            />

            <h1 className="text-2xl font-bold text-gray-900">
              Staff Management
            </h1>
          </div>

          <p className="mt-1 text-sm text-gray-500">
            Manage restaurant staff and role-based access.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={fetchStaff}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60">
            <RefreshCcw
              size={16}
              className={loading ? "animate-spin" : ""}
            />
            Refresh
          </button>

          <button
            type="button"
            onClick={startCreate}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            <Plus size={16} />
            Add Staff
          </button>
        </div>
      </div>

      {success && (
        <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          {success}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {showForm && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">
                {editingId ? "Edit Staff Member" : "Add Staff Member"}
              </h2>

              <p className="mt-1 text-sm text-gray-500">
                Permissions are derived from the selected role.
              </p>
            </div>

            <button
              type="button"
              onClick={closeForm}
              disabled={saving}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-50">
              <X size={20} />
            </button>
          </div>

          <form
            onSubmit={handleSubmit}
            className="space-y-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <FormField label="Username">
                <input
                  type="text"
                  required
                  value={form.username}
                  onChange={(event) =>
                    updateForm("username", event.target.value)
                  }
                  className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </FormField>

              <FormField label="Email">
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(event) => updateForm("email", event.target.value)}
                  className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </FormField>

              <FormField
                label={editingId ? "New Password (optional)" : "Password"}>
                <input
                  type="password"
                  required={!editingId}
                  value={form.password}
                  onChange={(event) =>
                    updateForm("password", event.target.value)
                  }
                  className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </FormField>

              <FormField label="Role">
                <select
                  value={form.role}
                  onChange={(event) => updateForm("role", event.target.value)}
                  className="w-full rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100">
                  {ROLE_OPTIONS.map((option) => (
                    <option
                      key={option.value}
                      value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </FormField>
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  updateForm("is_active", event.target.checked)
                }
                className="h-4 w-4 rounded border-gray-300 text-blue-600"
              />
              Account is active
            </label>

            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <div className="mb-3 flex items-center gap-2">
                <ShieldCheck
                  size={18}
                  className="text-blue-600"
                />

                <h3 className="font-semibold text-gray-900">
                  Role capabilities
                </h3>
              </div>

              <PermissionPreview capabilities={capabilities} />
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={closeForm}
                disabled={saving}
                className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                Cancel
              </button>

              <button
                type="submit"
                disabled={saving}
                className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60">
                {saving
                  ? "Saving..."
                  : editingId
                  ? "Update Staff"
                  : "Create Staff"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-5 py-4">
          <h2 className="font-bold text-gray-900">Restaurant Staff</h2>

          <p className="mt-1 text-sm text-gray-500">
            {staff.length} staff member
            {staff.length === 1 ? "" : "s"}
          </p>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-gray-500">
            Loading staff...
          </div>
        ) : staff.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">
            No staff members found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-gray-500">
                  <th className="px-5 py-3 font-semibold">User</th>

                  <th className="px-5 py-3 font-semibold">Role</th>

                  <th className="px-5 py-3 font-semibold">Status</th>

                  <th className="px-5 py-3 font-semibold">Capabilities</th>

                  <th className="px-5 py-3 text-right font-semibold">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody>
                {staff.map((member) => {
                  const memberCapabilities =
                    member.permissions || roleCapabilities(member.role);

                  return (
                    <tr
                      key={member.id}
                      className="border-b last:border-0">
                      <td className="px-5 py-4">
                        <div className="font-medium text-gray-900">
                          {member.username}
                        </div>

                        <div className="text-xs text-gray-500">
                          {member.email || "No email"}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <RoleBadge role={member.role} />
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                            member.is_active
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}>
                          {member.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>

                      <td className="max-w-md px-5 py-4">
                        <div className="flex flex-wrap gap-1.5">
                          {PERMISSION_FIELDS.filter(
                            (permission) => memberCapabilities[permission.id]
                          ).map((permission) => (
                            <span
                              key={permission.id}
                              className="rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700">
                              {permission.label}
                            </span>
                          ))}

                          {!PERMISSION_FIELDS.some(
                            (permission) => memberCapabilities[permission.id]
                          ) && (
                            <span className="text-xs text-gray-400">
                              No special permissions
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => startEdit(member)}
                            className="rounded-lg p-2 text-blue-600 hover:bg-blue-50"
                            title="Edit staff">
                            <Pencil size={16} />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleDelete(member)}
                            disabled={deletingId === member.id}
                            className="rounded-lg p-2 text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                            title="Delete staff">
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
    </div>
  );
}
