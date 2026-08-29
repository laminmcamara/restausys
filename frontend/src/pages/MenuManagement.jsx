import React, { useState, useEffect } from "react";
import api from "../services/api";
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  Package,
  DollarSign,
  Loader2,
  Check,
  AlertCircle,
} from "lucide-react";

const ProductManagement = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [modifiers, setModifiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    base_price: "",
    category: "",
    selectedModifiers: [],
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);

    // Fetch Categories
    try {
      const catRes = await api.get("/manager/categories/");
      const data = catRes.data.results || catRes.data || [];
      setCategories(data);
      console.log("Categories successfully loaded:", data);
    } catch (err) {
      console.error("Category Load Error:", err);
    }

    // Fetch Products
    try {
      const prodRes = await api.get("/manager/products/");
      setProducts(prodRes.data.results || prodRes.data || []);
    } catch (err) {
      console.error("Product Load Error:", err);
    }

    // Fetch Modifiers (Using the new endpoint we just registered)
    try {
      const modRes = await api.get("/manager/modifiers/");
      setModifiers(modRes.data.results || modRes.data || []);
    } catch (err) {
      console.warn("Modifiers not found, check backend router registration.");
      setModifiers([]);
    }

    setLoading(false);
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();

    if (!formData.category) {
      alert("Please select a category first.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        name: formData.name,
        base_price: formData.base_price,
        category: formData.category, // This must be the ID
        modifier_ids: formData.selectedModifiers,
      };

      await api.post("/manager/products/", payload);

      setFormData({
        name: "",
        base_price: "",
        category: "",
        selectedModifiers: [],
      });
      fetchData();
      alert("Product created successfully!");
    } catch (err) {
      console.error("Creation error:", err.response?.data);
      alert(
        err.response?.data?.detail ||
          "Failed to create product. Ensure all fields are valid."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const toggleModifier = (modId) => {
    setFormData((prev) => ({
      ...prev,
      selectedModifiers: prev.selectedModifiers.includes(modId)
        ? prev.selectedModifiers.filter((id) => id !== modId)
        : [...prev.selectedModifiers, modId],
    }));
  };

  if (loading)
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2
          className="animate-spin text-blue-600"
          size={40}
        />
      </div>
    );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-900">Menu Items</h1>
          <p className="text-slate-500">
            Create and manage your products and pricing.
          </p>
        </div>
        {categories.length === 0 && (
          <div className="flex items-center gap-2 bg-amber-50 text-amber-700 px-4 py-2 rounded-xl border border-amber-200 text-sm font-bold">
            <AlertCircle size={16} />
            No categories found. Create one first!
          </div>
        )}
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* FORM SECTION */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden sticky top-6">
            <div className="p-6 border-b border-slate-100">
              <h2 className="text-lg font-bold">Add New Product</h2>
            </div>

            <form
              onSubmit={handleCreateProduct}
              className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-black text-slate-400 uppercase mb-2">
                  Product Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-500 outline-none transition-all"
                  placeholder="e.g. Cheese Pizza"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-black text-slate-400 uppercase mb-2">
                    Price ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={formData.base_price}
                    onChange={(e) =>
                      setFormData({ ...formData, base_price: e.target.value })
                    }
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-500 outline-none"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-xs font-black text-slate-400 uppercase mb-2">
                    Category
                  </label>
                  <select
                    required
                    value={formData.category}
                    onChange={(e) =>
                      setFormData({ ...formData, category: e.target.value })
                    }
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-500 outline-none bg-white">
                    <option value="">Select...</option>
                    {categories.map((cat) => (
                      <option
                        key={cat.id}
                        value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-black text-slate-400 uppercase mb-2">
                  Modifiers
                </label>
                <div className="flex flex-wrap gap-2">
                  {modifiers.map((mod) => (
                    <button
                      key={mod.id}
                      type="button"
                      onClick={() => toggleModifier(mod.id)}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-bold transition-all ${
                        formData.selectedModifiers.includes(mod.id)
                          ? "border-blue-600 bg-blue-600 text-white"
                          : "border-slate-200 text-slate-500 hover:border-slate-400"
                      }`}>
                      {mod.name}
                    </button>
                  ))}
                  {modifiers.length === 0 && (
                    <p className="text-[10px] text-slate-400 italic">
                      No modifiers created yet.
                    </p>
                  )}
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting || categories.length === 0}
                className="w-full bg-slate-900 text-white py-4 rounded-2xl font-black hover:bg-black transition-all disabled:bg-slate-200">
                {submitting ? (
                  <Loader2 className="animate-spin mx-auto" />
                ) : (
                  "Save Product"
                )}
              </button>
            </form>
          </div>
        </div>

        {/* LIST SECTION */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-100 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                    <th className="px-6 py-4">Item</th>
                    <th className="px-6 py-4">Category</th>
                    <th className="px-6 py-4">Price</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {products.map((product) => (
                    <tr
                      key={product.id}
                      className="group hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
                            <Package size={16} />
                          </div>
                          <span className="font-bold text-slate-700">
                            {product.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded-md">
                          {product.category_name || "General"}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-black text-slate-900">
                        ${parseFloat(product.base_price).toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button className="p-2 hover:bg-white rounded-lg border border-transparent hover:border-slate-200 text-slate-400 hover:text-blue-600">
                            <Edit2 size={14} />
                          </button>
                          <button className="p-2 hover:bg-white rounded-lg border border-transparent hover:border-slate-200 text-slate-400 hover:text-red-600">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {products.length === 0 && (
              <div className="py-20 text-center text-slate-400">
                <Package
                  className="mx-auto mb-2 opacity-20"
                  size={40}
                />
                <p className="text-sm">No products added yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductManagement;
