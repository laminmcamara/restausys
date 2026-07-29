import React, { useEffect, useState } from "react";
import ProductForm from "../components/products/ProductForm";
import ProductList from "../components/products/ProductList";
import {
  fetchProducts,
  fetchCategories,
} from "../services/productService";

const ProductsPage = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);

  // ⚠️ Replace this with your real token logic
  const token = localStorage.getItem("access");

  const loadProducts = async () => {
    try {
      const data = await fetchProducts(token);
      setProducts(data);
    } catch (error) {
      console.error(error);
    }
  };

  const loadCategories = async () => {
    try {
      const data = await fetchCategories(token);
      setCategories(data);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    loadProducts();
    loadCategories();
  }, []);

  return (
    <div style={{ padding: "20px" }}>
      <h1>Product Management</h1>

      <ProductForm
        categories={categories}
        token={token}
        onProductCreated={loadProducts}
      />

      <ProductList products={products} />
    </div>
  );
};

export default ProductsPage;