import React, { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Products() {
  const { accessToken, logout } = useAuth();
  const { user } = useAuth();
  console.log("USER OBJECT:", user);

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (accessToken) {
      fetchProducts();
    }
  }, [accessToken]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        "http://127.0.0.1:8000/api/v1/products/",
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          logout();
          throw new Error("Session expired. Please login again.");
        }

        if (response.status === 403) {
          throw new Error("Not authorized to view products.");
        }

        throw new Error("Failed to load products.");
      }

      const data = await response.json();
      setProducts(data);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8">Loading products...</div>;
  if (error) return <div className="p-8 text-red-500">{error}</div>;

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold mb-6">Products</h2>

      {products.length === 0 ? (
        <p>No products available.</p>
      ) : (
        <div className="space-y-4">
          {products.map((product) => (
            <div key={product.id} className="border p-4 rounded">
              <h3 className="font-semibold">{product.name}</h3>
              <p>${product.base_price}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}