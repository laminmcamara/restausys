import React, { useState, useEffect } from "react";
import api from "../services/api";
import { Plus, Folder, Trash2, Edit2, Loader2, LayoutGrid } from "lucide-react";

const CategoryManagement = () => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const res = await api.get("/manager/categories/");
      setCategories(res.data.results || res.data);
    } catch (err) {
      console.error("Failed to fetch categories", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      await api.post("/manager/categories/", { name });
      setName("");
      fetchCategories();
    } catch (err) {
      alert("Error creating category. It might already exist.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (
      !window.confirm(
        "Delete this category? Products in this category might become uncategorized."
      )
    )
      return;
    try {
      await api.delete(`/manager/categories/${id}/`);
      fetchCategories();
    } catch (err) {
      alert("Could not delete category.");
    }
  };

  if (loading)
    return (
      <div className="p-10 text-center">
        <Loader2 className="animate-spin mx-auto text-blue-600" />
      </div>
    );

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-black text-slate-900">Categories</h1>
        <p className="text-slate-500">Organize your menu items into groups.</p>
      </div>

      {/* Create Form */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
        <form
          onSubmit={handleCreate}
          className="flex gap-3">
          <div className="flex-1 relative">
            <LayoutGrid
              className="absolute left-4 top-3.5 text-slate-400"
              size={18}
            />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Category Name (e.g. Main Course, Soft Drinks)"
              className="w-full pl-12 pr-4 py-3 rounded-2xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
              required
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="px-8 py-3 bg-blue-600 text-white rounded-2xl font-bold hover:bg-blue-700 transition-all disabled:opacity-50 flex items-center gap-2">
            {submitting ? (
              <Loader2
                className="animate-spin"
                size={18}
              />
            ) : (
              <Plus size={18} />
            )}
            Add Category
          </button>
        </form>
      </div>

      {/* List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {categories.map((cat) => (
          <div
            key={cat.id}
            className="bg-white p-5 rounded-2xl border border-slate-200 flex justify-between items-center group hover:border-blue-300 transition-all shadow-sm">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-slate-50 flex items-center justify-center text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                <Folder size={24} />
              </div>
              <div>
                <h3 className="font-bold text-slate-900">{cat.name}</h3>
                <p className="text-xs text-slate-400">
                  {cat.product_count || 0} Products
                </p>
              </div>
            </div>

            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg">
                <Edit2 size={16} />
              </button>
              <button
                onClick={() => handleDelete(cat.id)}
                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg">
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}

        {categories.length === 0 && (
          <div className="col-span-full py-20 text-center border-2 border-dashed border-slate-200 rounded-3xl">
            <Folder
              className="mx-auto text-slate-200 mb-2"
              size={48}
            />
            <p className="text-slate-400">
              No categories yet. Create your first one above!
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CategoryManagement;
