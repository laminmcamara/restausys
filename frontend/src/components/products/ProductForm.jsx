import React, { useState } from "react";
import { createProduct } from "../../services/productService";

const ProductForm = ({ categories, token, onProductCreated }) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [basePrice, setBasePrice] = useState("");
  const [category, setCategory] = useState("");
  const [isAvailable, setIsAvailable] = useState(true);
  const [image, setImage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append("name", name);
    formData.append("description", description);
    formData.append("base_price", basePrice);
    formData.append("category", category);
    formData.append("is_available", isAvailable);

    if (image) {
      formData.append("image", image);
    }

    try {
      await createProduct(formData, token);

      // Reset form
      setName("");
      setDescription("");
      setBasePrice("");
      setCategory("");
      setIsAvailable(true);
      setImage(null);

      onProductCreated(); // Refresh list
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ marginBottom: "30px" }}>
      <h2>Create Product</h2>

      <input
        type="text"
        placeholder="Product Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />

      <br />

      <textarea
        placeholder="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />

      <br />

      <input
        type="number"
        step="0.01"
        placeholder="Base Price"
        value={basePrice}
        onChange={(e) => setBasePrice(e.target.value)}
        required
      />

      <br />

      <select
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        required
      >
        <option value="">Select Category</option>
        {categories.map((cat) => (
          <option key={cat.id} value={cat.id}>
            {cat.name}
          </option>
        ))}
      </select>

      <br />

      <label>
        <input
          type="checkbox"
          checked={isAvailable}
          onChange={(e) => setIsAvailable(e.target.checked)}
        />
        Available
      </label>

      <br />

      <input
        type="file"
        accept="image/*"
        onChange={(e) => setImage(e.target.files[0])}
      />

      <br />
      <br />

      <button type="submit">Create Product</button>
    </form>
  );
};

export default ProductForm;