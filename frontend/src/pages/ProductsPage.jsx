import React, { useEffect, useState, useCallback } from "react";
import ProductForm from "../components/products/ProductForm";
import ProductList from "../components/products/ProductList";
import { fetchProducts, fetchCategories } from "../services/productService";
import { fetchModifierGroups } from "../services/modifierService";
import { useAuth } from "../hooks/useAuth";

const ProductsPage = () => {
  const { accessToken, refreshAccessToken, logout } = useAuth();

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [modifierGroups, setModifierGroups] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ================= LOAD PRODUCTS =================
  const loadProducts = useCallback(async () => {
    try {
      const data = await fetchProducts(accessToken, refreshAccessToken, logout);

      setProducts(data);
    } catch (err) {
      console.error(err);
      setError("Failed to load products.");
    }
  }, [accessToken, refreshAccessToken, logout]);

  // ================= LOAD CATEGORIES =================
  const loadCategories = useCallback(async () => {
    try {
      const data = await fetchCategories(
        accessToken,
        refreshAccessToken,
        logout
      );

      setCategories(data);
    } catch (err) {
      console.error(err);
      setError("Failed to load categories.");
    }
  }, [accessToken, refreshAccessToken, logout]);

  // ================= LOAD MODIFIER GROUPS =================
  const loadModifierGroups = useCallback(async () => {
    try {
      const data = await fetchModifierGroups(
        accessToken,
        refreshAccessToken,
        logout
      );

      setModifierGroups(data);
    } catch (err) {
      console.error(err);
      setError("Failed to load modifier groups.");
    }
  }, [accessToken, refreshAccessToken, logout]);

  // ================= INITIAL LOAD =================
  useEffect(() => {
    if (!accessToken) {
      setError("You must be logged in.");
      setLoading(false);
      return;
    }

    const init = async () => {
      setLoading(true);
      setError(null);

      try {
        await Promise.all([
          loadProducts(),
          loadCategories(),
          loadModifierGroups(),
        ]);
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [accessToken, loadProducts, loadCategories, loadModifierGroups]);

  // ================= RENDER =================
  if (loading) return <p>Loading products...</p>;

  if (error) return <p style={{ color: "red" }}>{error}</p>;

  return (
    <div style={{ padding: "20px" }}>
      <h1>Product Management</h1>

      <ProductForm
        categories={categories}
        modifierGroups={modifierGroups}
        accessToken={accessToken}
        refreshAccessToken={refreshAccessToken}
        logout={logout}
        onProductCreated={loadProducts}
      />

      <ProductList
        products={products}
        accessToken={accessToken}
        refreshAccessToken={refreshAccessToken}
        logout={logout}
        onRefresh={loadProducts}
      />
    </div>
  );
};

export default ProductsPage;
