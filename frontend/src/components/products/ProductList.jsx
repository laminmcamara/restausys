import React from "react";
import ProductCard from "./ProductCard";

const ProductList = ({ products, token, onRefresh }) => {
  if (!products || products.length === 0) {
    return <p>No products found.</p>;
  }

  return (
    <div>
      <h2>Products</h2>

      <div style={{ display: "grid", gap: "12px" }}>
        {products.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            token={token}
            onRefresh={onRefresh}
          />
        ))}
      </div>
    </div>
  );
};


export default ProductList;
