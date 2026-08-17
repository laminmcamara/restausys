import React, { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";

export default function Products() {
  const { accessToken } = useAuth();

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

  const PRODUCTS_URL = "http://127.0.0.1:8000/api/v1/manager/products/";
  const CATEGORIES_URL = "http://127.0.0.1:8000/api/v1/manager/categories/";
  const MODIFIER_GROUPS_URL =
    "http://127.0.0.1:8000/api/v1/manager/modifier-groups/";

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
      await Promise.all([
        fetchProducts(),
        fetchCategories(),
        fetchModifierGroups(),
      ]);
    } catch (err) {
      setError(err.message || "Failed to load product data.");
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    const response = await authFetch(PRODUCTS_URL);

    if (!response) return;

    if (!response.ok) {
      throw new Error(await parseError(response, "Failed to fetch products."));
    }

    const data = await response.json();
    setProducts(data);
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

  const fetchModifierGroups = async () => {
    const response = await authFetch(MODIFIER_GROUPS_URL);

    if (!response) return;

    if (!response.ok) {
      throw new Error(
        await parseError(response, "Failed to fetch modifier groups.")
      );
    }

    const data = await response.json();

    console.log("Modifier groups loaded in Products:", data);

    setModifierGroups(Array.isArray(data) ? data : data.results || []);
  };

  const handleCreate = async (e) => {
    e.preventDefault();

    if (!name.trim()) {
      setError("Product name is required.");
      return;
    }

    if (!basePrice || Number(basePrice) < 0) {
      setError("Base price must be 0 or greater.");
      return;
    }

    if (!selectedCategory) {
      setError("Please select a category.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const response = await authFetch(PRODUCTS_URL, {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          base_price: parseFloat(basePrice),
          category: selectedCategory,
          modifier_group_ids: selectedGroups,
        }),
      });

      if (!response) return;

      if (!response.ok) {
        throw new Error(
          await parseError(response, "Failed to create product.")
        );
      }

      setName("");
      setBasePrice("");
      setSelectedCategory("");
      setSelectedGroups([]);

      await fetchProducts();
    } catch (err) {
      setError(err.message || "Failed to create product.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (productId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this product?"
    );

    if (!confirmed) return;

    setSaving(true);
    setError("");

    try {
      const response = await authFetch(`${PRODUCTS_URL}${productId}/`, {
        method: "DELETE",
      });

      if (!response) return;

      if (!response.ok) {
        throw new Error(
          await parseError(response, "Failed to delete product.")
        );
      }

      await fetchProducts();
    } catch (err) {
      setError(err.message || "Failed to delete product.");
    } finally {
      setSaving(false);
    }
  };

  const startEditing = (product) => {
    setEditingId(product.id);
    setEditingName(product.name || "");
    setEditingBasePrice(product.base_price || "");

    setEditingCategory(
      product.category?.id
        ? String(product.category.id)
        : product.category
        ? String(product.category)
        : ""
    );

    const groupIds =
      product.modifier_groups?.map((group) =>
        String(typeof group === "object" ? group.id : group)
      ) || [];

    setEditingGroups(groupIds);
    setError("");
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditingName("");
    setEditingBasePrice("");
    setEditingCategory("");
    setEditingGroups([]);
  };

  const handleUpdate = async (productId) => {
    if (!editingName.trim()) {
      setError("Product name is required.");
      return;
    }

    if (!editingBasePrice || Number(editingBasePrice) < 0) {
      setError("Base price must be 0 or greater.");
      return;
    }

    if (!editingCategory) {
      setError("Please select a category.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const response = await authFetch(`${PRODUCTS_URL}${productId}/`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editingName.trim(),
          base_price: parseFloat(editingBasePrice),
          category: editingCategory,
          modifier_group_ids: editingGroups,
        }),
      });

      if (!response) return;

      if (!response.ok) {
        throw new Error(
          await parseError(response, "Failed to update product.")
        );
      }

      cancelEditing();
      await fetchProducts();
    } catch (err) {
      setError(err.message || "Failed to update product.");
    } finally {
      setSaving(false);
    }
  };

  const toggleGroup = (id) => {
    const groupId = String(id);

    setSelectedGroups((prev) =>
      prev.includes(groupId)
        ? prev.filter((existingId) => existingId !== groupId)
        : [...prev, groupId]
    );
  };

  const toggleEditingGroup = (id) => {
    const groupId = String(id);

    setEditingGroups((prev) =>
      prev.includes(groupId)
        ? prev.filter((existingId) => existingId !== groupId)
        : [...prev, groupId]
    );
  };
  
  if (loading) {
    return (
      <div className="p-8">
        <p className="text-gray-600">Loading products...</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Product Management</h1>
        <p className="text-gray-500 mt-1">
          Create products, assign categories, and attach modifier groups.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* CREATE FORM */}
      <form
        onSubmit={handleCreate}
        className="space-y-4 max-w-md">
        <input
          type="text"
          placeholder="Product name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="border p-2 rounded w-full"
          required
        />

        <input
          type="number"
          step="0.01"
          min="0"
          placeholder="Base price"
          value={basePrice}
          onChange={(e) => setBasePrice(e.target.value)}
          className="border p-2 rounded w-full"
          required
        />

        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="border p-2 rounded w-full"
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
          <h3 className="font-semibold mb-2">Modifier Groups</h3>

          {modifierGroups.length === 0 ? (
            <p className="text-gray-500 text-sm">No modifier groups found.</p>
          ) : (
            <div className="space-y-1">
              {modifierGroups.map((group) => (
                <label
                  key={group.id}
                  className="block">
                  <input
                    type="checkbox"
                    checked={selectedGroups.includes(String(group.id))}
                    onChange={() => toggleGroup(group.id)}
                    className="mr-2"
                  />
                  {group.name}
                </label>
              ))}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={saving}
          className={`text-white px-4 py-2 rounded ${
            saving
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700"
          }`}>
          {saving ? "Saving..." : "Create Product"}
        </button>
      </form>

      {/* PRODUCT LIST */}
      <div className="space-y-3">
        <h2 className="text-xl font-semibold">Products</h2>

        {products.length === 0 ? (
          <div className="border border-dashed p-6 rounded text-gray-500">
            No products yet.
          </div>
        ) : (
          products.map((product) => (
            <div
              key={product.id}
              className="border p-4 rounded space-y-3">
              {editingId === product.id ? (
                <div className="space-y-4">
                  <input
                    type="text"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    className="border p-2 rounded w-full"
                    required
                  />

                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={editingBasePrice}
                    onChange={(e) => setEditingBasePrice(e.target.value)}
                    className="border p-2 rounded w-full"
                    required
                  />

                  <select
                    value={editingCategory}
                    onChange={(e) => setEditingCategory(e.target.value)}
                    className="border p-2 rounded w-full"
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
                    <h3 className="font-semibold mb-2">Modifier Groups</h3>

                    {modifierGroups.length === 0 ? (
                      <p className="text-gray-500 text-sm">
                        No modifier groups found.
                      </p>
                    ) : (
                      <div className="space-y-1">
                        {modifierGroups.map((group) => (
                          <label
                            key={group.id}
                            className="block">
                            <input
                                type="checkbox"
                                checked={editingGroups.includes(String(group.id))}
                                onChange={() => toggleEditingGroup(group.id)}
                                className="mr-2"
                            />
                            {group.name}
                          </label>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleUpdate(product.id)}
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
                </div>
              ) : (
                <>
                  <div>
                    <h3 className="font-semibold">{product.name}</h3>
                    <p>${product.base_price}</p>

                    {product.category_name && (
                      <p className="text-sm text-gray-500">
                        Category: {product.category_name}
                      </p>
                    )}

                    {product.modifier_groups &&
                      product.modifier_groups.length > 0 && (
                        <p className="text-sm text-gray-500">
                          Modifier Groups:{" "}
                          {product.modifier_groups
                            .map((group) =>
                              typeof group === "object" ? group.name : group
                            )
                            .join(", ")}
                        </p>
                      )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => startEditing(product)}
                      disabled={saving}
                      className="bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-2 rounded disabled:bg-gray-400">
                      Edit
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDelete(product.id)}
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
