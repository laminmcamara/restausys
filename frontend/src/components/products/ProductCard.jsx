import React, { useState } from "react";
import { deleteProduct, updateProduct } from "../../services/productService";
import ProductForm from "./ProductForm";

// Use the environment variable or fallback to your local dev URL
const API_BASE = "http://127.0.0.1:8000";

const ProductCard = ({ product, token, onRefresh, categories }) => {
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${product.name}"?`)) return;

    try {
      setLoading(true);
      await deleteProduct(product.id, token);
      onRefresh();
    } catch (err) {
      alert("Failed to delete product.");
    } finally {
      setLoading(false);
    }
  };

  const toggleAvailability = async () => {
    try {
      setLoading(true);
      await updateProduct(
        product.id,
        { is_available: !product.is_available },
        token
      );
      onRefresh();
    } catch (err) {
      alert("Failed to update availability.");
    } finally {
      setLoading(false);
    }
  };

  // Helper to handle image URLs correctly
  const getImageUrl = (path) => {
    if (!path) return null;
    if (path.startsWith("http")) return path;
    return `${API_BASE}${path}`;
  };

  return (
    <div
      className={`border rounded-xl p-4 shadow-sm bg-white transition-opacity ${
        loading ? "opacity-50 pointer-events-none" : "opacity-100"
      }`}>
      {product.image && (
        <div className="w-full h-32 mb-3 overflow-hidden rounded-lg bg-gray-100">
          <img
            src={getImageUrl(product.image)}
            alt={product.name}
            className="w-full h-full object-cover"
          />
        </div>
      )}

      <div className="flex justify-between items-start">
        <h3 className="text-lg font-bold text-gray-800">{product.name}</h3>
        <span className="font-bold text-blue-600">
          ${Number(product.base_price).toFixed(2)}
        </span>
      </div>

      <p className="text-sm text-gray-500 mt-1 line-clamp-2 min-h-[2.5rem]">
        {product.description || "No description provided."}
      </p>

      <div className="mt-3 flex items-center justify-between">
        <span
          className={`text-xs font-bold px-2 py-1 rounded-full ${
            product.is_available
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}>
          {product.is_available ? "Available" : "Unavailable"}
        </span>

        <span className="text-xs text-gray-400">ID: #{product.id}</span>
      </div>

      <div className="flex gap-2 mt-4">
        <button
          onClick={() => setEditing(true)}
          className="flex-1 px-3 py-2 bg-slate-100 text-slate-700 text-sm font-semibold rounded-lg hover:bg-slate-200 transition">
          Edit
        </button>

        <button
          onClick={toggleAvailability}
          className={`flex-1 px-3 py-2 text-sm font-semibold rounded-lg transition ${
            product.is_available
              ? "bg-amber-50 text-amber-700 hover:bg-amber-100"
              : "bg-blue-50 text-blue-700 hover:bg-blue-100"
          }`}>
          {product.is_available ? "Disable" : "Enable"}
        </button>

        <button
          onClick={handleDelete}
          className="px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round">
            <path d="M3 6h18" />
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
          </svg>
        </button>
      </div>

      {/* ✅ EDIT MODAL */}
      {editing && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          <div className="bg-white p-6 rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-800">Edit Product</h2>
              <button
                onClick={() => setEditing(false)}
                className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>

            <ProductForm
              token={token}
              categories={categories}
              initialData={product}
              onSuccess={() => {
                setEditing(false);
                onRefresh();
              }}
            />

            <button
              onClick={() => setEditing(false)}
              className="mt-4 w-full py-2 text-sm font-medium text-gray-500 hover:text-gray-700 transition">
              Cancel and Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductCard;
