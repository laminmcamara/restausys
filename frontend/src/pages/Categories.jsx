import React, { useEffect, useState } from "react";
import api from "../services/api";

export default function Categories() {
  const [categories, setCategories] = useState([]);
  const [activeMenu, setActiveMenu] = useState(null);

  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadPageData();
  }, []);

  const loadPageData = async () => {
    setLoading(true);
    setError("");
    try {
      // Fetch menus and categories using the centralized API service
      const [menusRes, categoriesRes] = await Promise.all([
        api.get("/manager/menus/"),
        api.get("/manager/categories/"),
      ]);

      const menus = menusRes.data.results || menusRes.data;
      const active = menus.find((menu) => menu.is_active);

      setActiveMenu(active || null);
      setCategories(categoriesRes.data.results || categoriesRes.data);
    } catch (err) {
      console.error("Load Error:", err);
      setError(err.response?.data?.detail || "Failed to load categories.");
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const res = await api.get("/manager/categories/");
      setCategories(res.data.results || res.data);
    } catch (err) {
      setError("Failed to refresh categories list.");
    }
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
      await api.post("/manager/categories/", {
        name: name.trim(),
        menu: activeMenu.id,
      });

      setName("");
      await fetchCategories();
    } catch (err) {
      setError(
        err.response?.data?.name?.[0] ||
          err.response?.data?.detail ||
          "Failed to create category."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (categoryId) => {
    if (!editingName.trim()) {
      setError("Category name is required.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      await api.patch(`/manager/categories/${categoryId}/`, {
        name: editingName.trim(),
      });

      setEditingId(null);
      setEditingName("");
      await fetchCategories();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update category.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (categoryId) => {
    if (!window.confirm("Are you sure you want to delete this category?"))
      return;

    setSaving(true);
    setError("");

    try {
      await api.delete(`/manager/categories/${categoryId}/`);
      await fetchCategories();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete category.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-gray-600">Loading categories...</div>;
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

      {!activeMenu ? (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded font-medium">
          No active menu found. Please create and activate a menu first in Menu
          Management.
        </div>
      ) : (
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
          className={`px-4 py-2 rounded text-white font-medium ${
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
              className="border p-3 rounded flex items-center justify-between gap-4 bg-white shadow-sm">
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
                      onClick={() => handleUpdate(cat.id)}
                      disabled={saving}
                      className="bg-green-600 text-white px-3 py-2 rounded text-sm">
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="bg-gray-500 text-white px-3 py-2 rounded text-sm">
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <span className="font-medium text-gray-800">{cat.name}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setEditingId(cat.id);
                        setEditingName(cat.name);
                      }}
                      className="text-blue-600 hover:underline text-sm font-medium">
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(cat.id)}
                      className="text-red-600 hover:underline text-sm font-medium">
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
