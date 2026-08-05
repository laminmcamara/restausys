import React, { useState } from "react";
import { deleteProduct, updateProduct } from "../../services/productService";
import ProductForm from "./ProductForm";

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
      alert("Failed to delete.");
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
      alert("Failed to update.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border rounded-lg p-4 shadow-sm bg-white">
      {product.image && (
        <img
          src={`${API_BASE}${product.image}`}
          alt={product.name}
          className="w-20 mb-3 rounded"
        />
      )}

      <h3 className="text-lg font-semibold">{product.name}</h3>
      <p className="text-sm text-gray-600">{product.description}</p>
      <p className="mt-2 font-medium">${product.base_price}</p>
      <p className="text-sm">
        Status:{" "}
        <span
          className={product.is_available ? "text-green-600" : "text-red-600"}>
          {product.is_available ? "Available" : "Unavailable"}
        </span>
      </p>

      <div className="flex gap-2 mt-4">
        <button
          onClick={() => setEditing(true)}
          className="px-3 py-1 bg-blue-600 text-white rounded">
          Edit
        </button>

        <button
          onClick={toggleAvailability}
          className="px-3 py-1 bg-yellow-500 text-white rounded">
          Toggle
        </button>

        <button
          onClick={handleDelete}
          className="px-3 py-1 bg-red-600 text-white rounded">
          Delete
        </button>
      </div>

      {/* ✅ EDIT MODAL */}
      {editing && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex justify-center items-center">
          <div className="bg-white p-6 rounded-lg w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">Edit Product</h2>

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
              className="mt-3 text-sm text-gray-600">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductCard;
