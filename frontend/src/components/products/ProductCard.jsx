import React from "react";

const ProductCard = ({ product }) => {
  return (
    <div style={{ border: "1px solid #ccc", padding: "10px", marginBottom: "10px" }}>
      {product.image && (
        <img
          src={`http://127.0.0.1:8000${product.image}`}
          alt={product.name}
          width="80"
        />
      )}

      <h3>{product.name}</h3>
      <p>{product.description}</p>
      <p>Price: ${product.base_price}</p>
      <p>Status: {product.is_available ? "Available" : "Unavailable"}</p>
    </div>
  );
};

export default ProductCard;