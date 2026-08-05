import React, { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";

export default function Categories() {
  const { accessToken } = useAuth();

  const [categories, setCategories] = useState([]);
  const [activeMenu, setActiveMenu] = useState(null);

  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const MENUS_URL = "http://127.0.0.1:8000/api/v1/manager/menus/";
  const CATEGORIES_URL = "http://127.0.0.1:8000/api/v1/manager/categories/";

  useEffect(() => {
    if (accessToken) {
      loadPageData();
    }
  }, [accessToken]);

  const authFetch = async (url, options = {}) => {
    return fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });
  };

  const parseError = async (response, fallbackMessage) => {
    const data = await response.json().catch(() => null);

    if (data?.detail) return data.detail;
    if (data?.error) return data.error;

    if (typeof data === "object" && data !== null) {
      const firstKey = Object.keys(data)[0];

      if (firstKey) {
        const value = data[firstKey];

        if (Array.isArray(value)) {
          return `${firstKey}: ${value.join(", ")}`;
        }

        return `${firstKey}: ${value}`;
      }
    }

    return fallbackMessage;
  };

  const loadPageData = async () => {
    setLoading(true);
    setError("");

    try {
      await Promise.all([fetchActiveMenu(), fetchCategories()]);
    } catch (err) {
      setError(err.message || "Failed to load categories.");
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveMenu = async () => {
    const response = await authFetch(MENUS_URL);

    if (!response) return;

    if (!response.ok) {
      throw new Error(await parseError(response, "Failed to fetch menus."));
    }

    const data = await response.json();
    const active = data.find((menu) => menu.is_active);

    setActiveMenu(active || null);
  };

  const fetchCategories = async () => {
    const response = await authFetch(CATEGORIES_URL);

    if (!response) return;

    if (!response.ok) {
      throw new Error(
        await parseError(response, "Failed to fetch categories.")
      );
    }

    const data = await response.json();
    setCategories(data);
  };

  const handleCreate = async (e) => {
    e.preventDefault();

    if (!activeMenu) {
      setError(
        "No active menu found. Please create and activate a menu first."
      );
      return;
    }

    if (!name.trim()) {
      setError("Category name is required.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const response = await authFetch(CATEGORIES_URL, {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          menu: activeMenu.id,
        }),
      });

      if (!response) return;

      if (!response.ok) {
        throw new Error(
          await parseError(response, "Failed to create category.")
        );
      }

      setName("");
      await fetchCategories();
    } catch (err) {
      setError(err.message || "Failed to create category.");
    } finally {
      setSaving(false);
    }
  };

  const startEditing = (category) => {
    setEditingId(category.id);
    setEditingName(category.name);
    setError("");
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditingName("");
  };

  const handleUpdate = async (categoryId) => {
    if (!editingName.trim()) {
      setError("Category name is required.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const response = await authFetch(`${CATEGORIES_URL}${categoryId}/`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editingName.trim(),
        }),
      });

      if (!response) return;

      if (!response.ok) {
        throw new Error(
          await parseError(response, "Failed to update category.")
        );
      }

      setEditingId(null);
      setEditingName("");
      await fetchCategories();
    } catch (err) {
      setError(err.message || "Failed to update category.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (categoryId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this category?"
    );

    if (!confirmed) return;

    setSaving(true);
    setError("");

    try {
      const response = await authFetch(`${CATEGORIES_URL}${categoryId}/`, {
        method: "DELETE",
      });

      if (!response) return;

      if (!response.ok) {
        throw new Error(
          await parseError(response, "Failed to delete category.")
        );
      }

      await fetchCategories();
    } catch (err) {
      setError(err.message || "Failed to delete category.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-gray-600">Loading categories...</div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Category Management</h1>
        <p className="text-gray-500 mt-1">
          Create and manage categories for your active menu.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {!activeMenu && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded font-medium">
          No active menu found. Please create and activate a menu first.
        </div>
      )}

      {activeMenu && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded">
          Active menu: <span className="font-semibold">{activeMenu.name}</span>
        </div>
      )}

      <form
        onSubmit={handleCreate}
        className="flex gap-4 max-w-xl">
        <input
          type="text"
          placeholder="Category name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="border p-2 rounded w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />

        <button
          type="submit"
          disabled={!activeMenu || saving}
          className={`px-4 py-2 rounded text-white ${
            !activeMenu || saving
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700"
          }`}>
          {saving ? "Saving..." : "Add"}
        </button>
      </form>

      <div className="space-y-3">
        {categories.length === 0 ? (
          <div className="border border-dashed p-6 rounded text-gray-500">
            No categories yet.
          </div>
        ) : (
          categories.map((cat) => (
            <div
              key={cat.id}
              className="border p-3 rounded flex items-center justify-between gap-4">
              {editingId === cat.id ? (
                <>
                  <input
                    type="text"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    className="border p-2 rounded w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
                    autoFocus
                  />

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleUpdate(cat.id)}
                      disabled={saving}
                      className="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded disabled:bg-gray-400">
                      Save
                    </button>

                    <button
                      type="button"
                      onClick={cancelEditing}
                      disabled={saving}
                      className="bg-gray-500 hover:bg-gray-600 text-white px-3 py-2 rounded disabled:bg-gray-400">
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <span className="font-medium">{cat.name}</span>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => startEditing(cat)}
                      disabled={saving}
                      className="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-2 rounded disabled:bg-gray-400">
                      Edit
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDelete(cat.id)}
                      disabled={saving}
                      className="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded disabled:bg-gray-400">
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
