import React, { useEffect, useState } from "react";
import api from "../services/api";

export default function Products() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [modifierGroups, setModifierGroups] = useState([]);

  const [name, setName] = useState("");
  const [basePrice, setBasePrice] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedGroups, setSelectedGroups] = useState([]);

  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState("");
  const [editingBasePrice, setEditingBasePrice] = useState("");
  const [editingCategory, setEditingCategory] = useState("");
  const [editingGroups, setEditingGroups] = useState([]);

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
      const [prodRes, catRes, modRes] = await Promise.all([
        api.get("/manager/products/"),
        api.get("/manager/categories/"),
        api.get("/manager/modifier-groups/"),
      ]);

      setProducts(prodRes.data.results || prodRes.data);
      setCategories(catRes.data.results || catRes.data);
      setModifierGroups(modRes.data.results || modRes.data);
    } catch (err) {
      setError("Failed to load product data.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await api.get("/manager/products/");
      setProducts(res.data.results || res.data);
    } catch (err) {
      console.error("Failed to refresh products", err);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim() || !basePrice || !selectedCategory) {
      setError("Please fill in all required fields.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      await api.post("/manager/products/", {
        name: name.trim(),
        base_price: parseFloat(basePrice),
        category: selectedCategory,
        modifier_group_ids: selectedGroups,
      });
      setName("");
      setBasePrice("");
      setSelectedCategory("");
      setSelectedGroups([]);
      await fetchProducts();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create product.");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (productId) => {
    setSaving(true);
    try {
      await api.patch(`/manager/products/${productId}/`, {
        name: editingName.trim(),
        base_price: parseFloat(editingBasePrice),
        category: editingCategory,
        modifier_group_ids: editingGroups,
      });
      setEditingId(null);
      await fetchProducts();
    } catch (err) {
      setError("Failed to update product.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (productId) => {
    if (!window.confirm("Delete this product?")) return;
    try {
      await api.delete(`/manager/products/${productId}/`);
      await fetchProducts();
    } catch (err) {
      setError("Failed to delete product.");
    }
  };

  const startEditing = (product) => {
    setEditingId(product.id);
    setEditingName(product.name);
    setEditingBasePrice(product.base_price);
    setEditingCategory(product.category?.id || product.category || "");
    setEditingGroups(
      product.modifier_groups?.map((g) => String(g.id || g)) || []
    );
  };

  if (loading)
    return <div className="p-8 text-gray-600">Loading products...</div>;

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Product Management</h1>
        <p className="text-gray-500">
          Manage your menu items, prices, and modifiers.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* CREATE FORM */}
        <div className="bg-white p-6 rounded-xl border shadow-sm h-fit">
          <h2 className="text-lg font-bold mb-4">Add New Product</h2>
          <form
            onSubmit={handleCreate}
            className="space-y-4">
            <input
              type="text"
              placeholder="Product Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border p-2 rounded"
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Base Price"
              value={basePrice}
              onChange={(e) => setBasePrice(e.target.value)}
              className="w-full border p-2 rounded"
              required
            />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full border p-2 rounded"
              required>
              <option value="">Select Category</option>
              {categories.map((cat) => (
                <option
                  key={cat.id}
                  value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>

            <div>
              <p className="text-sm font-bold text-gray-700 mb-2">
                Modifier Groups
              </p>
              <div className="max-h-40 overflow-y-auto border rounded p-2 space-y-1">
                {modifierGroups.map((group) => (
                  <label
                    key={group.id}
                    className="flex items-center text-sm">
                    <input
                      type="checkbox"
                      checked={selectedGroups.includes(String(group.id))}
                      onChange={() =>
                        setSelectedGroups((prev) =>
                          prev.includes(String(group.id))
                            ? prev.filter((id) => id !== String(group.id))
                            : [...prev, String(group.id)]
                        )
                      }
                      className="mr-2"
                    />
                    {group.name}
                  </label>
                ))}
              </div>
            </div>
            <button
              type="submit"
              disabled={saving}
              className="w-full bg-blue-600 text-white py-2 rounded font-bold hover:bg-blue-700 disabled:bg-gray-400">
              {saving ? "Saving..." : "Create Product"}
            </button>
          </form>
        </div>

        {/* PRODUCT LIST */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-bold">Existing Products</h2>
          {products.length === 0 ? (
            <div className="text-center py-10 border border-dashed rounded text-gray-400">
              No products found.
            </div>
          ) : (
            products.map((product) => (
              <div
                key={product.id}
                className="bg-white border rounded-xl p-4 shadow-sm">
                {editingId === product.id ? (
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      className="w-full border p-2 rounded"
                    />
                    <input
                      type="number"
                      step="0.01"
                      value={editingBasePrice}
                      onChange={(e) => setEditingBasePrice(e.target.value)}
                      className="w-full border p-2 rounded"
                    />
                    <select
                      value={editingCategory}
                      onChange={(e) => setEditingCategory(e.target.value)}
                      className="w-full border p-2 rounded">
                      {categories.map((cat) => (
                        <option
                          key={cat.id}
                          value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleUpdate(product.id)}
                        className="bg-green-600 text-white px-4 py-1 rounded text-sm">
                        Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="bg-gray-400 text-white px-4 py-1 rounded text-sm">
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-bold text-gray-800">
                        {product.name}
                      </h3>
                      <p className="text-blue-600 font-semibold">
                        ${product.base_price}
                      </p>
                      <p className="text-xs text-gray-500 uppercase mt-1">
                        {product.category_name || "No Category"}
                      </p>
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={() => startEditing(product)}
                        className="text-blue-600 hover:underline text-sm font-medium">
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(product.id)}
                        className="text-red-600 hover:underline text-sm font-medium">
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
